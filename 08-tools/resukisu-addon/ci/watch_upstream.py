#!/usr/bin/env python3
"""Detect upstream BakaSU main revisions and previously successful peridot CI artifacts."""
from __future__ import annotations
import json
import os
import re
from pathlib import Path
from urllib.request import Request, urlopen

UPSTREAM = "Baka-SU/BakaSU"
PREFIX = "bakasu-peridot-"
NAME = re.compile(r"^bakasu-peridot-([0-9a-f]{40})-([0-9a-f]{64})$")
HEX_SHA = re.compile(r"^[0-9a-f]{40}$")


def choose(commit: str, artifacts: list[dict], *, force: bool = False) -> dict:
    if not HEX_SHA.fullmatch(commit):
        raise ValueError("BakaSU upstream SHA must be 40 lowercase hexadecimal digits")
    previous = []
    for entry in artifacts:
        match = NAME.fullmatch(entry.get("name", ""))
        if not match or entry.get("expired") or entry.get("size_in_bytes", 0) <= 0:
            continue
        previous.append((entry.get("created_at", ""), match.group(1), match.group(2)))
    previous.sort(reverse=True)
    already_built = any(rev == commit for _, rev, _ in previous)
    last_image = next((digest for _, rev, digest in previous if rev != commit), "")
    return {
        "upstream_sha": commit,
        "changed": force or not already_built,
        "already_built": already_built,
        "force": force,
        "previous_image_sha": last_image,
        "repository": UPSTREAM,
    }


def api_json(url: str, token: str) -> dict:
    request = Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "peridot-bakasu-autobuilder",
        "X-GitHub-Api-Version": "2022-11-28",
        **({"Authorization": "Bearer " + token} if token else {}),
    })
    with urlopen(request, timeout=25) as response:
        return json.load(response)


def inspect_remote(repo: str, token: str, force: bool) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise ValueError("Invalid GitHub repository name")
    sha = api_json(f"https://api.github.com/repos/{UPSTREAM}/git/ref/heads/main", "")["object"]["sha"]
    artifacts = []
    for page in range(1, 6):
        batch = api_json(f"https://api.github.com/repos/{repo}/actions/artifacts?per_page=100&page={page}", token).get("artifacts", [])
        artifacts.extend(batch)
        if len(batch) < 100:
            break
    return choose(sha, artifacts, force=force)


def main() -> None:
    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ.get("GITHUB_TOKEN", "")
    force = os.environ.get("BAKASU_FORCE_BUILD", "false").lower() == "true"
    result = inspect_remote(repo, token, force)
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with Path(output).open("a", encoding="utf-8") as handle:
            for key in ("upstream_sha", "previous_image_sha", "changed", "already_built"):
                value = result[key]
                handle.write(f"{key}={str(value).lower() if isinstance(value, bool) else value}\n")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as handle:
            handle.write(
                "### POCO F6 BakaSU upstream check\n\n"
                f"Upstream: https://github.com/{UPSTREAM}\n\n"
                f"Commit: {result['upstream_sha']}\n\n"
                f"Build required: **{result['changed']}**\n\n"
                "GitHub Actions polls periodically, rather than receiving upstream webhooks.\n\n"
            )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
