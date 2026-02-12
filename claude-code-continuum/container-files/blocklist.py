#!/usr/bin/env python3
"""
Command Blocklist Management

Checks commands against blocklist patterns and manages approvals.
"""

# Try to import regex with timeout support, fall back to re
try:
    import regex
    HAS_REGEX_MODULE = True
except ImportError:
    import re
    HAS_REGEX_MODULE = False

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
        try:
            with open(self.blocklist_file) as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if line and not line.startswith('#'):
                        patterns.append(line)
        except (IOError, PermissionError) as e:
            print(f"Warning: Could not read blocklist file: {e}")
            return []

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
                if HAS_REGEX_MODULE:
                    # Use regex module with timeout to prevent ReDoS
                    if regex.search(pattern, command, timeout=1):
                        return pattern
                else:
                    # Fallback to standard re module (no timeout protection)
                    if re.search(pattern, command):
                        return pattern
            except (re.error, regex.error if HAS_REGEX_MODULE else Exception):
                # If not valid regex, try exact substring match
                if pattern in command:
                    return pattern
            except TimeoutError:
                # Regex timeout - treat as non-match for safety
                print(f"Warning: Regex pattern '{pattern}' timed out, skipping")
                continue

        return None

    def remove_pattern(self, pattern: str):
        """Remove pattern from blocklist (for 'always allow')"""
        if pattern in self.patterns:
            self.patterns.remove(pattern)
            self._save_patterns()

    def _save_patterns(self):
        """Save current patterns back to file"""
        try:
            with open(self.blocklist_file, 'w') as f:
                f.write("# CCC Command Blocklist\n")
                f.write("# Commands that require approval before execution\n\n")
                for pattern in self.patterns:
                    f.write(f"{pattern}\n")
        except (IOError, PermissionError) as e:
            print(f"Warning: Could not write blocklist file: {e}")

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
            try:
                response = input("Allow? [y/n/always]: ").lower().strip()
            except (EOFError, KeyboardInterrupt):
                print("\nInput cancelled - command denied")
                return (False, False)

            if response == 'y':
                return (True, False)
            elif response == 'n':
                return (False, False)
            elif response == 'always':
                return (True, True)
            else:
                print("Please enter 'y', 'n', or 'always'")
