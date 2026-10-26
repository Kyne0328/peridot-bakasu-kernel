#!/usr/bin/env python3
"""Reconcile known fullbundle 6.1.138 -> Theettam 6.1.176 three-way conflicts.

Input: an ISOLATED pinned Theettam source Git worktree after applying the
owner's 6.1.138 UAPI5/WildKernels tracked diff with 'git apply --3way'.
No automatic generic conflict resolution; require the EXACT 17 known paths
and hunk counts. Recheck every result by compiling and with the stock ABI gate.

This script does NOT copy the owner-specific supplemental source directories,
BakaSU UAPI5 driver, SUSFS/NoMount sources, certificates, or stock config.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import subprocess

UPSTREAM = "38d491869bb5d4b4f5337548535f2f1dd3c834a1"
# H = keep 6.1.176, O = preserve owner modification, C = combine,
# X = integrate mutually exclusive BBRv3/non-BBR3 callback without duplicates.
DECISIONS = {
    "drivers/Kconfig": "C",
    "drivers/Makefile": "C",
    "drivers/base/power/wakeup.c": "H",
    "fs/f2fs/f2fs.h": "H",
    "fs/proc/base.c": "O",
    "include/linux/tcp.h": "O",
    "include/net/tcp.h": "H O O H H O",
    "include/uapi/linux/inet_diag.h": "O O H",
    "include/uapi/linux/rtnetlink.h": "O",
    "kernel/power/process.c": "H",
    "kernel/time/alarmtimer.c": "H",
    "lib/string.c": "H",
    "net/ipv4/sysctl_net_ipv4.c": "H",
    "net/ipv4/tcp_input.c": "O X H H",
    "net/ipv4/tcp_ipv4.c": "O C",
    "net/ipv4/tcp_output.c": "H H",
    "net/ipv4/tcp_rate.c": "H",
}
CONFLICT = re.compile(r"(?ms)^<<<<<<< ours\n(.*?)^=======\n(.*?)^>>>>>>> theirs\n")


def run(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def resolve(root: Path, apply: bool) -> dict:
    rev = run(root, "rev-parse", "HEAD")
    if rev != UPSTREAM:
        raise ValueError(f"Source pin mismatch: {rev}")
    files = run(root, "diff", "--name-only", "--diff-filter=U").splitlines()
    if set(files) != set(DECISIONS):
        raise ValueError(f"Changed conflict set, missing={set(DECISIONS)-set(files)}, unexpected={set(files)-set(DECISIONS)}")
    rendered: dict[str, str] = {}
    audit: list[dict] = []
    for path in sorted(files):
        original = (root / path).read_text()
        choices = DECISIONS[path].split()
        index = 0

        def substitute(match: re.Match[str]) -> str:
            nonlocal index
            head, owner = match.group(1), match.group(2)
            position = index
            index += 1
            if position >= len(choices):
                raise ValueError(f"Extra conflict in {path}")
            choice = choices[position]
            audit.append({"file": path, "hunk": position, "choice": choice})
            if choice == "H":
                return head
            if choice == "O":
                return owner
            if choice == "C":
                return head + ("\n" if path == "net/ipv4/tcp_ipv4.c" else "") + owner
            if choice == "X" and path == "net/ipv4/tcp_input.c" and position == 1:
                return (
                    '  if (ca_ops && strncmp(ca_ops->name, "bbr3", 4) == 0) {\n'
                    '    bbr3 = *(struct bbr3 **)inet_csk_ca(sk);\n'
                    '    if (bbr3 && bbr3->skb_marked_lost)\n'
                    '      bbr3->skb_marked_lost(sk, skb);\n'
                    '  } else if (ca_ops && ca_ops->skb_marked_lost) {\n'
                    '    ca_ops->skb_marked_lost(sk, skb);\n'
                    '  }\n'
                )
            raise ValueError(f"Unsupported conflict choice {path}:{position}:{choice}")

        result = CONFLICT.sub(substitute, original)
        if index != len(choices) or re.search(r"(?m)^<<<<<<<|^>>>>>>>|^=======\s*$", result):
            raise ValueError(f"Unresolved conflict in {path} ({index}/{len(choices)})")
        rendered[path] = result

    # Both 6.1.138 and 6.1.176 introduce an identical rate helper outside
    # of the conflicting whitespace hunk. Git's merge does not flag identical
    # duplicate function definitions; require exact bodies before removing one.
    rate = root / "net/ipv4/tcp_rate.c"
    rtext = rendered["net/ipv4/tcp_rate.c"]
    declaration = "void tcp_set_tx_in_flight(struct sock *sk, struct sk_buff *skb)\n{"
    positions = []
    cursor = 0
    while (at := rtext.find(declaration, cursor)) >= 0:
        end = rtext.find("\n}\n", at)
        if end < 0:
            raise ValueError("Truncated tcp_set_tx_in_flight body")
        positions.append((at, end + 3))
        cursor = end + 3
    if len(positions) != 2:
        raise ValueError(f"Expected exactly 2 duplicate tcp_set_tx_in_flight definitions, got {len(positions)}")
    a = rtext[slice(*positions[0])]
    b = rtext[slice(*positions[1])]
    if a != b:
        raise ValueError("Rate-helper bodies differ: manual merge required")
    rendered["net/ipv4/tcp_rate.c"] = rtext[:positions[1][0]] + rtext[positions[1][1]:]
    audit.append({"file": "net/ipv4/tcp_rate.c",
                  "hunk": "identical-extra-helper",
                  "choice": "remove identical duplicate", "bytes": len(b)})

    # First validate ALL paths, then mutate; never partially apply on mismatch.
    if apply:
        for path, content in rendered.items():
            (root / path).write_text(content)
            subprocess.run(["git", "-C", str(root), "add", "--", path], check=True)
        if run(root, "ls-files", "-u"):
            raise RuntimeError("Unresolved Git index entries remain")
    return {"source_commit": rev, "status": "merged-uncompiled" if apply else "dry-run",
            "files": len(files), "hunks": audit,
            "warning": "Manual ABI/source review and actual compilation remain mandatory."}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--apply", action="store_true", help="Actually resolve and stage conflicts")
    p.add_argument("--report", type=Path)
    args = p.parse_args()
    result = resolve(args.source.resolve(), args.apply)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
