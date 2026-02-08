import os
from typing import Dict, List, Optional, Tuple

import streamlit as st

from jira_automation.config import Config
from jira_automation.jira_client import JiraClient
from jira_automation.llm_analyzer import LLMAnalyzer
from jira_automation.main import JiraAutomationApp


class SilentUI:
    def display_creation_progress(self, current: int, total: int, ticket_summary: str):
        return


def apply_theme():
    st.set_page_config(
        page_title="Jira Automation Studio",
        layout="wide",
    )
    st.markdown(
        """
        <style>
        :root {
            --bg: #0b0e12;
            --surface: #12161b;
            --surface-2: #151b22;
            --ink: #f2f4f6;
            --muted: #a8b0ba;
            --accent: #5ce1d7;
            --accent-2: #ff9f4a;
            --card: #141a21;
            --border: #232a33;
            --glow: rgba(92, 225, 215, 0.18);
            --epic: #6dd3ff;
            --story: #b98bff;
            --task: #ffd166;
            --subtask: #9cffc7;
        }
        .stApp {
            background: radial-gradient(1200px 800px at 15% -20%, #1f2834 0%, var(--bg) 55%, #0a0c0f 100%);
            color: var(--ink);
        }
        header[data-testid="stHeader"] {
            background: transparent;
        }
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f1319 0%, #10151b 100%);
            border-right: 1px solid var(--border);
        }
        section[data-testid="stSidebar"] * {
            color: var(--ink);
        }
        .block-container {
            padding-top: 2.5rem;
            padding-bottom: 2rem;
        }
        h1, h2, h3, h4, h5, h6, p, label, span {
            font-family: "Palatino Linotype", "Book Antiqua", "Georgia", serif;
            color: var(--ink);
        }
        .hero {
            background: linear-gradient(135deg, #1b2431 0%, #121820 100%);
            border: 1px solid rgba(92, 225, 215, 0.25);
            border-radius: 22px;
            padding: 1.8rem 2.2rem;
            box-shadow: 0 18px 40px rgba(0, 0, 0, 0.5);
        }
        .hero h1 {
            font-size: 2.4rem;
            margin-bottom: 0.3rem;
        }
        .hero p {
            font-size: 1.02rem;
            color: var(--muted);
            margin-top: 0.2rem;
        }
        .stTextArea textarea, .stTextInput input, .stSelectbox select, .stNumberInput input {
            background: var(--card) !important;
            border: 1px solid var(--border) !important;
            border-radius: 12px !important;
            color: var(--ink) !important;
        }
        .stTextArea textarea:focus, .stTextInput input:focus {
            border-color: var(--accent) !important;
            box-shadow: 0 0 0 3px var(--glow) !important;
        }
        .stButton button {
            background: linear-gradient(120deg, var(--accent), #4bb0a7);
            border: 1px solid rgba(92, 225, 215, 0.6);
            color: #081014;
            border-radius: 12px;
            padding: 0.5rem 1.1rem;
            box-shadow: 0 10px 24px rgba(0, 0, 0, 0.3);
        }
        .stButton button:hover {
            background: linear-gradient(120deg, #4fbeb5, #3ea39a);
            border-color: rgba(92, 225, 215, 0.9);
        }
        .section-title {
            font-size: 1.35rem;
            margin: 0.4rem 0 0.6rem 0;
            letter-spacing: 0.04em;
        }
        .card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.1rem 1.4rem;
            box-shadow: 0 14px 28px rgba(0, 0, 0, 0.4);
        }
        .ticket-pill {
            display: inline-block;
            padding: 0.25rem 0.7rem;
            border-radius: 999px;
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            margin-right: 0.6rem;
            border: 1px solid transparent;
        }
        .pill-epic {
            background: rgba(109, 211, 255, 0.12);
            border-color: rgba(109, 211, 255, 0.5);
            color: var(--epic);
        }
        .pill-story {
            background: rgba(185, 139, 255, 0.12);
            border-color: rgba(185, 139, 255, 0.5);
            color: var(--story);
        }
        .pill-task {
            background: rgba(255, 209, 102, 0.12);
            border-color: rgba(255, 209, 102, 0.5);
            color: var(--task);
        }
        .pill-subtask {
            background: rgba(156, 255, 199, 0.12);
            border-color: rgba(156, 255, 199, 0.5);
            color: var(--subtask);
        }
        .subtle {
            color: var(--muted);
        }
        .divider {
            height: 1px;
            background: var(--border);
            margin: 1.2rem 0;
        }
        div[data-testid="stDataFrame"] {
            border-radius: 14px;
            overflow: hidden;
            border: 1px solid var(--border);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def build_config_from_inputs(
    jira_url: str,
    jira_email: str,
    jira_api_token: str,
    openai_api_key: str,
    persist: bool,
) -> Config:
    os.environ["JIRA_URL"] = jira_url.strip()
    os.environ["JIRA_EMAIL"] = jira_email.strip()
    os.environ["JIRA_API_TOKEN"] = jira_api_token.strip()
    os.environ["OPENAI_API_KEY"] = openai_api_key.strip()

    config = Config()
    if persist:
        config.save_env_file(jira_url, jira_email, jira_api_token, openai_api_key)
    return config


def describe_ticket(ticket: Dict, tickets: List[Dict]) -> str:
    parent_summary = ""
    parent_idx = ticket.get("parent_index")
    if parent_idx is not None and 0 <= parent_idx < len(tickets):
        parent_summary = tickets[parent_idx].get("summary", "")
    if parent_summary:
        return f"{ticket['type']} - {ticket['summary']} (Parent: {parent_summary})"
    return f"{ticket['type']} - {ticket['summary']}"


def build_parent_options(current_index: int, tickets: List[Dict]) -> List[Tuple[str, Optional[int]]]:
    options = [("None", None)]
    for idx, t in enumerate(tickets):
        if idx == current_index:
            continue
        label = f"{idx + 1}. {t['type']} - {t['summary']}"
        options.append((label, idx))
    return options


def tickets_table(tickets: List[Dict]) -> List[Dict]:
    rows = []
    for ticket in tickets:
        parent = ""
        parent_idx = ticket.get("parent_index")
        if parent_idx is not None and 0 <= parent_idx < len(tickets):
            parent = tickets[parent_idx].get("summary", "")
        rows.append(
            {
                "Type": ticket.get("type"),
                "Summary": ticket.get("summary"),
                "Parent": parent,
            }
        )
    return rows


def pill_class(ticket_type: str) -> str:
    normalized = (ticket_type or "").strip().lower()
    if normalized == "epic":
        return "pill-epic"
    if normalized == "story":
        return "pill-story"
    if normalized == "subtask":
        return "pill-subtask"
    return "pill-task"


def main():
    apply_theme()
    st.markdown(
        """
        <div class="hero">
          <h1>Jira Automation Studio</h1>
          <p>Turn raw requirements into a clean Jira ticket hierarchy with full control and review.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "config" not in st.session_state:
        st.session_state.config = Config()

    if "tickets" not in st.session_state:
        st.session_state.tickets = []

    if "projects" not in st.session_state:
        st.session_state.projects = []

    if "creating" not in st.session_state:
        st.session_state.creating = False

    if "created" not in st.session_state:
        st.session_state.created = False

    if "last_requirements" not in st.session_state:
        st.session_state.last_requirements = ""

    if "created_tickets" not in st.session_state:
        st.session_state.created_tickets = []

    if "create_errors" not in st.session_state:
        st.session_state.create_errors = []

    with st.sidebar:
        st.markdown("<div class='section-title'>Configuration</div>", unsafe_allow_html=True)
        with st.form("config_form", clear_on_submit=False):
            config = st.session_state.config
            jira_url = st.text_input("Jira URL", value=config.jira_url, placeholder="https://your-domain.atlassian.net")
            jira_email = st.text_input("Jira Email", value=config.jira_email)
            jira_api_token = st.text_input("Jira API Token", value=config.jira_api_token, type="password")
            openai_api_key = st.text_input("OpenAI API Key", value=config.openai_api_key, type="password")
            persist = st.checkbox("Save to .env", value=False)
            submitted = st.form_submit_button("Apply Configuration", disabled=st.session_state.creating)

        if submitted:
            st.session_state.config = build_config_from_inputs(
                jira_url, jira_email, jira_api_token, openai_api_key, persist
            )
            st.success("Configuration applied for this session.")

        config = st.session_state.config
        if config.is_configured():
            jira_client = JiraClient(config)
            if st.button("Test Jira Connection", disabled=st.session_state.creating):
                with st.spinner("Testing connection..."):
                    ok = jira_client.test_connection()
                if ok:
                    st.success("Connected to Jira.")
                else:
                    st.error("Failed to connect to Jira. Check your credentials.")
        else:
            st.warning("Provide Jira credentials to continue.")

    config = st.session_state.config
    if not (config.is_configured() and config.is_llm_configured()):
        st.info("Set Jira and OpenAI credentials to unlock analysis and ticket creation.")
        return

    jira_client = JiraClient(config)

    st.markdown("<div class='section-title'>Project</div>", unsafe_allow_html=True)
    project_col, refresh_col = st.columns([3, 1])
    with refresh_col:
        if st.button("Load Projects", disabled=st.session_state.creating):
            with st.spinner("Loading projects..."):
                st.session_state.projects = jira_client.get_projects()

    projects = st.session_state.projects
    if not projects:
        st.info("Load projects to choose a destination.")
        return

    project_map = {f"{p['key']} - {p['name']}": p["key"] for p in projects}
    selection = project_col.selectbox("Select Project", list(project_map.keys()))
    project_key = project_map[selection]

    st.markdown("<div class='section-title'>Requirements</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='card'>Paste requirements in plain English. Finish with an actionable summary.</div>",
        unsafe_allow_html=True,
    )
    requirements = st.text_area(
        "Requirements",
        height=220,
        placeholder="Describe the problem, desired outcomes, constraints, and acceptance criteria.",
        label_visibility="collapsed",
    )

    if st.session_state.created and requirements.strip() != st.session_state.last_requirements:
        st.info("New requirements detected. Run analysis again to enable ticket creation.")

    analyze_col, clear_col = st.columns([2, 1])
    with analyze_col:
        if st.button("Analyze Requirements", disabled=st.session_state.creating):
            if not requirements.strip():
                st.error("Please provide requirements before analyzing.")
            else:
                with st.spinner("Analyzing requirements with AI..."):
                    analyzer = LLMAnalyzer(config)
                    st.session_state.tickets = analyzer.analyze_requirements(requirements)
                st.session_state.last_requirements = requirements.strip()
                st.session_state.created = False
                st.session_state.created_tickets = []
                st.session_state.create_errors = []
                if st.session_state.tickets:
                    st.success(f"Generated {len(st.session_state.tickets)} tickets.")
                else:
                    st.error("No tickets were generated. Try refining the requirements.")

    with clear_col:
        if st.button("Clear Draft", disabled=st.session_state.creating):
            st.session_state.tickets = []
            st.session_state.created = False
            st.session_state.last_requirements = ""
            st.session_state.created_tickets = []
            st.session_state.create_errors = []

    tickets = st.session_state.tickets
    if not tickets:
        return

    st.markdown("<div class='section-title'>Tickets Preview</div>", unsafe_allow_html=True)
    for ticket in tickets:
        st.markdown(
            f"<div class='card'><span class='ticket-pill {pill_class(ticket.get('type', ''))}'>"
            f"{ticket.get('type')}</span><strong>{ticket.get('summary')}</strong>"
            f"<div class='subtle'>{ticket.get('description', '')[:140]}</div></div>",
            unsafe_allow_html=True,
        )
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    st.dataframe(tickets_table(tickets), use_container_width=True, hide_index=True)

    st.markdown("<div class='section-title'>Edit Tickets</div>", unsafe_allow_html=True)
    for i, ticket in enumerate(tickets):
        with st.expander(describe_ticket(ticket, tickets), expanded=False):
            ticket["type"] = st.selectbox(
                "Type",
                ["Epic", "Story", "Task", "Subtask"],
                index=["Epic", "Story", "Task", "Subtask"].index(ticket.get("type", "Task")),
                key=f"type_{i}",
            )
            ticket["summary"] = st.text_input(
                "Summary", value=ticket.get("summary", ""), key=f"summary_{i}"
            )
            ticket["description"] = st.text_area(
                "Description",
                value=ticket.get("description", ""),
                key=f"description_{i}",
                height=140,
            )
            criteria_text = "\n".join(ticket.get("acceptance_criteria", []))
            criteria_text = st.text_area(
                "Acceptance Criteria (one per line)",
                value=criteria_text,
                key=f"criteria_{i}",
                height=120,
            )
            ticket["acceptance_criteria"] = [c.strip() for c in criteria_text.splitlines() if c.strip()]

            options = build_parent_options(i, tickets)
            current_parent = ticket.get("parent_index")
            current_label = next((label for label, idx in options if idx == current_parent), "None")
            parent_label = st.selectbox(
                "Parent Ticket",
                [label for label, _ in options],
                index=[label for label, _ in options].index(current_label),
                key=f"parent_{i}",
            )
            selected_idx = next(idx for label, idx in options if label == parent_label)
            ticket["parent_index"] = selected_idx

    st.markdown("<div class='section-title'>Create in Jira</div>", unsafe_allow_html=True)
    confirm = st.checkbox(
        "I confirm these tickets should be created in Jira.",
        disabled=st.session_state.creating or st.session_state.created,
    )

    create_disabled = (
        st.session_state.creating
        or st.session_state.created
        or not confirm
        or not tickets
        or requirements.strip() != st.session_state.last_requirements
    )
    if not st.session_state.created:
        if st.button("Create Tickets", disabled=create_disabled):
            st.session_state.creating = True
            with st.spinner("Creating tickets in Jira..."):
                app = JiraAutomationApp()
                app.jira_client = jira_client
                app.ui = SilentUI()
                created, errors = app.create_tickets(project_key, tickets)
            st.session_state.creating = False
            st.session_state.created = True
            st.session_state.created_tickets = created
            st.session_state.create_errors = errors

    if st.session_state.created_tickets:
        st.success(f"Created {len(st.session_state.created_tickets)} tickets in Jira.")
        st.dataframe(
            st.session_state.created_tickets,
            use_container_width=True,
            hide_index=True,
            column_config={
                "url": st.column_config.LinkColumn("URL"),
            },
        )
    if st.session_state.create_errors:
        st.warning("Some tickets could not be created.")
        st.text("\n".join(st.session_state.create_errors))


if __name__ == "__main__":
    main()
