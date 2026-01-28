# server.py
import os
import json
import requests
import sys
import builtins
from typing import Optional, Dict, Any, Tuple

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from agentdna import AgentDNA

# ─────────────────────────────
# Force print → stderr (MCP stdio)
# ─────────────────────────────

_original_print = builtins.print

def _stderr_print(*args, **kwargs):
    _original_print(
        *args,
        file=sys.stderr,
        **{k: v for k, v in kwargs.items() if k != "file"},
    )

builtins.print = _stderr_print

# ─────────────────────────────
# Env + GitHub + AgentDNA setup
# ─────────────────────────────

load_dotenv()

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
AGENTDNA_API_KEY = os.environ.get("AGENTDNA_API_KEY")

if not GITHUB_TOKEN:
    raise RuntimeError("Set GITHUB_TOKEN environment variable")

if not AGENTDNA_API_KEY:
    raise RuntimeError("Set AGENTDNA_API_KEY environment variable")

# 🔒 FIXED REPO CONFIG
REPO_OWNER = "SynapzeCore"
REPO_NAME = "sample-repo"
BASE_BRANCH = "main"

REPO_URL = f"https://github.com/{REPO_OWNER}/{REPO_NAME}"
API_BASE = "https://api.github.com"

mcp = FastMCP("GitHubMCP")

dna = AgentDNA(alias="github_server_1", role="remote", api_key=AGENTDNA_API_KEY)
print("[SERVER] ✅ GitHub MCP server DID:", dna.trust.did)
print("[SERVER] ✅ Repo URL:", REPO_URL)

# ─────────────────────────────
# AgentDNA helpers
# ─────────────────────────────

async def _verify_host_envelope(
    dna_envelope: Optional[Any],
) -> Tuple[Optional[str], Optional[Dict[str, Any]], Optional[list]]:

    if not dna_envelope:
        return None, None, None

    if isinstance(dna_envelope, dict):
        dna_envelope_str = json.dumps(dna_envelope)
    elif isinstance(dna_envelope, str):
        dna_envelope_str = dna_envelope
    else:
        return None, None, ["Unsupported dna_envelope type"]

    print("Whats the dna_envelope_str: ", dna_envelope_str)
    info = await dna.handle(raw_text=dna_envelope_str, verify_mode="light")

    return (
        info.get("original_message"),
        info.get("host_block"),
        info.get("trust_issues"),
    )


def _build_signed_response(
    original_message: Optional[str],
    payload: dict,
    host_block: Optional[Dict[str, Any]],
    trust_issues: Optional[list],
    inject_fake: bool = False,
) -> str:
    if original_message is None:
        original_message = json.dumps(payload)

    if inject_fake:
        original_message += " [SERVER_TAMPERED]"

    built = dna.build(
        original_message=original_message,
        response=json.dumps(payload),
        host_block=host_block,
        extra={"host_trust_issues": trust_issues},
    )

    return built.get("combined_json", json.dumps(built))

# ─────────────────────────────
# MCP TOOLS
# ─────────────────────────────

@mcp.tool()
async def create_issue(
    title: str,
    description: str,
    dna_envelope: dict | str | None = None,
    inject_fake: bool = False,
) -> str:
    print("[SERVER] create_issue called")

    original_message, host_block, trust_issues = await _verify_host_envelope(dna_envelope)

    url = f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/issues"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    resp = requests.post(
        url,
        headers=headers,
        json={"title": title, "body": description},
    )

    if resp.status_code == 201:
        data = resp.json()
        payload = {
            "ok": True,
            "issue_url": data.get("html_url"),
        }
    else:
        payload = {
            "ok": False,
            "status_code": resp.status_code,
            "error": resp.text,
        }

    return _build_signed_response(
        original_message, payload, host_block, trust_issues, inject_fake
    )


@mcp.tool()
async def create_pull_request(
    title: str,
    description: str,
    head: str,
    dna_envelope: dict | str | None = None,
    inject_fake: bool = False,
) -> str:
    print("[SERVER] create_pull_request called")

    original_message, host_block, trust_issues = await _verify_host_envelope(dna_envelope)

    url = f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/pulls"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    resp = requests.post(
        url,
        headers=headers,
        json={
            "title": title,
            "body": description,
            "head": head,
            "base": BASE_BRANCH,
        },
    )

    if resp.status_code == 201:
        data = resp.json()
        payload = {
            "ok": True,
            "pr_url": data.get("html_url"),
        }
    else:
        payload = {
            "ok": False,
            "status_code": resp.status_code,
            "error": resp.text,
        }

    return _build_signed_response(
        original_message, payload, host_block, trust_issues, inject_fake
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
