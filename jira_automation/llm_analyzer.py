"""LLM integration for analyzing and structuring requirements."""

from typing import List, Dict, Optional
from openai import OpenAI
from rich.console import Console
import json

from .config import Config

console = Console()


class LLMAnalyzer:
    """Analyzes requirements using LLM and structures them into Jira tickets."""
    
    def __init__(self, config: Config):
        self.config = config
        if not config.openai_api_key:
            raise ValueError("OpenAI API key not configured")
        self.client = OpenAI(api_key=config.openai_api_key)
    
    def analyze_requirements(self, requirements: str) -> List[Dict]:
        """Analyze requirements and generate ticket structure."""
        import sys
        print("[DEBUG] Preparing prompt for LLM...", flush=True)
        
        prompt = f"""Analyze the following requirements and generate a structured hierarchy of Jira tickets.

Requirements:
{requirements}

Generate a JSON structure with the following format:
{{
  "tickets": [
    {{
      "type": "Epic" | "Story" | "Task" | "Subtask",
      "summary": "Title of the ticket",
      "description": "Detailed description",
      "acceptance_criteria": ["Criterion 1", "Criterion 2", ...],
      "parent_index": null or index of parent ticket (for Stories/Tasks/Subtasks)
    }}
  ]
}}

Rules:
1. Start with Epics at the top level (parent_index: null)
2. Stories and Tasks should reference their parent Epic (parent_index: 0, 1, etc.)
3. Subtasks should reference their parent Story or Task
4. Each ticket must have clear acceptance criteria
5. Descriptions should be detailed and actionable
6. Organize logically by feature or functionality
7. Use "Subtask" (not "Sub-task") for sub-tasks

Return ONLY valid JSON, no additional text."""

        try:
            import sys
            print("[DEBUG] Calling OpenAI API...", flush=True)
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing software requirements and structuring them into Jira tickets. Always return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            print("[DEBUG] Received response from OpenAI, parsing...", flush=True)
            
            print("[DEBUG] Checking response...", flush=True)
            
            if not response.choices or not response.choices[0].message.content:
                print("[ERROR] Empty response from LLM", flush=True)
                console.print("[red]Error: Empty response from LLM[/red]")
                return []
            
            content = response.choices[0].message.content
            print(f"[DEBUG] Response content length: {len(content)}", flush=True)
            print(f"[DEBUG] First 200 chars: {content[:200]}", flush=True)
            
            print("[DEBUG] Parsing JSON...", flush=True)
            result = json.loads(content)
            print("[DEBUG] JSON parsed successfully", flush=True)
            
            # Process and validate the structure
            tickets = result.get('tickets', [])
            print(f"[DEBUG] Found {len(tickets)} tickets in response", flush=True)
            
            if not tickets:
                print("[WARNING] No tickets generated from requirements", flush=True)
                console.print("[yellow]Warning: No tickets generated from requirements[/yellow]")
                return []
            
            print("[DEBUG] Processing tickets...", flush=True)
            processed = self._process_tickets(tickets)
            print(f"[DEBUG] Processed {len(processed)} tickets", flush=True)
            return processed
            
        except json.JSONDecodeError as e:
            console.print(f"[red]Error parsing LLM response: {e}[/red]")
            if 'content' in locals():
                console.print(f"[red]Response was: {content[:500]}[/red]")
            return []
        except Exception as e:
            console.print(f"[red]Error calling LLM: {e}[/red]")
            import traceback
            console.print(f"[red]Traceback: {traceback.format_exc()}[/red]")
            return []
    
    def _process_tickets(self, tickets: List[Dict]) -> List[Dict]:
        """Process and validate ticket structure."""
        processed = []
        
        for idx, ticket in enumerate(tickets):
            processed_ticket = {
                'index': idx,
                'type': ticket.get('type', 'Task'),
                'summary': ticket.get('summary', 'Untitled'),
                'description': ticket.get('description', ''),
                'acceptance_criteria': ticket.get('acceptance_criteria', []),
                'parent_index': ticket.get('parent_index'),
                'key': None  # Will be set after creation
            }
            processed.append(processed_ticket)
        
        return processed

    def extract_task_from_email(self, subject: str, from_addr: str, body: str) -> Optional[Dict]:
        """
        Extract a single Jira task (summary + description) from email content.
        Identifies what the sender is asking or requesting.
        """
        prompt = f"""Analyze the following email and extract the sender's request or inquiry.

Subject: {subject}
From: {from_addr}

Email body:
{body[:4000]}

Generate a JSON with this format:
{{
  "summary": "Short descriptive title of the request (max 80 chars)",
  "description": "Detailed description including: what the sender is asking, relevant email context, and any important details"
}}

Rules:
1. summary must be concise and in English
2. description must include the key information from the email
3. If the email has no clear request, use a generic summary like "Email inquiry from [sender]" and use the body as description
4. Return ONLY valid JSON, no additional text."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an assistant that extracts requests from emails to create Jira tasks. Respond only with valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            if not response.choices or not response.choices[0].message.content:
                return None

            content = response.choices[0].message.content
            result = json.loads(content)
            summary = result.get("summary", "Email inquiry")
            description = result.get("description", body[:2000] if body else "")
            return {"summary": summary[:255], "description": description}
        except (json.JSONDecodeError, Exception) as e:
            console.print(f"[red]Error extracting task from email: {e}[/red]")
            return None

