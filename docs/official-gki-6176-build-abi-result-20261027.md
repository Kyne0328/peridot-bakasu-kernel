# Official GKI 6.1.176 / BakaSU UAPI6 / WildKernels — POCO F6 RI8 (2026-10-27)

**Status: real kernel compiled, exact retained stock-module import CRC scan passed, three signed recovery ZIPs verified. On-device boot is NOT verified.**

This supersedes the previous Theettam experiment, which failed on 17,902 stock module import CRC occurrences.

## Reproducible source integration

- Official Android GKI release: android14-6.1-2026-09_r1, commit 79480508eb1eed09620f1cd5484dbfa4a677d0a9, Linux 6.1.176.
- Original POCO F6 stock-compatible kernel source: 0c3d559bcd85c64dae9c9c9687abbe5347fff3ad, Linux 6.1.138.
- Root: Baka-SU/BakaSU commit d5e9e025b8b49155f8014684d64c91742b465f65, UAPI 6.
- 66-file kernel feature overlay three-way applied to official 6.1.176. Only fs/f2fs/f2fs.h and fs/proc/base.c conflicted, both reconciled. Zero unresolved merges.
- Reproducible tracked source patch: 08-tools/resukisu-addon/patches/official-gki-6176-stock-uapi6-20261027.patch, 134,171 bytes, SHA-256 c0a90b54b323da297a8499d261b3632821369a8a516da15c1bedd341fe807c90. Supplemental feature trees and BakaSU driver source are pinned/staged separately.
- Linux kernelrelease: 6.1.176-android14-11-g0c3d559bcd85-ab14529422.
- Stock config retains KSU, SUSFS, MODVERSIONS, MODULE_SIG_PROTECT, CFI_CLANG, NOMOUNT, BBG, NTSYNC, TCP_CONG_BBR3, BTF and all other enabled original options except Google's intentionally removed 6.1 memfd-ashmem shim.

## Actual build artifacts

- Full ARM64 kernel compile: make -j10, exit 0.
- Image SHA-256: 6b753ec430452098acc66223b5a33c51880d466f5b8027411536e5745ab93b6b.
- Module.symvers SHA-256: 715812612da1ad429d6ea17f157ecc27c42d00c849d7abceb279465e595a9439.
- Stock module import scan SHA-256: 0f1eb84df5cc845b563714da5797d0d32893fcc76574dc50b7d186977da2962e.
- Combined offline qualification SHA-256: 593204e858c3d387e26451452de08afcc78cdfd253490fbea9b68116c65c331e.

## Actual POCO F6 stock module ABI: PASS

Exact imported CRC requirements were scanned from 712 pinned .ko files (system_dlkm 60, vendor_dlkm 314, vendor_boot 338) and compared with this build's exact Module.symvers:

- 39,387 module import occurrences total.
- 34,725 matching kernel-export CRC import occurrences.
- 4,662 module-to-module or other non-kernel-export import occurrences, covered by the prior verified stock module baseline.
- **Zero mismatching kernel import CRCs, zero missing required kernel exports and zero affected module files.**
- module_layout CRC identical to the previous validated kernel (0xea759d7f).
- Across all exported symbols, 68 CRCs changed and 24 old exports are missing, but none was imported by the 712 scanned stock modules. Do not claim all generic exports are identical.
- Linux's versioned module loader skips the release-token portion of module vermagic when __versions CRCs are present, as verified in kernel/module/version.c.

This is **offline compatibility evidence**, not proof of successful boot or all Qualcomm functionality.

## Recovery ZIPs (signed and integrity verified)

Files are in the owner's retained RI8 folder:
D:\hyperos4-peridot-kyneos-ri8-20261014\outputs\kernel-recovery

| Purpose | Filename | SHA-256 |
|---|---|---|
| **Official 6.1.176 rooted update** | BakaSU-UAPI6-WildKernels-RI8-Linux-6.1.176-Update-20261027.zip | f3bffbf745deee32d4e2de8b900fecbe51fa196f4a6b862cd96b9d0f23ccfeb1 |
| Rollback to rooted UAPI6 6.1.138 | BakaSU-UAPI6-WildKernels-RI8-Linux-6.1.176-Rollback-6.1.138-20261027.zip | 76e38e967feaa955d98eaca8bb002be4bf3722ea74c00255f4074012847b8871 |
| Rollback to stock 6.1.138 | BakaSU-UAPI6-WildKernels-RI8-Linux-6.1.176-Rollback-Stock-20261027.zip | 70774c3cfee7e7f0eb829a1975442ec3eb2b164eecc98995245f9b77c8dee67a |

All three are active-slot boot-only AnyKernel3 ZIPs. They preserve ramdisk and AVB flags, validate device codename peridot and enforce exact accepted input Image hashes. ZIP CRC, embedded image hashes, signed ZIP signatures and manifests were independently verified with the retained development certificate. Recovery trust of that certificate has not been demonstrated.

## Deployment limitation

No ADB device was connected during this task. The new kernel has not been flashed or device-boot tested; camera, GPU/display, Wi-Fi, IMS, thermal, suspend, root manager, and SUSFS runtime functionality remain to be checked.

For an initial test flash: first verify exact HyperOS 4 RI8 target and current active slot; back up the current active boot partition and keep recovery and rollback ZIP available. Do not force a failed kernel-hash guard. Do not format data, flash vendor_boot/super, or disable AVB to compensate for an incompatible boot.

This should be published only as a clearly labeled **experimental pre-release** until on-device verification completes. The original working 6.1.138 kernel and ROM images remain intact.
