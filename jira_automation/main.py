"""Main application entry point."""

import os
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from rich.console import Console

from .config import Config
from .jira_client import JiraClient
from .llm_analyzer import LLMAnalyzer
from .console_ui import ConsoleUI

console = Console()


class JiraAutomationApp:
    """Main application class."""
    
    def __init__(self):
        self.config = Config()
        self.ui = ConsoleUI()
        self.jira_client = None
        self.llm_analyzer = None
    
    def setup_configuration(self):
        """Handle initial configuration."""
        if not self.config.is_configured():
            self.ui.console.print("[yellow]First time setup required.[/yellow]")
            config_data = self.ui.get_initial_config()
            
            # Save non-sensitive config
            self.config.save_config(config_data['jira_url'])
            
            # Check if LLM is configured
            openai_key = self.config.openai_api_key
            if not openai_key:
                self.ui.console.print("[yellow]LLM configuration required.[/yellow]")
                openai_key = self.ui.get_llm_config()
            
            # Save to .env file
            self.config.save_env_file(
                config_data['jira_url'],
                config_data['jira_email'],
                config_data['jira_api_token'],
                openai_key
            )
            self.ui.console.print("[green]Configuration saved to .env file[/green]")
            
            # Reload config
            from dotenv import load_dotenv
            load_dotenv(override=True)
            self.config = Config()
        
        if not self.config.is_llm_configured():
            self.ui.console.print("[yellow]LLM configuration required.[/yellow]")
            api_key = self.ui.get_llm_config()
            # Update .env file
            env_file = Path.cwd() / ".env"
            if env_file.exists():
                lines = []
                key_updated = False
                with open(env_file, 'r') as f:
                    for line in f:
                        if line.startswith('OPENAI_API_KEY='):
                            lines.append(f'OPENAI_API_KEY={api_key}\n')
                            key_updated = True
                        else:
                            lines.append(line)
                if not key_updated:
                    lines.append(f'\nOPENAI_API_KEY={api_key}\n')
                with open(env_file, 'w') as f:
                    f.writelines(lines)
            else:
                # Create new .env file
                self.config.save_env_file(
                    self.config.jira_url,
                    self.config.jira_email,
                    self.config.jira_api_token,
                    api_key
                )
            from dotenv import load_dotenv
            load_dotenv(override=True)
            self.config = Config()
    
    def initialize_clients(self):
        """Initialize Jira and LLM clients."""
        if not self.config.is_configured():
            self.ui.console.print("[red]Configuration incomplete. Please check your .env file.[/red]")
            sys.exit(1)
        
        self.jira_client = JiraClient(self.config)
        
        # Test connection
        self.ui.console.print("[yellow]Testing Jira connection...[/yellow]")
        if not self.jira_client.test_connection():
            self.ui.console.print("[red]Failed to connect to Jira. Please check your credentials.[/red]")
            sys.exit(1)
        self.ui.console.print("[green]✓ Connected to Jira[/green]")
        
        if not self.config.is_llm_configured():
            self.ui.console.print("[red]LLM configuration missing. Please set OPENAI_API_KEY in .env file.[/red]")
            sys.exit(1)
        
        try:
            self.llm_analyzer = LLMAnalyzer(self.config)
            self.ui.console.print("[green]✓ LLM configured[/green]")
        except Exception as e:
            self.ui.console.print(f"[red]Error initializing LLM: {e}[/red]")
            sys.exit(1)
    
    def select_project_interactive(self):
        """Select project interactively."""
        projects = self.jira_client.get_projects()
        if not projects:
            self.ui.console.print("[red]No projects found. Please check your Jira permissions.[/red]")
            sys.exit(1)
        
        selected_project = self.ui.select_project(projects)
        if not selected_project:
            self.ui.console.print("[red]No project selected. Exiting.[/red]")
            sys.exit(1)
        
        return selected_project['key']
    
    def process_requirements(self, requirements: str) -> List[Dict]:
        """Process requirements using LLM."""
        import sys
        
        if not requirements.strip():
            print("[ERROR] No requirements provided.", flush=True)
            return []
        
        # Verify LLM analyzer is initialized
        if not self.llm_analyzer:
            print("[ERROR] LLM analyzer not initialized!", flush=True)
            return []
        
        # Show clear message before processing
        print("\n[INFO] 🤖 Analyzing requirements with AI...", flush=True)
        print("[INFO] This may take 10-30 seconds. Please wait...", flush=True)
        
        # Process requirements
        try:
            print("[DEBUG] Calling LLM analyzer...", flush=True)
            tickets = self.llm_analyzer.analyze_requirements(requirements)
            print(f"[DEBUG] Received {len(tickets) if tickets else 0} tickets from analyzer", flush=True)
        except Exception as e:
            print(f"\n[ERROR] Error during analysis: {e}", flush=True)
            import traceback
            print(f"[ERROR] Details: {str(e)}", flush=True)
            print(f"[DEBUG] {traceback.format_exc()}", flush=True)
            return []
        
        if not tickets:
            print("[ERROR] Failed to generate ticket structure.", flush=True)
            return []
        
        print(f"[SUCCESS] ✓ Successfully generated {len(tickets)} tickets!\n", flush=True)
        return tickets
    
    def review_and_edit_tickets(self, tickets: List[Dict]) -> List[Dict]:
        """Allow user to review and edit tickets."""
        self.ui.display_tickets_preview(tickets)
        
        while True:
            action = self.ui.console.input(
                "\n[bold]Actions:[/bold] [cyan]e[/cyan]dit ticket, [cyan]d[/cyan]elete ticket, [cyan]c[/cyan]ontinue, [cyan]q[/cyan]uit: "
            ).strip().lower()
            
            if action == 'q':
                self.ui.console.print("[yellow]Exiting without creating tickets.[/yellow]")
                sys.exit(0)
            elif action == 'c':
                break
            elif action == 'e':
                try:
                    ticket_num = int(self.ui.console.input("Enter ticket number to edit: "))
                    idx = ticket_num - 1
                    if 0 <= idx < len(tickets):
                        tickets[idx] = self.ui.edit_ticket(tickets[idx])
                        self.ui.display_tickets_preview(tickets)
                    else:
                        self.ui.console.print("[red]Invalid ticket number[/red]")
                except ValueError:
                    self.ui.console.print("[red]Please enter a valid number[/red]")
            elif action == 'd':
                try:
                    ticket_num = int(self.ui.console.input("Enter ticket number to delete: "))
                    idx = ticket_num - 1
                    if 0 <= idx < len(tickets):
                        tickets.pop(idx)
                        # Reindex
                        for i, ticket in enumerate(tickets):
                            ticket['index'] = i
                        self.ui.display_tickets_preview(tickets)
                    else:
                        self.ui.console.print("[red]Invalid ticket number[/red]")
                except ValueError:
                    self.ui.console.print("[red]Please enter a valid number[/red]")
        
        return tickets
    
    def create_tickets(self, project_key: str, tickets: List[Dict]) -> Tuple[List[Dict], List[str]]:
        """Create tickets in Jira in correct order."""
        created_tickets = []
        errors = []
        
        # Create mapping from original index to ticket
        index_to_ticket = {ticket['index']: ticket for ticket in tickets}
        
        # Sort tickets: Epics first, then Stories/Tasks, then Subtasks
        # Map common variations to standard types
        type_order = {'Epic': 0, 'Story': 1, 'Task': 1, 'Subtask': 2, 'Sub-task': 2}
        sorted_tickets = sorted(tickets, key=lambda t: (type_order.get(t['type'], 1), t['index']))
        
        # Map from original index to created ticket key
        index_to_key = {}
        
        def is_subtask_type(issue_type: str) -> bool:
            normalized = issue_type.strip().lower().replace("-", "").replace(" ", "")
            return normalized == "subtask"

        def find_parent_chain(start_index: int) -> List[int]:
            chain = []
            current = start_index
            visited = set()
            while current is not None and current not in visited:
                visited.add(current)
                chain.append(current)
                parent = index_to_ticket.get(current, {}).get("parent_index")
                current = parent
            return chain

        def find_first_non_subtask_ancestor(start_index: int) -> Optional[int]:
            for idx in find_parent_chain(start_index):
                parent_ticket = index_to_ticket.get(idx)
                if not parent_ticket:
                    continue
                if not is_subtask_type(parent_ticket.get("type", "")):
                    return idx
            return None

        def find_epic_ancestor(start_index: int) -> Optional[int]:
            for idx in find_parent_chain(start_index):
                parent_ticket = index_to_ticket.get(idx)
                if not parent_ticket:
                    continue
                if parent_ticket.get("type", "").strip().lower() == "epic":
                    return idx
            return None

        # Create tickets in order
        for ticket in sorted_tickets:
            self.ui.display_creation_progress(
                len(created_tickets) + 1,
                len(tickets),
                ticket['summary']
            )
            
            # Determine parent key
            parent_key = None
            epic_key = None
            issue_type = ticket["type"]

            parent_index = ticket.get("parent_index")
            if parent_index is not None:
                non_subtask_parent_idx = find_first_non_subtask_ancestor(parent_index)
                epic_parent_idx = find_epic_ancestor(parent_index)

                if is_subtask_type(issue_type):
                    if non_subtask_parent_idx is None:
                        errors.append(f"Skipped subtask (missing parent): {ticket['summary']}")
                        continue

                    parent_ticket = index_to_ticket.get(non_subtask_parent_idx)
                    parent_type = parent_ticket.get("type", "").strip().lower()
                    if parent_type == "epic":
                        issue_type = "Task"
                        epic_key = index_to_key.get(non_subtask_parent_idx)
                        if not epic_key:
                            errors.append(f"Skipped subtask (missing parent): {ticket['summary']}")
                            continue
                        errors.append(f"Promoted subtask to Task under Epic: {ticket['summary']}")
                    else:
                        parent_key = index_to_key.get(non_subtask_parent_idx)
                        if not parent_key:
                            errors.append(f"Skipped subtask (missing parent): {ticket['summary']}")
                            continue
                else:
                    if epic_parent_idx is not None:
                        epic_key = index_to_key.get(epic_parent_idx)

            # Format description with acceptance criteria
            description = ticket.get('description', '')
            if ticket.get('acceptance_criteria'):
                description += "\n\nAcceptance Criteria:\n"
                for ac in ticket['acceptance_criteria']:
                    description += f"• {ac}\n"
            
            # Create issue
            result = self.jira_client.create_issue(
                project_key=project_key,
                issue_type=issue_type,
                summary=ticket['summary'],
                description=description,
                parent_key=parent_key,
                epic_key=epic_key
            )
            
            if result:
                issue_key = result['key']
                # Store mapping from original index to created key
                index_to_key[ticket['index']] = issue_key
                created_tickets.append({
                    'key': issue_key,
                    'type': ticket['type'],
                    'summary': ticket['summary'],
                    'url': self.jira_client.get_issue_url(issue_key),
                    'original_index': ticket['index']
                })
                ticket['key'] = issue_key
            else:
                errors.append(f"Failed to create: {ticket['summary']}")
        
        return created_tickets, errors
    
    def run(self):
        """Main application flow."""
        self.ui.welcome()
        
        # Setup configuration
        self.setup_configuration()
        
        # Initialize clients
        self.initialize_clients()
        
        # Select project (always required)
        project_key = self.select_project_interactive()
        self.ui.console.print(f"\n[green]Selected project: {project_key}[/green]\n")
        
        # Get requirements
        import sys
        print("\n[VERBOSE] About to call get_requirements()", flush=True)
        print("", end="", flush=True)  # Ensure newline
        
        requirements = self.ui.get_requirements()
        print("[VERBOSE] Returned from get_requirements()", flush=True)
        print("", flush=True)  # Force flush
        
        print(f"[VERBOSE] Requirements length: {len(requirements)}, stripped: {len(requirements.strip())}", flush=True)
        
        if not requirements.strip():
            print("\n[ERROR] No requirements provided. Exiting.", flush=True)
            sys.exit(1)
        
        # Show immediate feedback using print for reliability
        word_count = len(requirements.split())
        char_count = len(requirements)
        print(f"\n[INFO] Processing: {word_count} words, {char_count} characters", flush=True)
        
        # Process requirements
        print("[VERBOSE] About to call process_requirements()", flush=True)
        print("[INFO] Starting AI analysis...", flush=True)
        tickets = self.process_requirements(requirements)
        print("[VERBOSE] Returned from process_requirements()", flush=True)
        print("", flush=True)  # Force flush after processing
        
        print(f"[VERBOSE] Tickets returned: {len(tickets) if tickets else 0}", flush=True)
        
        if not tickets:
            print("[ERROR] No tickets generated. Exiting.", flush=True)
            self.ui.console.print("[red]No tickets generated. Exiting.[/red]")
            sys.exit(1)
        
        print(f"[VERBOSE] About to call review_and_edit_tickets() with {len(tickets)} tickets", flush=True)
        
        # Review and edit
        tickets = self.review_and_edit_tickets(tickets)
        print(f"[VERBOSE] Returned from review_and_edit_tickets() with {len(tickets)} tickets", flush=True)
        
        # Confirm creation
        if not self.ui.confirm_creation():
            self.ui.console.print("[yellow]Creation cancelled.[/yellow]")
            sys.exit(0)
        
        # Create tickets
        created_tickets, errors = self.create_tickets(project_key, tickets)
        
        # Display report
        self.ui.display_final_report(created_tickets, errors)


def main():
    """Entry point."""
    app = JiraAutomationApp()
    app.run()


if __name__ == "__main__":
    main()
