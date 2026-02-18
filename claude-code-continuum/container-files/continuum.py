#!/usr/bin/env python3
"""
Continuum Repository Management

Handles initialization, syncing, and management of the continuum git repository.
"""

import os
import json
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
import subprocess
import uuid
from datetime import datetime
import shutil

class ContinuumRepo:
    """Manages the continuum repository structure and operations"""

    DEFAULT_BLOCKLIST = [
        "# CCC Command Blocklist",
        "# Commands that require approval before execution",
        "",
        "rm -rf",
        "dd",
        "mkfs.*",
        "iptables",
        "nftables",
        "sudo",
        "chmod",
        "chown",
        "curl.*|.*bash",
        "wget.*|.*bash",
        "systemctl",
    ]

    DEFAULT_AUTO_LOAD_RULES = {
        'repos': ['*'],
        'load': ['git-workflows.md']
    }

    def __init__(self, path: str):
        self.path = Path(path)
        self.sessions_dir = self.path / 'sessions'
        self.knowledge_dir = self.path / 'knowledge'
        self.config_dir = self.path / 'config'

    def init(self):
        """Initialize continuum repository structure"""
        # Create directories
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Create default blocklist
        blocklist_file = self.config_dir / 'blocklist.txt'
        if not blocklist_file.exists():
            blocklist_file.write_text('\n'.join(self.DEFAULT_BLOCKLIST) + '\n')

        # Create default auto-load rules
        rules_file = self.config_dir / 'auto-load-rules.yaml'
        if not rules_file.exists():
            with open(rules_file, 'w') as f:
                yaml.dump(self.DEFAULT_AUTO_LOAD_RULES, f, default_flow_style=False)

        # Create default knowledge files
        self._create_default_knowledge()

    def _create_default_knowledge(self):
        """Create default knowledge markdown files"""
        default_files = {
            'git-workflows.md': '# Git Workflows\n\nCommon git patterns and workflows.\n',
            'openshift-ci.md': '# OpenShift CI\n\nProw jobs, CI/CD workflows, artifact hunting.\n',
            'kubernetes.md': '# Kubernetes\n\nK8s and OVN networking patterns.\n',
            'jira.md': '# Jira\n\nBug tracking workflows and patterns.\n',
            'golang-patterns.md': '# Go Patterns\n\nGo best practices and common patterns.\n',
        }

        for filename, content in default_files.items():
            file_path = self.knowledge_dir / filename
            if not file_path.exists():
                file_path.write_text(content)

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all available sessions"""
        if not self.sessions_dir.exists():
            return []

        sessions = []
        for session_dir in self.sessions_dir.iterdir():
            if session_dir.is_dir():
                metadata_file = session_dir / 'metadata.json'
                if metadata_file.exists():
                    with open(metadata_file) as f:
                        metadata = json.load(f)
                    sessions.append(metadata)

        return sessions

    def create_snapshot(self, workspace_path: Path, description: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a session snapshot

        Args:
            workspace_path: Path to the workspace directory
            description: Optional description for the session

        Returns:
            Session metadata dictionary
        """
        # Generate session ID: timestamp + UUID
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        session_uuid = str(uuid.uuid4())[:8]
        session_id = f"session-{timestamp}-{session_uuid}"

        # Create session directory
        session_dir = self.sessions_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        # Capture host system details (passed from wrapper script)
        hostname = os.environ.get('CCC_HOST_HOSTNAME', 'unknown')
        kernel_version = os.environ.get('CCC_HOST_KERNEL', 'unknown')

        # Capture git state
        git_info = self._capture_git_state(workspace_path)

        # Build metadata
        metadata = {
            'session_id': session_id,
            'timestamp': datetime.now().isoformat(),
            'description': description or f"Session from {workspace_path.name}",
            'workspace_path': str(workspace_path.absolute()),
            'hostname': hostname,
            'kernel_version': kernel_version,
            'git': git_info
        }

        # Save metadata
        with open(session_dir / 'metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)

        # Capture conversation history
        self._capture_conversation(session_dir)

        # Capture git workspace state
        if git_info['is_repo']:
            self._capture_git_workspace(workspace_path, session_dir, git_info)

        return metadata

    def _capture_git_state(self, workspace_path: Path) -> Dict[str, Any]:
        """Capture current git repository state"""
        git_info = {
            'is_repo': False,
            'branch': None,
            'has_uncommitted': False,
            'has_unpushed': False
        }

        # Check if this is a git repo
        result = subprocess.run(
            ['git', '-C', str(workspace_path), 'rev-parse', '--git-dir'],
            capture_output=True
        )

        if result.returncode != 0:
            return git_info

        git_info['is_repo'] = True

        # Get current branch
        result = subprocess.run(
            ['git', '-C', str(workspace_path), 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            git_info['branch'] = result.stdout.strip()

        # Check for uncommitted changes
        result = subprocess.run(
            ['git', '-C', str(workspace_path), 'status', '--porcelain'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            git_info['has_uncommitted'] = True

        # Check for unpushed commits
        result = subprocess.run(
            ['git', '-C', str(workspace_path), 'log', '@{u}..HEAD', '--oneline'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            git_info['has_unpushed'] = True

        return git_info

    def _capture_conversation(self, session_dir: Path):
        """Capture current Claude Code conversation history"""
        # Find the current Claude session history file
        claude_dir = Path.home() / '.claude'
        history_file = claude_dir / 'history.jsonl'

        if history_file.exists():
            # Copy the entire history file
            # In a real implementation, we'd want to filter to just the current session
            shutil.copy(history_file, session_dir / 'conversation.jsonl')

    def _capture_git_workspace(self, workspace_path: Path, session_dir: Path, git_info: Dict[str, Any]):
        """Capture git workspace state (uncommitted changes, unpushed commits)"""
        # Capture uncommitted changes as a patch
        if git_info['has_uncommitted']:
            result = subprocess.run(
                ['git', '-C', str(workspace_path), 'diff', 'HEAD'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                (session_dir / 'snapshot.patch').write_text(result.stdout)

        # If there are unpushed commits, record the WIP branch name
        if git_info['has_unpushed'] and git_info['branch']:
            wip_branch = f"claude-wip/{git_info['branch']}-{session_dir.name}"
            (session_dir / 'wip-branch').write_text(wip_branch)

            # Push the WIP branch to remote
            try:
                subprocess.run(
                    ['git', '-C', str(workspace_path), 'push', 'origin', f"{git_info['branch']}:{wip_branch}"],
                    check=True,
                    capture_output=True
                )
            except subprocess.CalledProcessError:
                # If push fails, just record the branch name anyway
                pass

    def commit_and_push_snapshot(self, session_id: str, description: str) -> bool:
        """
        Commit the session snapshot to the continuum repo and push to remote

        Args:
            session_id: The session ID to commit
            description: Description for the commit message

        Returns:
            True if successful, False otherwise
        """
        ssh_key_path = Path.home() / '.ssh' / 'continuum_key'
        git_env = {
            **os.environ,
            'GIT_SSH_COMMAND': f'ssh -i {ssh_key_path} -o StrictHostKeyChecking=no'
        }

        try:
            # Add the session directory
            subprocess.run(
                ['git', '-C', str(self.path), 'add', f'sessions/{session_id}'],
                check=True
            )

            # Check if there are changes to commit
            result = subprocess.run(
                ['git', '-C', str(self.path), 'diff', '--cached', '--quiet'],
                capture_output=True
            )

            if result.returncode != 0:  # Non-zero means there are changes
                # Commit the snapshot
                commit_msg = f"snapshot: {description}\n\nSession ID: {session_id}"
                subprocess.run(
                    ['git', '-C', str(self.path), 'commit', '-m', commit_msg],
                    check=True
                )

                # Push to remote
                subprocess.run(
                    ['git', '-C', str(self.path), 'push'],
                    check=True,
                    env=git_env
                )

            return True
        except subprocess.CalledProcessError as e:
            print(f"Error committing snapshot: {e}")
            return False

    def clone_or_pull(self, repo_url: str) -> bool:
        """Clone continuum repo if not exists, otherwise pull latest"""
        # Construct SSH key path properly (will expand ~ to home directory)
        ssh_key_path = Path.home() / '.ssh' / 'continuum_key'
        git_env = {
            **os.environ,
            'GIT_SSH_COMMAND': f'ssh -i {ssh_key_path} -o StrictHostKeyChecking=no'
        }

        try:
            if (self.path / '.git').exists():
                # Already cloned, pull latest
                subprocess.run(
                    ['git', '-C', str(self.path), 'pull'],
                    check=True,
                    capture_output=True,
                    env=git_env
                )
            else:
                # Clone repo
                self.path.parent.mkdir(parents=True, exist_ok=True)
                subprocess.run(
                    ['git', 'clone', repo_url, str(self.path)],
                    check=True,
                    capture_output=True,
                    env=git_env
                )

                # If freshly cloned and empty, initialize structure
                if not self.sessions_dir.exists():
                    self.init()

                    # Configure git user for commits
                    subprocess.run(
                        ['git', '-C', str(self.path), 'config', 'user.name', 'CCC Bot'],
                        check=True
                    )
                    subprocess.run(
                        ['git', '-C', str(self.path), 'config', 'user.email', 'ccc@local'],
                        check=True
                    )

                    subprocess.run(
                        ['git', '-C', str(self.path), 'add', '.'],
                        check=True
                    )
                    # Only commit if there are changes
                    result = subprocess.run(
                        ['git', '-C', str(self.path), 'diff', '--cached', '--quiet'],
                        capture_output=True
                    )
                    if result.returncode != 0:  # Non-zero means there are changes
                        subprocess.run(
                            ['git', '-C', str(self.path), 'commit', '-m', 'Initialize continuum structure'],
                            check=True
                        )
                        subprocess.run(
                            ['git', '-C', str(self.path), 'push'],
                            check=True,
                            env=git_env
                        )

            return True
        except subprocess.CalledProcessError as e:
            print(f"Error syncing continuum repo: {e}")
            if e.stderr:
                print(f"Git error output: {e.stderr.decode()}")
            return False
