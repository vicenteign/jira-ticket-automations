"""
API server for Jira automation webhooks.
Exposes /webhook/email for Google Apps Script integration.
Deploy to Render or similar cloud platforms.
"""

import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from jira_automation.config import Config
from jira_automation.jira_client import JiraClient
from jira_automation.llm_analyzer import LLMAnalyzer

load_dotenv()

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# --- Config ---
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").strip()
JIRA_EMAIL_PROJECT_KEY = os.getenv("JIRA_EMAIL_PROJECT_KEY", "").strip()
JIRA_WEBSITE_ASSIGNEE_EMAIL = os.getenv("JIRA_WEBSITE_ASSIGNEE_EMAIL", "").strip()
EMAIL_LLM_CONTEXT_PATH = os.getenv("EMAIL_LLM_CONTEXT_PATH", "email_llm_context.md").strip()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifespan."""
    logger.info("Starting Jira automation API server")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Jira Automation API",
    description="Webhook for email-to-Jira automation",
    version="1.0.0",
    lifespan=lifespan,
)


# --- Helpers ---


def verify_webhook_secret(request: Request) -> None:
    """Verify X-Webhook-Secret header."""
    if not WEBHOOK_SECRET:
        logger.warning("WEBHOOK_SECRET not configured - skipping validation")
        return

    secret = request.headers.get("X-Webhook-Secret", "")
    if secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")


@app.get("/")
async def root():
    """Health check / root."""
    return {"status": "ok", "service": "jira-automation-api"}


@app.get("/health")
async def health():
    """Health check for Render and load balancers."""
    return {"status": "healthy"}


@app.post("/webhook/email")
async def webhook_email(request: Request):
    """
    Receive email JSON from Google Apps Script.
    Analyzes content with LLM and creates a Jira task automatically.
    """
    verify_webhook_secret(request)

    try:
        payload = await request.json()
    except Exception as e:
        logger.error("Invalid JSON body: %s", e)
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # Parse payload
    subject = payload.get("subject") or ""
    from_addr = payload.get("from") or ""
    body_obj = payload.get("body") or {}
    body_plain = body_obj.get("plain") if isinstance(body_obj, dict) else ""
    body_html = body_obj.get("html") if isinstance(body_obj, dict) else ""

    if not body_plain and not body_html:
        body_plain = str(body_obj)[:5000] if body_obj else ""

    body_text = (body_plain or body_html or "").strip()

    if not body_text and not subject:
        raise HTTPException(status_code=400, detail="Email body and subject are empty")

    # Config check
    config = Config()
    if not config.is_configured():
        logger.error("Jira not configured (JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN)")
        raise HTTPException(status_code=503, detail="Jira not configured")

    if not config.is_llm_configured():
        logger.error("OpenAI API key not configured")
        raise HTTPException(status_code=503, detail="LLM not configured")

    if not JIRA_EMAIL_PROJECT_KEY:
        logger.error("JIRA_EMAIL_PROJECT_KEY not set")
        raise HTTPException(status_code=503, detail="JIRA_EMAIL_PROJECT_KEY not configured")

    # Load optional client context for LLM (helps infer is_website_requirement)
    llm_context = ""
    for base in (Path.cwd(), Path(__file__).resolve().parent):
        ctx_path = base / EMAIL_LLM_CONTEXT_PATH
        if ctx_path.exists() and ctx_path.is_file():
            try:
                llm_context = ctx_path.read_text(encoding="utf-8")
                logger.info("Loaded email LLM context from %s", ctx_path)
            except Exception as e:
                logger.warning("Could not read %s: %s", ctx_path, e)
            break

    # Extract task from email with LLM
    llm = LLMAnalyzer(config)
    task = llm.extract_task_from_email(
        subject=subject, from_addr=from_addr, body=body_text, context=llm_context
    )

    if not task:
        logger.error("LLM failed to extract task from email")
        raise HTTPException(status_code=500, detail="Failed to extract task from email")

    # Add email metadata to description
    meta = f"---\n*Email from: {from_addr}*"
    if payload.get("message_id"):
        meta += f"\n*Message ID: {payload.get('message_id')}*"
    full_description = f"{task['description']}\n\n{meta}"

    # Resolve assignee for website requirements
    assignee_account_id = None
    if task.get("is_website_requirement") and JIRA_WEBSITE_ASSIGNEE_EMAIL:
        jira = JiraClient(config)
        assignee_account_id = jira.get_account_id_by_email(
            JIRA_WEBSITE_ASSIGNEE_EMAIL, JIRA_EMAIL_PROJECT_KEY
        )
        if assignee_account_id:
            logger.info("Assigning website task to %s", JIRA_WEBSITE_ASSIGNEE_EMAIL)
        else:
            logger.warning("Could not find Jira user for %s, creating unassigned", JIRA_WEBSITE_ASSIGNEE_EMAIL)

    # Create Jira issue
    jira = JiraClient(config)
    result = jira.create_issue(
        project_key=JIRA_EMAIL_PROJECT_KEY,
        issue_type="Task",
        summary=task["summary"],
        description=full_description,
        parent_key=None,
        epic_key=None,
        assignee_account_id=assignee_account_id,
    )

    if not result:
        logger.error("Failed to create Jira issue (check logs above for Jira API error)")
        raise HTTPException(
            status_code=500,
            detail="Failed to create Jira issue. Check Render logs for Jira API error (e.g. invalid project key, permissions, or issue type).",
        )

    issue_key = result.get("key")
    issue_url = jira.get_issue_url(issue_key) if issue_key else ""

    logger.info("Created Jira issue %s from email subject=%s", issue_key, subject[:50])

    return JSONResponse(
        status_code=200,
        content={
            "ok": True,
            "jira_key": issue_key,
            "jira_url": issue_url,
            "summary": task["summary"],
        },
    )
