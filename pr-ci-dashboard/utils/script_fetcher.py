"""Fetch bash scripts from GitHub on startup."""
import os
import shutil
import requests

E2E_SCRIPT_URL = "https://raw.githubusercontent.com/openshift-eng/ai-helpers/main/plugins/ci/skills/e2e-retest/e2e-retest.sh"
PAYLOAD_SCRIPT_URL = "https://raw.githubusercontent.com/openshift-eng/ai-helpers/main/plugins/ci/skills/payload-retest/payload-retest.sh"

# Local paths for development (fallback if GitHub fetch fails)
AI_HELPERS_PATH = os.path.expanduser("~/repos/RedHat/openshift/ai-helpers")
E2E_LOCAL = f"{AI_HELPERS_PATH}/plugins/ci/skills/e2e-retest/e2e-retest.sh"
PAYLOAD_LOCAL = f"{AI_HELPERS_PATH}/plugins/ci/skills/payload-retest/payload-retest.sh"

SCRIPT_DIR = "/tmp/pr-ci-dashboard"

def fetch_scripts():
    """Download scripts from GitHub to local temp directory, or copy from local repo."""
    os.makedirs(SCRIPT_DIR, exist_ok=True)

    scripts = {
        'e2e-retest.sh': (E2E_SCRIPT_URL, E2E_LOCAL),
        'payload-retest.sh': (PAYLOAD_SCRIPT_URL, PAYLOAD_LOCAL)
    }

    for filename, (url, local_fallback) in scripts.items():
        local_path = os.path.join(SCRIPT_DIR, filename)

        # Try GitHub first
        try:
            print(f"Fetching {filename} from GitHub...")
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            with open(local_path, 'w') as f:
                f.write(response.text)

            os.chmod(local_path, 0o755)
            print(f"✅ {filename} ready at {local_path}")
            continue

        except requests.RequestException as e:
            print(f"⚠️  GitHub fetch failed: {e}")
            print(f"   Trying local fallback: {local_fallback}")

        # Fallback to local copy
        try:
            if os.path.exists(local_fallback):
                shutil.copy2(local_fallback, local_path)
                os.chmod(local_path, 0o755)
                print(f"✅ {filename} ready at {local_path} (from local repo)")
            else:
                raise Exception(f"Local fallback not found: {local_fallback}")

        except (IOError, OSError) as e:
            raise Exception(f"Failed to copy {filename} from local repo: {e}")

    return SCRIPT_DIR

def get_script_path(script_name):
    """Get full path to a fetched script."""
    return os.path.join(SCRIPT_DIR, script_name)
