# Jira Ticket Automation

Python application that converts free-text requirements into a complete structure of Jira Cloud tickets, using an LLM to interpret, organize, and enrich the information.

## Features

- ✅ Persistent initial configuration (first run only)
- ✅ Mandatory board selection on each run
- ✅ Requirements analysis with AI (LLM)
- ✅ Automatic hierarchy generation (Epics → Stories/Tasks → Sub-tasks)
- ✅ Interactive preview and editing before creating tickets
- ✅ Controlled creation in Jira Cloud (only after confirmation)
- ✅ Final report with ticket IDs and links
- ✅ Secure credential management via environment variables

## Requirements

- Python 3.8 or higher
- Jira Cloud account with permissions to create tickets
- Jira Cloud API Token
- OpenAI API Key (for the LLM)

## Installation

1. Clone or download the repository:
```bash
cd jira-brandandbot-automation
```

2. Create a virtual environment (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp env.example .env
```

Edit the `.env` file with your credentials:
```env
JIRA_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-jira-api-token
OPENAI_API_KEY=your-openai-api-key
```

### Getting Jira API Token

1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Create a new API token
3. Copy the token and add it to your `.env` file

### Getting OpenAI API Key

1. Go to https://platform.openai.com/api-keys
2. Create a new API key
3. Copy the key and add it to your `.env` file

## Usage

Run the application:
```bash
python main.py
```

### Application Flow

1. **First run**: The app will prompt for basic configuration (URL, email, token). This is saved locally.

2. **Project selection**: On each run, select the project/board where tickets will be created.

3. **Requirements input**: Enter your requirements in free text. Press Enter twice to finish.

4. **AI analysis**: The app will analyze the requirements and generate a ticket structure.

5. **Preview and edit**: Review the generated structure. You can:
   - Edit tickets (press `e` and the ticket number)
   - Delete tickets (press `d` and the ticket number)
   - Continue (press `c`)
   - Quit without creating (press `q`)

6. **Confirmation**: Confirm ticket creation in Jira.

7. **Final report**: A report with created tickets and their links will be displayed.

## API Server: Email → Jira (Webhook)

FastAPI server that receives emails from Google Apps Script, analyzes content with AI, and automatically creates Jira tasks.

### Additional environment variables

```env
WEBHOOK_SECRET=your-shared-secret-with-appscript
JIRA_EMAIL_PROJECT_KEY=PROJ   # Project where tasks will be created
```

### Run server locally

```bash
uvicorn server:app --reload --port 8000
```

The `/webhook/email` endpoint accepts POST with the email JSON (message_id, from, subject, body.plain, body.html).

### Deploy to Render

1. Connect the repo on [Render](https://render.com)
2. Use the `render.yaml` blueprint or create a Web Service
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn server:app --host 0.0.0.0 --port $PORT`
5. Configure environment variables (JIRA_*, OPENAI_API_KEY, WEBHOOK_SECRET, JIRA_EMAIL_PROJECT_KEY)

Webhook URL will be: `https://your-service.onrender.com/webhook/email`

### Google Apps Script

In your script, configure:

```javascript
const WEBHOOK_URL = "https://your-service.onrender.com/webhook/email";
const WEBHOOK_SECRET = "same-secret-as-WEBHOOK_SECRET";
```

The payload must include: `message_id`, `thread_id`, `from`, `to`, `date`, `subject`, `body: { plain, html }`.

## Project Structure

```
jira-brandandbot-automation/
├── jira_automation/
│   ├── __init__.py
│   ├── config.py          # Configuration management
│   ├── jira_client.py     # Jira Cloud API client
│   ├── llm_analyzer.py    # LLM integration
│   ├── console_ui.py      # Console interface
│   └── main.py            # Main logic
├── main.py                # Entry point (console)
├── server.py              # FastAPI API (email→Jira webhook)
├── streamlit_app.py       # Streamlit UI
├── render.yaml            # Render configuration
├── Procfile               # Start command (Render/Heroku)
├── requirements.txt       # Dependencies
├── env.example            # Environment variables example
├── .gitignore
└── README.md
```

## Security

- Sensitive credentials (API keys, tokens) are managed via environment variables (`.env` file)
- The `.env` file is in `.gitignore` and is not committed
- Persistent config only stores the Jira URL (non-sensitive)
- Project selection is always explicit to avoid mistakes

## Troubleshooting

### Jira connection error
- Verify the Jira URL is correct
- Confirm the API token is valid
- Check you have permissions to create tickets in the project

### LLM error
- Verify the OpenAI API key is valid
- Confirm you have credits available in your OpenAI account

### Projects not showing
- Verify you have access to the projects in Jira
- Confirm credentials are correct

## License

Internal use only.
