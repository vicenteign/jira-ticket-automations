"""Jira Cloud API client."""

import logging
import requests
from typing import List, Dict, Optional
from rich.console import Console

logger = logging.getLogger(__name__)
from rich.table import Table

from .config import Config

console = Console()


class JiraClient:
    """Client for interacting with Jira Cloud API v3."""
    
    def __init__(self, config: Config):
        self.config = config
        self.base_url = config.jira_url.rstrip('/')
        self.headers = config.get_auth_headers()
        self._epic_link_field_id = None
    
    def test_connection(self) -> bool:
        """Test connection to Jira Cloud."""
        try:
            response = requests.get(
                f"{self.base_url}/rest/api/3/myself",
                headers=self.headers,
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            console.print(f"[red]Error testing connection: {e}[/red]")
            return False
    
    def get_projects(self) -> List[Dict]:
        """Get list of available projects/boards."""
        try:
            # Get projects
            response = requests.get(
                f"{self.base_url}/rest/api/3/project",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            projects = response.json()
            
            # Get boards
            boards_response = requests.get(
                f"{self.base_url}/rest/agile/1.0/board",
                headers=self.headers,
                timeout=10
            )
            boards = []
            if boards_response.status_code == 200:
                boards = boards_response.json().get('values', [])
            
            # Combine and format
            result = []
            for project in projects:
                result.append({
                    'key': project['key'],
                    'name': project['name'],
                    'id': project['id'],
                    'type': 'project'
                })
            
            for board in boards:
                project_key = board.get('location', {}).get('projectKey', '')
                if project_key:
                    result.append({
                        'key': project_key,
                        'name': f"{board['name']} (Board)",
                        'id': board['id'],
                        'type': 'board'
                    })
            
            # Remove duplicates by key
            seen = set()
            unique_result = []
            for item in result:
                if item['key'] not in seen:
                    seen.add(item['key'])
                    unique_result.append(item)
            
            return unique_result
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Error fetching projects: {e}[/red]")
            return []
    
    def display_projects(self, projects: List[Dict]):
        """Display projects in a formatted table."""
        table = Table(title="Available Projects/Boards")
        table.add_column("Key", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Type", style="yellow")
        
        for project in projects:
            table.add_row(
                project['key'],
                project['name'],
                project['type']
            )
        
        console.print(table)
    
    def create_issue(
        self,
        project_key: str,
        issue_type: str,
        summary: str,
        description: str,
        parent_key: Optional[str] = None,
        epic_key: Optional[str] = None,
    ) -> Optional[Dict]:
        """Create a Jira issue. Returns None on failure."""
        normalized_type = self._normalize_issue_type(issue_type)

        issue_data = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": self._format_description(description),
                },
                "issuetype": {"name": normalized_type},
            }
        }

        if parent_key:
            issue_data["fields"]["parent"] = {"key": parent_key}
        if epic_key:
            epic_link_field = self._get_epic_link_field_id()
            if epic_link_field:
                issue_data["fields"][epic_link_field] = epic_key
            elif "parent" not in issue_data["fields"]:
                issue_data["fields"]["parent"] = {"key": epic_key}

        try:
            response = requests.post(
                f"{self.base_url}/rest/api/3/issue",
                headers=self.headers,
                json=issue_data,
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            err_msg = str(e)
            err_body = ""
            if e.response is not None and hasattr(e.response, "text"):
                err_body = e.response.text or ""
            logger.error(
                "Jira create_issue failed: %s | status=%s | body=%s",
                err_msg,
                getattr(e.response, "status_code", "?"),
                err_body[:500],
            )
            console.print(f"[red]Error creating issue '{summary}': {e}[/red]")
            if err_body:
                console.print(f"[red]Jira response: {err_body[:300]}[/red]")
            return None
    
    def _normalize_issue_type(self, issue_type: str) -> str:
        """Normalize issue type names for Jira compatibility."""
        type_mapping = {
            'Sub-task': 'Subtask',
            'Sub task': 'Subtask',
            'subtask': 'Subtask',
            'sub-task': 'Subtask'
        }
        return type_mapping.get(issue_type, issue_type)

    def _get_epic_link_field_id(self) -> Optional[str]:
        """Fetch and cache the Epic Link field id for company-managed projects."""
        if self._epic_link_field_id is not None:
            return self._epic_link_field_id

        try:
            response = requests.get(
                f"{self.base_url}/rest/api/3/field",
                headers=self.headers,
                timeout=15
            )
            response.raise_for_status()
            fields = response.json()
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Error fetching Jira fields: {e}[/red]")
            self._epic_link_field_id = None
            return None

        for field in fields:
            if field.get("name", "").strip().lower() == "epic link":
                self._epic_link_field_id = field.get("id")
                return self._epic_link_field_id

        self._epic_link_field_id = None
        return None
    
    def _format_description(self, text: str) -> List[Dict]:
        """Format description text as Jira document format."""
        lines = text.split('\n')
        content = []
        
        for line in lines:
            if line.strip():
                content.append({
                    "type": "paragraph",
                    "content": [{
                        "type": "text",
                        "text": line
                    }]
                })
            else:
                content.append({"type": "paragraph", "content": []})
        
        return content if content else [{"type": "paragraph", "content": []}]
    
    def get_issue_url(self, issue_key: str) -> str:
        """Get the URL for an issue."""
        return f"{self.base_url}/browse/{issue_key}"
