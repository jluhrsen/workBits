#!/usr/bin/env python3
"""
Continuum Repository Management

Handles initialization, syncing, and management of the continuum git repository.
"""

import os
import yaml
from pathlib import Path
from typing import List, Dict, Any
import subprocess

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
                    import json
                    with open(metadata_file) as f:
                        metadata = json.load(f)
                    sessions.append(metadata)

        return sessions

    def clone_or_pull(self, repo_url: str) -> bool:
        """Clone continuum repo if not exists, otherwise pull latest"""
        try:
            if (self.path / '.git').exists():
                # Already cloned, pull latest
                subprocess.run(
                    ['git', '-C', str(self.path), 'pull'],
                    check=True,
                    capture_output=True
                )
            else:
                # Clone repo
                self.path.parent.mkdir(parents=True, exist_ok=True)
                subprocess.run(
                    ['git', 'clone', repo_url, str(self.path)],
                    check=True,
                    capture_output=True,
                    env={**os.environ, 'GIT_SSH_COMMAND': 'ssh -i ~/.ssh/continuum_key -o StrictHostKeyChecking=no'}
                )

                # If freshly cloned and empty, initialize structure
                if not self.sessions_dir.exists():
                    self.init()
                    subprocess.run(
                        ['git', '-C', str(self.path), 'add', '.'],
                        check=True
                    )
                    subprocess.run(
                        ['git', '-C', str(self.path), 'commit', '-m', 'Initialize continuum structure'],
                        check=True
                    )
                    subprocess.run(
                        ['git', '-C', str(self.path), 'push'],
                        check=True,
                        env={**os.environ, 'GIT_SSH_COMMAND': 'ssh -i ~/.ssh/continuum_key -o StrictHostKeyChecking=no'}
                    )

            return True
        except subprocess.CalledProcessError as e:
            print(f"Error syncing continuum repo: {e}")
            return False
