# Global Instructions

## Commands for copy-paste

When providing shell commands for the user to run, always give them as single-line strings with no newlines, tabs, or indentation. The user copy-pastes them into remote terminals (often via SSH) where multi-line commands break. Use `&&` to chain sequential commands. No heredocs, no multi-line JSON, no indented blocks. Keep each command under 120 characters to avoid terminal line-wrap issues. If a logical operation needs more than that, split it into multiple separate commands rather than chaining into one long line.
