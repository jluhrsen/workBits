"""Fetch bash scripts from GitHub on startup."""
import os
import shutil
import requests

# Script URLs from PR #177
# NOTE: Once the PR is merged, these URLs will work. For now, we fall back to local paths.
E2E_SCRIPT_URL = "https://raw.githubusercontent.com/openshift-eng/ai-helpers/add-ci-pr-retest-command/plugins/ci/skills/e2e-retest/e2e-retest.sh"
PAYLOAD_SCRIPT_URL = "https://raw.githubusercontent.com/openshift-eng/ai-helpers/add-ci-pr-retest-command/plugins/ci/skills/payload-retest/payload-retest.sh"

# Local fallback paths (when PR not yet merged)
AI_HELPERS_REPO = os.path.expanduser("~/repos/RedHat/openshift/ai-helpers")
E2E_LOCAL_PATH = f"{AI_HELPERS_REPO}/plugins/ci/skills/e2e-retest/e2e-retest.sh"
PAYLOAD_LOCAL_PATH = f"{AI_HELPERS_REPO}/plugins/ci/skills/payload-retest/payload-retest.sh"

SCRIPT_DIR = "/tmp/pr-ci-dashboard"

def fetch_scripts():
    """Download scripts from GitHub to local temp directory."""
    os.makedirs(SCRIPT_DIR, exist_ok=True)

    scripts = {
        'e2e-retest.sh': (E2E_SCRIPT_URL, E2E_LOCAL_PATH),
        'payload-retest.sh': (PAYLOAD_SCRIPT_URL, PAYLOAD_LOCAL_PATH)
    }

    for filename, (url, local_fallback) in scripts.items():
        local_path = os.path.join(SCRIPT_DIR, filename)

        # Try fetching from GitHub first
        try:
            print(f"Fetching {filename} from GitHub...")
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            with open(local_path, 'w') as f:
                f.write(response.text)

            print(f"✅ {filename} fetched from GitHub")

        except (requests.RequestException, IOError) as e:
            # Fall back to local file if GitHub fetch fails
            print(f"⚠️  GitHub fetch failed ({e}), using local file...")
            if os.path.exists(local_fallback):
                shutil.copy2(local_fallback, local_path)
                print(f"✅ {filename} copied from local repo")
            else:
                raise FileNotFoundError(
                    f"Cannot fetch {filename} from GitHub and local file not found at {local_fallback}"
                )

        os.chmod(local_path, 0o755)
        print(f"📍 {filename} ready at {local_path}")

    return SCRIPT_DIR

def get_script_path(script_name):
    """Get full path to a fetched script."""
    return os.path.join(SCRIPT_DIR, script_name)
