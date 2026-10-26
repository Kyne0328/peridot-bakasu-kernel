#!/usr/bin/env python3
"""Fail-closed module ABI gate for experimental rooted 6.1.176 peridot kernels.

Reads generated Module.symvers and ALL pinned .ko __versions imports, rather
than relying on another kernel maintainer's baseline. Never loads modules.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from kernel_abi import imports


def read_symvers(path: Path) -> dict[str, int]:
    result: dict[str, int] = {}
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        cells = line.split()
        if len(cells) < 2:
            raise ValueError(f"{path}:{index}: malformed symbol entry")
        symbol, crc = cells[1], int(cells[0], 16)
        if symbol in result:
            raise ValueError(f"duplicate symbol: {symbol}")
        result[symbol] = crc
    if not result:
        raise ValueError(f"empty Module.symvers: {path}")
    return result


def compare_records(
    records: list[tuple[str, str, list[tuple[str, int]]]],
    stock: dict[str, int],
    candidate: dict[str, int],
    module_exports: set[str],
) -> dict:
    """Separate kernel export failures from module-to-module imports."""
    summary: dict[str, Counter] = {}
    failures: list[dict] = []
    for origin, name, symbols in records:
        counts = summary.setdefault(origin, Counter())
        counts["modules"] += 1
        counts["imports"] += len(symbols)
        for symbol, crc in symbols:
            if symbol in stock:
                counts["stock_kernel_imports"] += 1
                if stock[symbol] != crc:
                    counts["stock_baseline_mismatches"] += 1
                    failures.append({"module": name, "origin": origin, "symbol": symbol,
                                     "problem": "stock_baseline_not_matching_module",
                                     "module_crc": hex(crc), "stock_crc": hex(stock[symbol])})
                if symbol not in candidate:
                    counts["kernel_exports_missing"] += 1
                    failures.append({"module": name, "origin": origin, "symbol": symbol,
                                     "problem": "missing_kernel_export"})
                elif candidate[symbol] != crc:
                    counts["kernel_crc_mismatches"] += 1
                    failures.append({"module": name, "origin": origin, "symbol": symbol,
                                     "problem": "candidate_kernel_crc_mismatch",
                                     "module_crc": hex(crc), "candidate_crc": hex(candidate[symbol])})
            elif symbol in candidate:
                # An export absent in stock cannot be presumed a compatible
                # replacement; compare the module's required CRC anyway.
                if candidate[symbol] != crc:
                    counts["new_kernel_crc_mismatches"] += 1
                    failures.append({"module": name, "origin": origin, "symbol": symbol,
                                     "problem": "new_kernel_export_crc_mismatch",
                                     "module_crc": hex(crc), "candidate_crc": hex(candidate[symbol])})
            elif symbol in module_exports:
                counts["module_to_module_imports"] += 1
            else:
                counts["unresolved_imports"] += 1
                failures.append({"module": name, "origin": origin, "symbol": symbol,
                                 "problem": "unresolved_import"})
    return {
        "status": "pass" if not failures else "fail",
        "module_counts": {k: dict(v) for k, v in sorted(summary.items())},
        "failure_count": len(failures),
        "failures": failures,
    }


def check_uapi5(path: Path) -> dict:
    """Reject mismatched root manager UAPI even when KSU itself compiles."""
    text = path.read_text(encoding="utf-8")
    found = re.search(r"\bKERNEL_SU_UAPI_VERSION\s*=\s*(\d+)\s*;", text)
    if not found:
        raise ValueError("Cannot verify KERNEL_SU_UAPI_VERSION")
    if int(found.group(1)) != 5:
        raise ValueError(f"Expected root UAPI 5, got {found.group(1)}")
    return {"root_uapi_version": 5}


def validate_build(image: Path, config: Path, expected_release: str) -> dict:
    cfg = set(config.read_text(encoding="utf-8").splitlines())
    required = ("KSU", "KSU_SUSFS", "MODVERSIONS", "CFI_CLANG", "MODULE_SIG",
                "NOMOUNT", "BBG", "NTSYNC", "TCP_CONG_BBR3")
    missing = [name for name in required if f"CONFIG_{name}=y" not in cfg]
    if missing:
        raise ValueError("Required rooted fullbundle configs disabled: " + ", ".join(missing))
    if "CONFIG_MODULE_SIG_PROTECT=y" in cfg:
        raise ValueError("This experiment requires owner-approved MODULE_SIG_PROTECT=n")
    if "CONFIG_MODULE_SIG_FORCE=y" in cfg:
        raise ValueError("MODULE_SIG_FORCE unexpectedly enabled")
    raw = image.read_bytes()
    banner = re.search(rb"Linux version (6\.1\.\d+[^\x00\s]*)", raw)
    if not banner or banner.group(1).decode() != expected_release:
        raise ValueError("Built Image kernel release does not match pinned target")
    if not expected_release.startswith("6.1.176"):
        raise ValueError("This gate only supports the approved 6.1.176 experiment")
    return {"kernel_release": expected_release,
            "image_sha256": hashlib.sha256(raw).hexdigest(),
            "config_sha256": hashlib.sha256(config.read_bytes()).hexdigest(),
            "module_signature_policy": "optional; MODULE_SIG_PROTECT=n, MODULE_SIG_FORCE=n",
            "module_modversions": "enforced"}



def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--image", type=Path, required=True)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--symvers", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--release", required=True, help="Exact built kernel.release string")
    p.add_argument("--uapi-header", required=True, type=Path, help="Exact integrated driver uapi/supercall.h")
    args = p.parse_args()

    # Reuse the existing stock-module loader; signature enforcement is optional.
    sys.path.insert(0, str(ROOT / "08-tools" / "resukisu-addon"))
    import verify_uapi5_full_bundle as stock_verify

    report = {"schema": 1, "device": "peridot", "root_flavor": "ReSukiSU+SUSFS",
              "source": "stock-module-ABI-verification", "status": "fail"}
    try:
        for item in (args.image, args.config, args.symvers, args.uapi_header, stock_verify.STOCK_SYMVERS):
            if not item.is_file():
                raise FileNotFoundError(str(item))
        report.update(validate_build(args.image, args.config, args.release))
        report.update(check_uapi5(args.uapi_header))
        stock = read_symvers(stock_verify.STOCK_SYMVERS)
        candidate = read_symvers(args.symvers)
        modules = stock_verify.collect_modules()
        module_exports = set().union(*(stock_verify.exports(data) for _, _, data in modules))
        records = [(origin, name, imports(data)) for origin, name, data in modules]
        report.update(compare_records(records, stock, candidate, module_exports))
        report["stock_exports"] = len(stock)
        report["candidate_exports"] = len(candidate)
        report["symvers_sha256"] = hashlib.sha256(args.symvers.read_bytes()).hexdigest()
        if report["status"] == "pass":
            # A valid stock module CRC map is mandatory; signatures are
            # deliberately not a gate after the owner's explicit policy change.
            report["signature_validation_required"] = False
            report["status"] = "offline-kmi-pass-not-device-tested"
    except Exception as exc:
        report["status"] = "fail"
        report["error"] = str(exc)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "failures"}, indent=2))
    if report["status"] != "offline-kmi-pass-not-device-tested":
        print("BLOCKED: rooted kernel is NOT approved for packaging/flashing", file=sys.stderr)
        return 1
    print("Offline KMI and root gates passed; still NOT device-tested")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
