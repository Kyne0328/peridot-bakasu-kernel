#!/usr/bin/env python3
"""Rebase one SUSFS proc-maps patch hunk onto Vibranium's optimized header writer.

Vibranium replaced the original void show_vma_header_prefix() with a fast,
int-returning implementation. The upstream SUSFS patch's declaration block
belongs immediately before show_map_vma() in either implementation. This
script changes ONLY that context; it does not discard hooks or ignore rejected
hunks. The resulting patch must still pass a strict --fuzz=0 dry run.
"""
import pathlib
import sys

if len(sys.argv) != 3:
    raise SystemExit("usage: port_susfs_v18.py <upstream.patch> <rebased.patch>")

source, target = map(pathlib.Path, sys.argv[1:])
text = source.read_text()
old = (
    "@@ -274,6 +277,14 @@ static void show_vma_header_prefix(struct seq_file *m,\n"
    " \tseq_putc(m, ' ');\n"
    " }\n"
    " \n"
)
new = (
    "@@ -416,6 +416,14 @@ static int show_vma_header_prefix(struct seq_file *m,\n"
    " \treturn 0;\n"
    " }\n"
    " \n"
)
if text.count(old) != 1:
    raise SystemExit("Upstream SUSFS task_mmu.c hunk changed; require manual inspection")
target.write_text(text.replace(old, new, 1))
print(f"Vibranium proc-maps context rebased: {target}")
