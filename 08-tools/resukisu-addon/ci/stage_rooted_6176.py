#!/usr/bin/env python3
"""Stage owner UAPI5, SUSFS and fullbundle sources for isolated 6.1.176 build.

Use AFTER resolve_6176_conflicts.py --apply. Requires a local preserved
known-good owner's fullbundle and separately pinned Theettam 6.1.176 source.
No source trees, ROM images, signing keys or proprietary files are published.
This prepares an EXPERIMENT, not a flashable package.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess

PIN = "38d491869bb5d4b4f5337548535f2f1dd3c834a1"
EXTRA = (
    "drivers/misc/ntsync.c",
    "fs/susfs.c", "fs/nomount",
    "include/linux/susfs.h", "include/linux/susfs_def.h",
    "include/uapi/linux/ntsync.h",
    "net/ipv4/tcp_bbr3.c", "net/ipv4/tcp_plb.c",
    "security/baseband-guard", "Baseband-guard", "NoMount",
    "certs/peridot-stock-public.pem",
)
REQUIRED = ("KSU", "KSU_SUSFS", "MODVERSIONS", "CFI_CLANG",
            "NOMOUNT", "BBG", "NTSYNC", "TCP_CONG_BBR3")


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def stage(source: Path, legacy: Path, driver: Path, config_from: Path,
          out: Path, driver_dest: Path) -> dict:
    if git(source, "rev-parse", "HEAD") != PIN:
        raise ValueError("Wrong 6.1.176 source commit")
    if git(source, "ls-files", "-u"):
        raise ValueError("Unresolved merge conflicts; refuse to stage")
    uapi = (driver / "uapi/supercall.h").read_text()
    if not re.search(r"\bKERNEL_SU_UAPI_VERSION\s*=\s*5\s*;", uapi):
        raise ValueError("Owner root driver is not UAPI 5")
    if driver_dest.exists():
        raise ValueError("Driver destination already exists; no overwrite")
    if out.exists():
        raise ValueError("Output/config destination already exists; no overwrite")

    manifest = []
    for relative in EXTRA:
        src, dest = legacy / relative, source / relative
        if not src.exists():
            raise FileNotFoundError(str(src))
        if dest.exists():
            manifest.append({"path": relative, "status": "upstream-present; unchanged"})
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dest, symlinks=True,
                            ignore=shutil.ignore_patterns(".git", ".gitignore", "*.orig"))
        else:
            shutil.copy2(src, dest)
        manifest.append({"path": relative, "status": "copied-from-owner"})
    driver_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(driver, driver_dest, symlinks=True,
                    ignore=shutil.ignore_patterns(".git"))
    link = source / "drivers/kernelsu"
    if link.exists() or link.is_symlink():
        raise ValueError("KernelSU driver symlink already exists")
    if driver_dest.resolve() != (source.parent / "ReSukiSU").resolve():
        raise ValueError("Driver destination must be source/../ReSukiSU for known driver symlink")
    link.symlink_to("../../ReSukiSU/kernel")
    if not (link / "Kbuild").is_file():
        raise ValueError("UAPI5 driver Kbuild missing after staging")

    out.mkdir(parents=True)
    cfg = config_from.read_text()
    for key in REQUIRED:
        if f"CONFIG_{key}=y" not in cfg:
            raise ValueError(f"Missing required fullbundle config: {key}")
    cfg = cfg.replace("CONFIG_MODULE_SIG_PROTECT=y",
                      "# CONFIG_MODULE_SIG_PROTECT is not set")
    cfg = cfg.replace("CONFIG_MODULE_SIG_FORCE=y",
                      "# CONFIG_MODULE_SIG_FORCE is not set")
    (out / ".config").write_text(cfg)
    return {"source_commit": PIN, "root_uapi": 5,
            "signature_policy": "MODULE_SIG_PROTECT=n; MODULE_SIG_FORCE=n",
            "modversions": "enforced",
            "extra": manifest, "status": "staged-not-compiled"}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--legacy-common", required=True, type=Path)
    p.add_argument("--driver", required=True, type=Path)
    p.add_argument("--config-from", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--driver-dest", required=True, type=Path)
    p.add_argument("--report", required=True, type=Path)
    a = p.parse_args()
    result = stage(*(getattr(a, key).resolve() for key in (
        "source", "legacy_common", "driver", "config_from", "out", "driver_dest")))
    a.report.parent.mkdir(parents=True, exist_ok=True)
    a.report.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
