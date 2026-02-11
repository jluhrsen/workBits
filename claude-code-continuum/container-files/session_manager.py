#!/usr/bin/env python3
"""
Claude Code Continuum - Session Manager

Handles session listing, restoration, and continuum repo sync.
"""

import os
import sys
from pathlib import Path
from typing import Optional

class SessionManager:
    """Manages CCC sessions and continuum repository synchronization"""

    def __init__(self):
        self.continuum_repo_url = os.environ.get('CONTINUUM_REPO_URL', '')
        self.workspace_path = Path('/workspace')
        self.continuum_path = Path.home() / '.continuum'

        # Detect Claude account info
        self.claude_account = self._detect_claude_account()

    def _detect_claude_account(self) -> str:
        """Detect which Claude account/auth method is being used"""
        if os.environ.get('CLAUDE_CODE_USE_VERTEX'):
            gcp_id = os.environ.get('GCP_ID', 'unknown')
            return f"Vertex AI ({gcp_id})"
        elif os.environ.get('ANTHROPIC_API_KEY'):
            return "Anthropic API (direct)"
        else:
            return "Unknown"

    def generate_banner(self, workspace_path: str) -> str:
        """Generate startup banner with permissions and configuration"""
        lines = [
            "🌌 Claude Code Continuum",
            "━" * 60,
            f"⚠️  READ/WRITE ACCESS: {workspace_path} (and below)",
            "⚠️  Whitelisted: /tmp",
        ]

        if self.continuum_repo_url:
            lines.append(f"⚠️  Continuum repo: {self.continuum_repo_url}")
        else:
            lines.append("ℹ️  CONTINUUM_REPO_URL not set - sessions local only")
            lines.append("ℹ️  To enable cloud sync:")
            lines.append("    1. Create private git repo")
            lines.append("    2. Set: export CONTINUUM_REPO_URL=git@github.com:you/continuum.git")
            lines.append("    3. Or use: /set_ccc_repo <url> in this session")

        lines.append(f"ℹ️  Claude account: {self.claude_account}")
        lines.append("━" * 60)

        return "\n".join(lines)

    def run(self):
        """Main entrypoint - show banner and start Claude"""
        # Get current workspace
        workspace = os.getcwd()

        # Show banner
        print(self.generate_banner(workspace))
        print()
        sys.stdout.flush()

        # For now, just launch Claude directly
        # TODO: Add session picker, sync, restore logic
        os.execvp('claude', ['claude'] + sys.argv[1:])

def main():
    manager = SessionManager()
    manager.run()

if __name__ == '__main__':
    main()
