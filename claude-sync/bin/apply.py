#!/usr/bin/env python3
"""Apply the claude-sync payload from this repo onto the local machine.

Copies every file listed in manifest.json "files" into place, backing up any
existing copy, and fills the JIRA_API_TOKEN placeholder from the local
(gitignored) token file. Never writes a secret back into the repo.
"""
import argparse, json, shutil, sys, time
from pathlib import Path

HOME = Path.home()
SYNC = Path(__file__).resolve().parent.parent
MANIFEST = json.loads((SYNC / "manifest.json").read_text())
TOKEN_FILE = HOME / "repos/workBits/jira_token"
PLACEHOLDER = "__FROM_FILE:$HOME/repos/workBits/jira_token__"
STAMP = time.strftime("%Y%m%d-%H%M%S")


def expand(target: str) -> Path:
    return Path(target.replace("$HOME", str(HOME)))


def backup(path: Path, backup_dir: Path) -> None:
    if not path.exists():
        return
    dest = backup_dir / path.relative_to(HOME)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if path.is_dir():
        shutil.copytree(path, dest, dirs_exist_ok=True)
    else:
        shutil.copy2(path, dest)


def fill_token(path: Path) -> bool:
    """Replace the token placeholder in a settings file with the real token."""
    text = path.read_text()
    if PLACEHOLDER not in text:
        return False
    if not TOKEN_FILE.exists():
        print(f"  ! {TOKEN_FILE} missing - left placeholder in {path.name}")
        return False
    path.write_text(text.replace(PLACEHOLDER, TOKEN_FILE.read_text().strip()))
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    backup_dir = HOME / f".claude/backups/claude-sync-{STAMP}"
    print(f"Applying payload from {SYNC}")
    if not args.dry_run:
        backup_dir.mkdir(parents=True, exist_ok=True)
        print(f"Backups: {backup_dir}")

    for rel, target in MANIFEST["files"].items():
        src, dst = SYNC / rel, expand(target)
        if not src.exists():
            print(f"  - skip {rel} (not in payload)")
            continue
        print(f"  {rel} -> {dst}")
        if args.dry_run:
            continue
        backup(dst, backup_dir)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            # Mirror payload skills without deleting machine-managed ones.
            for sub in src.iterdir():
                out = dst / sub.name
                if out.exists():
                    shutil.rmtree(out) if out.is_dir() else out.unlink()
                shutil.copytree(sub, out) if sub.is_dir() else shutil.copy2(sub, out)
        else:
            shutil.copy2(src, dst)
            if dst.name.startswith("settings.") and fill_token(dst):
                dst.chmod(0o600)
                print(f"    token filled from {TOKEN_FILE}")
    print("Done." if not args.dry_run else "Dry run complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
