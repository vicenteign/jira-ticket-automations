# Client / Recipient Context for Email → Jira

This file is concatenated to the LLM prompt to help it understand the client context and better infer when a request is website-related (`is_website_requirement: true`).

## Website context

The website:
- Manages manuscripts and publications
- Has columns/tables for pending items (e.g. manuscripts, submissions)
- Displays author information

## When to treat as website requirement

- Adding new columns (e.g. pending manuscripts, author highlights)
- New pages or views
- Changes to tables, lists, or dashboards
- UI/UX changes to the web app
- Frontend features or components

## Sender-specific notes

(Add notes about specific senders/domains if needed, e.g. "Emails from @brandandbot.com are usually about the website")
