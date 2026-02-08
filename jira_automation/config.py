"""Configuration management for Jira automation."""

import os
import yaml
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Manages application configuration."""
    
    def __init__(self):
        self.config_dir = Path.home() / ".jira-automation"
        self.config_file = self.config_dir / "config.yaml"
        self.config_dir.mkdir(exist_ok=True)
        
        # Load environment variables
        self.jira_url = os.getenv("JIRA_URL", "").strip()
        self.jira_email = os.getenv("JIRA_EMAIL", "").strip()
        self.jira_api_token = os.getenv("JIRA_API_TOKEN", "").strip()
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
        
        # Load persistent config
        self._load_config()
    
    def _load_config(self):
        """Load persistent configuration from YAML file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config_data = yaml.safe_load(f) or {}
                    jira_config = config_data.get('jira', {})
                    self.jira_url = self.jira_url or jira_config.get('url', '')
            except Exception:
                pass
    
    def save_config(self, jira_url: str):
        """Save non-sensitive configuration."""
        config_data = {
            'jira': {
                'url': jira_url
            }
        }
        with open(self.config_file, 'w') as f:
            yaml.dump(config_data, f)
    
    def save_env_file(self, jira_url: str, jira_email: str, jira_api_token: str, openai_api_key: str = None):
        """Save credentials to .env file in the project root."""
        env_file = Path.cwd() / ".env"
        env_content = f"""# Jira Cloud Configuration
JIRA_URL={jira_url}
JIRA_EMAIL={jira_email}
JIRA_API_TOKEN={jira_api_token}

# LLM Configuration (OpenAI)
"""
        if openai_api_key:
            env_content += f"OPENAI_API_KEY={openai_api_key}\n"
        else:
            env_content += "OPENAI_API_KEY=your-openai-api-key-here\n"
        
        with open(env_file, 'w') as f:
            f.write(env_content)
    
    def is_configured(self) -> bool:
        """Check if basic configuration exists."""
        return bool(self.jira_url and self.jira_email and self.jira_api_token)
    
    def is_llm_configured(self) -> bool:
        """Check if LLM configuration exists."""
        return bool(self.openai_api_key)
    
    def get_auth_headers(self) -> dict:
        """Get authentication headers for Jira API."""
        import base64
        credentials = f"{self.jira_email}:{self.jira_api_token}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return {
            "Authorization": f"Basic {encoded}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

