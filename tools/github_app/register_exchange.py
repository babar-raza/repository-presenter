"""Exchange a GitHub App manifest-flow code for real app credentials and store them.

Completes OWNER-04's registration step (project/state.yaml). The one manual action is
tools/github_app/register.html's button click; this script does everything after the
resulting redirect. It never writes a credential to disk or prints one in full.

Usage:
    python tools/github_app/register_exchange.py --redirect-url "https://github.com/babar-raza/repository-presenter?code=...&state=..."
    python tools/github_app/register_exchange.py --code "the-code-alone"

Requires: gh CLI authenticated as an account with permission to create the app and to set
secrets on babar-raza/repository-presenter (repo:write, admin on the repo for secrets).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any
from urllib.parse import parse_qs, urlparse

REPO = "babar-raza/repository-presenter"

# credential field -> GitHub Actions secret name (per OWNER-04's resume_predicate)
SECRET_MAP = {
    "id": "GH_APP_ID",
    "pem": "GH_APP_PRIVATE_KEY",
    "client_id": "GH_APP_CLIENT_ID",
    "client_secret": "GH_APP_CLIENT_SECRET",
    "webhook_secret": "GH_APP_WEBHOOK_SECRET",
}


def extract_code(redirect_url: str | None, code: str | None) -> str:
    if code:
        return code.strip()
    if not redirect_url:
        raise SystemExit("Provide --code or --redirect-url")
    parsed = urlparse(redirect_url)
    qs = parse_qs(parsed.query)
    values = qs.get("code")
    if not values:
        raise SystemExit(f"No 'code' query parameter found in: {redirect_url}")
    return values[0]


def exchange(code: str) -> dict[str, Any]:
    result = subprocess.run(
        [
            "gh",
            "api",
            "--method",
            "POST",
            f"/app-manifests/{code}/conversions",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        # The code is single-use and expires in ~1 hour; a failure here almost always
        # means it was already consumed or is stale, not a script defect.
        raise SystemExit(
            f"Exchange failed (code may be expired/consumed):\n{result.stderr}"
        )
    return dict(json.loads(result.stdout))


def store_secret(name: str, value: str) -> None:
    result = subprocess.run(
        ["gh", "secret", "set", name, "--repo", REPO, "--body", value],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit(f"Failed to store {name}: {result.stderr}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--redirect-url", help="Full URL GitHub redirected to after app creation"
    )
    parser.add_argument(
        "--code", help="The manifest-flow code alone, if you already extracted it"
    )
    args = parser.parse_args()

    code = extract_code(args.redirect_url, args.code)
    creds = exchange(code)

    stored, missing = [], []
    for field, secret_name in SECRET_MAP.items():
        value = creds.get(field)
        if value is None:
            missing.append(field)
            continue
        store_secret(secret_name, str(value))
        stored.append(secret_name)

    slug = creds.get("slug", "<unknown>")
    app_id = creds.get("id", "<unknown>")

    print(f"App registered: slug={slug} id={app_id}")
    print(f"Secrets stored on {REPO}: {', '.join(stored)}")
    if missing:
        print(
            f"Fields not present in the response (not stored): {', '.join(missing)}",
            file=sys.stderr,
        )
    print(
        "\nNext manual step: open "
        f"https://github.com/settings/apps/{slug}/installations and install the app on "
        "every aspose-*-foss org you administer — this second click is required by GitHub "
        "and has no API path around it for a first installation."
    )
    print(
        "\nVerification (OWNER-04's resume_predicate): a hosted workflow run must mint a "
        "read-only installation token for the canary repository once installed."
    )


if __name__ == "__main__":
    main()
