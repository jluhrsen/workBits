#!/usr/bin/env python3
"""
Claude Code Continuum - Session Manager

Handles session listing, restoration, and continuum repo sync.
"""

import os
import sys
from pathlib import Path
from typing import Optional
from continuum import ContinuumRepo

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

    def sync_continuum(self) -> bool:
        """Sync continuum repository if configured"""
        if not self.continuum_repo_url:
            return False

        print("📡 Syncing continuum repository...")
        try:
            repo = ContinuumRepo(str(self.continuum_path))
            success = repo.clone_or_pull(self.continuum_repo_url)

            if success:
                print("✓ Continuum synced")
            else:
                print("⚠️  Warning: Failed to sync continuum repository")

            return success
        except Exception as e:
            print(f"⚠️  Warning: Failed to sync continuum repository: {e}")
            return False

    def list_sessions(self):
        """List available sessions from continuum"""
        repo = ContinuumRepo(str(self.continuum_path))
        return repo.list_sessions()

    def session_picker(self) -> bool:
        """
        Interactive session picker UI

        Returns:
            True if should launch Claude Code (new or existing session)
            False if user wants to exit
        """
        sessions = self.list_sessions()

        if not sessions:
            # No sessions available - handle corner case
            print("📭 No sessions found")
            print()

            while True:
                response = input("Start new session? (y/n): ").strip().lower()
                if response == 'y':
                    print()
                    print("🚀 Starting new Claude Code session...")
                    print()
                    return True
                elif response == 'n':
                    print()
                    print("👋 Exiting")
                    return False
                else:
                    print("Please enter 'y' or 'n'")

        # TODO: Handle case where sessions exist
        # For now, this is unreachable
        return True

    def run(self):
        """Main entrypoint - show banner, sync, and start Claude"""
        workspace = os.getcwd()

        # Show banner
        print(self.generate_banner(workspace))
        print()

        # Sync continuum if configured
        if self.continuum_repo_url:
            self.sync_continuum()
            print()

        # Show session picker
        should_launch = self.session_picker()

        if should_launch:
            # Launch Claude Code
            os.execvp('claude', ['claude'] + sys.argv[1:])
        else:
            # User chose to exit
            sys.exit(0)

def main():
    manager = SessionManager()
    manager.run()

if __name__ == '__main__':
    main()
