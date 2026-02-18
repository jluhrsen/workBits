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

        # Display available sessions
        print("📚 Available Sessions:")
        print()

        # Sort by timestamp (most recent first)
        sessions.sort(key=lambda s: s.get('timestamp', ''), reverse=True)

        for i, session in enumerate(sessions, 1):
            timestamp = session.get('timestamp', 'unknown')[:19]  # YYYY-MM-DDTHH:MM:SS
            description = session.get('description', 'No description')
            hostname = session.get('hostname', 'unknown')
            workspace = session.get('workspace_path', 'unknown')

            print(f"  {i}. {timestamp} - {description}")
            print(f"     Host: {hostname} | Workspace: {workspace}")
            print()

        # Show options
        print("Options:")
        print("  [1-{}] - Restore session".format(len(sessions)))
        print("  [n]   - New session")
        print("  [q]   - Quit")
        print()

        # Get user choice
        while True:
            choice = input("Choice: ").strip().lower()

            if choice == 'q':
                print()
                print("👋 Exiting")
                return False
            elif choice == 'n':
                print()
                print("🚀 Starting new Claude Code session...")
                print()
                return True
            elif choice.isdigit() and 1 <= int(choice) <= len(sessions):
                selected = sessions[int(choice) - 1]
                self.restore_session(selected)
                print()
                print(f"🔄 Restoring session: {selected['description']}")
                print()
                return True
            else:
                print(f"Invalid choice. Enter 1-{len(sessions)}, 'n', or 'q'")

    def restore_session(self, session_metadata: dict):
        """Restore a session by copying conversation history"""
        import shutil

        session_id = session_metadata['session_id']
        session_dir = self.continuum_path / 'sessions' / session_id

        # Copy conversation history to Claude's history location
        conversation_file = session_dir / 'conversation.jsonl'
        if conversation_file.exists():
            claude_history = Path.home() / '.claude' / 'history.jsonl'
            claude_history.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(conversation_file, claude_history)

    def copy_gcp_credentials(self):
        """Copy GCP credentials file and fix ownership using sudo"""
        import subprocess

        source = Path('/gcp/creds.json')
        target = Path.home() / '.config' / 'gcloud' / 'application_default_credentials.json'

        if source.exists():
            # Create target directory
            target.parent.mkdir(parents=True, exist_ok=True)

            # Copy file using sudo (to read root-owned file)
            subprocess.run(['sudo', 'cp', str(source), str(target)], check=True)

            # Fix ownership to claude user
            subprocess.run(['sudo', 'chown', 'claude:claude', str(target)], check=True)

    def copy_ssh_credentials(self):
        """Copy SSH keys and known_hosts, fix ownership using sudo"""
        import subprocess

        ssh_dir = Path.home() / '.ssh'
        ssh_dir.mkdir(mode=0o700, exist_ok=True)

        # Copy continuum deploy key if mounted
        continuum_key_source = Path('/tmp/host-ssh/continuum_key')
        continuum_key_target = ssh_dir / 'continuum_key'
        if continuum_key_source.exists():
            subprocess.run(['sudo', 'cp', str(continuum_key_source), str(continuum_key_target)], check=True)
            subprocess.run(['sudo', 'chown', 'claude:claude', str(continuum_key_target)], check=True)
            subprocess.run(['sudo', 'chmod', '600', str(continuum_key_target)], check=True)

        # Copy known_hosts if mounted
        known_hosts_source = Path('/tmp/host-ssh/known_hosts')
        known_hosts_target = ssh_dir / 'known_hosts'
        if known_hosts_source.exists():
            subprocess.run(['sudo', 'cp', str(known_hosts_source), str(known_hosts_target)], check=True)
            subprocess.run(['sudo', 'chown', 'claude:claude', str(known_hosts_target)], check=True)
            subprocess.run(['sudo', 'chmod', '644', str(known_hosts_target)], check=True)

    def run(self):
        """Main entrypoint - show banner, sync, and start Claude"""
        workspace = os.getcwd()

        # Copy GCP credentials if mounted
        self.copy_gcp_credentials()

        # Copy SSH credentials if mounted
        self.copy_ssh_credentials()

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
            # Launch Claude Code with CCC plugin
            plugin_dir = str(Path.home() / '.claude' / 'plugins' / 'ccc')
            os.execvp('claude', ['claude', '--plugin-dir', plugin_dir] + sys.argv[1:])
        else:
            # User chose to exit
            sys.exit(0)

def main():
    manager = SessionManager()
    manager.run()

if __name__ == '__main__':
    main()
