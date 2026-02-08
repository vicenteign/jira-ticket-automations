"""Interactive console UI for the application."""

from typing import List, Dict, Optional
from contextlib import contextmanager
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.text import Text
from rich.markdown import Markdown
from rich.status import Status

console = Console()


class ConsoleUI:
    """Handles all console interactions."""
    
    def __init__(self):
        self.console = console
    
    def welcome(self):
        """Display welcome message."""
        welcome_text = """
# Jira Brand and Bot Automation

Convert your requirements into structured Jira tickets using AI.
"""
        self.console.print(Panel(Markdown(welcome_text), title="Welcome", border_style="green"))
    
    def get_initial_config(self) -> Dict[str, str]:
        """Get initial configuration from user."""
        self.console.print("\n[bold cyan]Initial Configuration[/bold cyan]")
        self.console.print("Please provide your Jira Cloud configuration:\n")
        
        jira_url = Prompt.ask("Jira URL", default="https://your-domain.atlassian.net")
        jira_email = Prompt.ask("Jira Email")
        jira_api_token = Prompt.ask("Jira API Token", password=True)
        
        return {
            'jira_url': jira_url,
            'jira_email': jira_email,
            'jira_api_token': jira_api_token
        }
    
    def get_llm_config(self) -> str:
        """Get LLM API key from user."""
        self.console.print("\n[bold cyan]LLM Configuration[/bold cyan]")
        api_key = Prompt.ask("OpenAI API Key", password=True)
        return api_key
    
    def select_project(self, projects: List[Dict]) -> Optional[Dict]:
        """Let user select a project/board."""
        if not projects:
            self.console.print("[red]No projects available.[/red]")
            return None
        
        self.console.print("\n[bold cyan]Select a Project/Board:[/bold cyan]\n")
        
        # Display projects
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=4)
        table.add_column("Key", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Type", style="yellow")
        
        for idx, project in enumerate(projects, 1):
            table.add_row(
                str(idx),
                project['key'],
                project['name'],
                project['type']
            )
        
        self.console.print(table)
        
        while True:
            try:
                choice = Prompt.ask("\nSelect project number", default="1")
                idx = int(choice) - 1
                if 0 <= idx < len(projects):
                    return projects[idx]
                else:
                    self.console.print(f"[red]Please select a number between 1 and {len(projects)}[/red]")
            except ValueError:
                self.console.print("[red]Please enter a valid number[/red]")
    
    def get_requirements(self) -> str:
        """Get requirements input from user."""
        import sys
        print("\n[VERBOSE] Entering get_requirements()", flush=True)
        
        self.console.print("\n[bold cyan]Enter Requirements[/bold cyan]")
        self.console.print("Enter your requirements (press Enter twice or type /done to finish):\n")
        sys.stdout.flush()
        print("[VERBOSE] Prompt displayed, waiting for input...", flush=True)
        
        lines = []
        empty_lines = 0
        line_count = 0
        
        while True:
            try:
                print(f"[VERBOSE] Waiting for input (line {line_count + 1}, empty_lines={empty_lines})...", flush=True)
                line = input()
                line_count += 1
                print(f"[VERBOSE] Received line {line_count}: '{line[:50]}...' (empty_lines={empty_lines})", flush=True)
                
                if line.strip().lower() == "/done":
                    print("[VERBOSE] /done received, finishing input", flush=True)
                    break

                if not line.strip():
                    empty_lines += 1
                    print(f"[VERBOSE] Empty line detected, count={empty_lines}", flush=True)
                    if empty_lines >= 2:
                        print("[VERBOSE] Two empty lines detected, finishing input", flush=True)
                        break
                else:
                    empty_lines = 0
                    lines.append(line)
                    print(f"[VERBOSE] Added line to list, total lines={len(lines)}", flush=True)
            except EOFError:
                print("[VERBOSE] EOFError caught, breaking", flush=True)
                break
            except KeyboardInterrupt:
                print("[VERBOSE] KeyboardInterrupt caught", flush=True)
                self.console.print("\n[yellow]Input cancelled by user.[/yellow]")
                sys.stdout.flush()
                return ""
        
        requirements = '\n'.join(lines)
        print(f"[VERBOSE] Building requirements string, {len(lines)} lines, {len(requirements)} chars", flush=True)
        
        # Always print feedback immediately
        print("", flush=True)  # New line
        self.console.print(f"[green]✓ Requirements received ({len(lines)} lines, {len(requirements)} characters)[/green]")
        sys.stdout.flush()
        print(f"[VERBOSE] Returning from get_requirements(), length={len(requirements)}", flush=True)
        return requirements
    
    @contextmanager
    def show_loading(self, message: str = "Processing..."):
        """Context manager to show loading spinner."""
        try:
            with self.console.status(
                f"[bold yellow]{message}[/bold yellow]", 
                spinner="dots",
                spinner_style="yellow"
            ):
                yield
        finally:
            # Print completion message
            self.console.print("[green]✓ Analysis complete![/green]\n")
    
    def display_tickets_preview(self, tickets: List[Dict]):
        """Display tickets preview for review."""
        self.console.print("\n[bold cyan]Generated Tickets Preview[/bold cyan]\n")
        
        for ticket in tickets:
            parent_info = ""
            if ticket.get('parent_index') is not None:
                parent = tickets[ticket['parent_index']]
                parent_info = f" (Parent: {parent['summary']})"
            
            # Format acceptance criteria
            ac_text = "\n".join([f"  • {ac}" for ac in ticket.get('acceptance_criteria', [])])
            
            content = f"""
[bold]Type:[/bold] {ticket['type']}
[bold]Summary:[/bold] {ticket['summary']}{parent_info}

[bold]Description:[/bold]
{ticket.get('description', 'No description')}

[bold]Acceptance Criteria:[/bold]
{ac_text if ac_text else '  None specified'}
"""
            self.console.print(Panel(content, title=f"Ticket #{ticket['index'] + 1}", border_style="blue"))
    
    def edit_ticket(self, ticket: Dict) -> Dict:
        """Allow user to edit a ticket."""
        self.console.print(f"\n[bold yellow]Editing Ticket #{ticket['index'] + 1}[/bold yellow]")
        self.console.print(f"Current Summary: {ticket['summary']}")
        
        new_summary = Prompt.ask("New summary", default=ticket['summary'])
        new_description = Prompt.ask("New description", default=ticket.get('description', ''))
        
        # Edit acceptance criteria
        self.console.print("\nCurrent acceptance criteria:")
        for ac in ticket.get('acceptance_criteria', []):
            self.console.print(f"  • {ac}")
        
        ac_input = Prompt.ask("New acceptance criteria (comma-separated)", default="")
        new_ac = [ac.strip() for ac in ac_input.split(',') if ac.strip()] if ac_input else ticket.get('acceptance_criteria', [])
        
        return {
            **ticket,
            'summary': new_summary,
            'description': new_description,
            'acceptance_criteria': new_ac
        }
    
    def confirm_creation(self) -> bool:
        """Ask user to confirm ticket creation."""
        return Confirm.ask("\n[bold yellow]Create these tickets in Jira?[/bold yellow]", default=False)
    
    def display_creation_progress(self, current: int, total: int, ticket_summary: str):
        """Display progress during ticket creation."""
        self.console.print(f"[cyan]Creating ticket {current}/{total}: {ticket_summary}[/cyan]")
    
    def display_final_report(self, created_tickets: List[Dict], errors: List[str]):
        """Display final report of created tickets."""
        self.console.print("\n[bold green]Creation Report[/bold green]\n")
        
        if created_tickets:
            table = Table(title="Created Tickets")
            table.add_column("Type", style="cyan")
            table.add_column("Key", style="green")
            table.add_column("Summary", style="white")
            table.add_column("URL", style="blue")
            
            for ticket in created_tickets:
                table.add_row(
                    ticket['type'],
                    ticket['key'],
                    ticket['summary'],
                    ticket['url']
                )
            
            self.console.print(table)
        
        if errors:
            self.console.print("\n[bold red]Errors:[/bold red]")
            for error in errors:
                self.console.print(f"[red]  • {error}[/red]")
        
        self.console.print(f"\n[bold]Total created: {len(created_tickets)}[/bold]")
        if errors:
            self.console.print(f"[bold red]Errors: {len(errors)}[/bold red]")
