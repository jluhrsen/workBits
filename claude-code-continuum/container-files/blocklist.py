#!/usr/bin/env python3
"""
Command Blocklist Management

Checks commands against blocklist patterns and manages approvals.
"""

import re
from pathlib import Path
from typing import List, Optional

class CommandBlocklist:
    """Manages command blocklist for security approval prompts"""

    def __init__(self, blocklist_file: str):
        self.blocklist_file = Path(blocklist_file)
        self.patterns = self._load_patterns()

    def _load_patterns(self) -> List[str]:
        """Load blocklist patterns from file"""
        if not self.blocklist_file.exists():
            return []

        patterns = []
        with open(self.blocklist_file) as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if line and not line.startswith('#'):
                    patterns.append(line)

        return patterns

    def is_blocked(self, command: str) -> Optional[str]:
        """
        Check if command matches any blocklist pattern

        Returns:
            The matching pattern if blocked, None if allowed
        """
        for pattern in self.patterns:
            # Support both exact matches and regex patterns
            try:
                if re.search(pattern, command):
                    return pattern
            except re.error:
                # If not valid regex, try exact substring match
                if pattern in command:
                    return pattern

        return None

    def remove_pattern(self, pattern: str):
        """Remove pattern from blocklist (for 'always allow')"""
        if pattern in self.patterns:
            self.patterns.remove(pattern)
            self._save_patterns()

    def _save_patterns(self):
        """Save current patterns back to file"""
        with open(self.blocklist_file, 'w') as f:
            f.write("# CCC Command Blocklist\n")
            f.write("# Commands that require approval before execution\n\n")
            for pattern in self.patterns:
                f.write(f"{pattern}\n")

    def prompt_approval(self, command: str, pattern: str) -> tuple[bool, bool]:
        """
        Prompt user for approval of blocked command

        Returns:
            (approved, remember) - whether to allow, and whether to remember choice
        """
        print(f"\n⚠️  BLOCKED COMMAND: {pattern}")
        print(f"Command: {command}")
        print("This command requires approval.")

        while True:
            response = input("Allow? [y/n/always]: ").lower().strip()

            if response == 'y':
                return (True, False)
            elif response == 'n':
                return (False, False)
            elif response == 'always':
                return (True, True)
            else:
                print("Please enter 'y', 'n', or 'always'")
