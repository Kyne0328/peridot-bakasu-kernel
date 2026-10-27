"""Focused tests: import CRCs are a device contract, not a maintainer's claim."""
from __future__ import annotations
import importlib.util
import sys
import unittest
import tempfile
from pathlib import Path

PATH = Path(__file__).with_name("verify_rooted_6176.py")
SPEC = importlib.util.spec_from_file_location("verify_rooted_6176", PATH)
module = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(module)


class StockKmiTests(unittest.TestCase):
    def test_root_uapi5_required(self):
        with tempfile.TemporaryDirectory() as folder:
            header = Path(folder) / "supercall.h"
            header.write_text("static const __u32 KERNEL_SU_UAPI_VERSION = 5;\n")
            self.assertEqual(module.check_uapi5(header)["root_uapi_version"], 5)
            header.write_text("static const __u32 KERNEL_SU_UAPI_VERSION = 2;\n")
            with self.assertRaisesRegex(ValueError, "Expected root UAPI 5"):
                module.check_uapi5(header)

    def test_relaxed_signature_policy_keeps_crc_and_features(self):
        with tempfile.TemporaryDirectory() as folder:
            image = Path(folder) / "Image"
            config = Path(folder) / ".config"
            image.write_bytes(b"\0Linux version 6.1.176-android14-11-test (gcc) #1\0")
            config.write_text("\n".join(
                f"CONFIG_{name}=y" for name in (
                    "KSU", "KSU_SUSFS", "MODVERSIONS", "CFI_CLANG",
                    "MODULE_SIG", "NOMOUNT", "BBG", "NTSYNC", "TCP_CONG_BBR3"
                )
            ))
            result = module.validate_build(image, config, "6.1.176-android14-11-test")
            self.assertEqual(result["module_modversions"], "enforced")
            config.write_text(config.read_text() + "\nCONFIG_MODULE_SIG_PROTECT=y\n")
            with self.assertRaisesRegex(ValueError, "MODULE_SIG_PROTECT=n"):
                module.validate_build(image, config, "6.1.176-android14-11-test")

    def test_all_matching_stock_kernel_imports_pass(self):
        rows = [("vendor_dlkm", "display.ko", [("driver_probe", 0x1234)])]
        r = module.compare_records(rows, {"driver_probe": 0x1234},
                                   {"driver_probe": 0x1234}, set())
        self.assertEqual(r["status"], "pass")

    def test_mismatched_candidate_crc_fails(self):
        rows = [("vendor_boot", "adsp_sleepmon.ko", [("rpmsg_send", 0xABCD)])]
        r = module.compare_records(rows, {"rpmsg_send": 0xABCD},
                                   {"rpmsg_send": 0xAAAA}, set())
        self.assertEqual(r["status"], "fail")
        self.assertEqual(r["module_counts"]["vendor_boot"]["kernel_crc_mismatches"], 1)

    def test_removed_stock_export_fails(self):
        rows = [("system_dlkm", "6lowpan.ko", [("module_layout", 0x1111)])]
        r = module.compare_records(rows, {"module_layout": 0x1111}, {}, set())
        self.assertEqual(r["status"], "fail")
        self.assertEqual(r["module_counts"]["system_dlkm"]["kernel_exports_missing"], 1)

    def test_module_to_module_import_is_not_kernel_crc_mismatch(self):
        rows = [("vendor_dlkm", "foo.ko", [("vendor_shared", 0x2222)])]
        r = module.compare_records(rows, {"kernel_export": 0x3333},
                                   {"kernel_export": 0x3333}, {"vendor_shared"})
        self.assertEqual(r["status"], "pass")

    def test_unresolved_import_fails(self):
        rows = [("vendor_dlkm", "foo.ko", [("unknown", 0x1234)])]
        r = module.compare_records(rows, {"known": 0x1234},
                                   {"known": 0x1234}, set())
        self.assertEqual(r["status"], "fail")
        self.assertEqual(r["module_counts"]["vendor_dlkm"]["unresolved_imports"], 1)

    def test_stock_baseline_mismatch_fails_closed(self):
        rows = [("vendor_dlkm", "foo.ko", [("known", 0x1234)])]
        r = module.compare_records(rows, {"known": 0x5678},
                                   {"known": 0x1234}, set())
        self.assertEqual(r["status"], "fail")
        self.assertEqual(r["module_counts"]["vendor_dlkm"]["stock_baseline_mismatches"], 1)


if __name__ == "__main__":
    unittest.main()
