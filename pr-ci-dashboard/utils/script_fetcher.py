"""Fetch bash scripts from GitHub on startup."""
import os
import requests

E2E_SCRIPT_URL = "https://raw.githubusercontent.com/openshift-eng/ai-helpers/add-ci-pr-retest-command/plugins/ci/skills/e2e-retest/e2e-retest.sh"
PAYLOAD_SCRIPT_URL = "https://raw.githubusercontent.com/openshift-eng/ai-helpers/add-ci-pr-retest-command/plugins/ci/skills/payload-retest/payload-retest.sh"

SCRIPT_DIR = "/tmp/pr-ci-dashboard"

def fetch_scripts():
    """Download scripts from GitHub to local temp directory."""
    os.makedirs(SCRIPT_DIR, exist_ok=True)

    scripts = {
        'e2e-retest.sh': E2E_SCRIPT_URL,
        'payload-retest.sh': PAYLOAD_SCRIPT_URL
    }

    for filename, url in scripts.items():
        local_path = os.path.join(SCRIPT_DIR, filename)

        print(f"Fetching {filename} from GitHub...")
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        with open(local_path, 'w') as f:
            f.write(response.text)

        os.chmod(local_path, 0o755)
        print(f"✅ {filename} ready at {local_path}")

    return SCRIPT_DIR

def get_script_path(script_name):
    """Get full path to a fetched script."""
    return os.path.join(SCRIPT_DIR, script_name)
