"""Validate stock Qualcomm ELF module parsing, including NOBITS BSS."""
import sys
import struct
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kernel_abi import imports


def module_with_bss(bss_type: int) -> bytes:
    names = b"\0__versions\0.shstrtab\0.bss\0"
    offset = 64
    shstr_offset = 64 + 4 * 64
    versions_offset = shstr_offset + len(names)
    buf = bytearray(versions_offset + 64)
    buf[:6] = b"\x7fELF\x02\x01"
    struct.pack_into("<Q", buf, 40, offset)
    struct.pack_into("<HHH", buf, 58, 64, 4, 2)

    def section(index: int, name: str, kind: int, file_offset: int, size: int) -> None:
        struct.pack_into("<IIQQQQIIQQ", buf, offset + index * 64,
                         names.index(name.encode()), kind, 0, 0, file_offset, size,
                         0, 0, 0, 0)
    section(1, "__versions", 1, versions_offset, 64)
    section(2, ".shstrtab", 3, shstr_offset, len(names))
    section(3, ".bss", bss_type, 1000, 4096)
    buf[shstr_offset:shstr_offset + len(names)] = names
    struct.pack_into("<Q", buf, versions_offset, 0x12345678)
    buf[versions_offset + 8:versions_offset + 8 + len(b"module_layout\0")] = b"module_layout\0"
    return bytes(buf)


class StockElfModuleTests(unittest.TestCase):
    def test_legitimate_nobits_bss_not_on_disk(self):
        self.assertEqual(imports(module_with_bss(8)),
                         [("module_layout", 0x12345678)])

    def test_oversized_file_backed_section_rejected(self):
        with self.assertRaisesRegex(ValueError, "Module section out of bounds"):
            imports(module_with_bss(1))


if __name__ == "__main__":
    unittest.main()
