# Rooted Linux 6.1.176 POCO F6 — actual build result (2026-10-26)

**Outcome: COMPILED; STOCK MODULE ABI FAILED; DO NOT FLASH.**

This report documents a **real kernel compilation**, not the previous 6.1.176 third-party KMI comparison. The build is a source-level experiment in the owner's private WSL workspace. It does not change the KyneOS RI8 or One UI 9 ROM image, active boot partition, or existing rooted 6.1.138 kernel.

## Exact source / build identity

| Item | Verified |
|---|---|
| Hardware | POCO F6 peridot |
| Base | Theettam 2.8 Linux 6.1.176, commit `38d491869bb5d4b4f5337548535f2f1dd3c834a1` |
| Root driver | Owner preserved ReSukiSU **UAPI 5**, commit `8770c7e324a22895703c4916b8a16520e0b81c79` |
| SUSFS | 2.3.0 (inline hooks detected at build) |
| Module policy | `CONFIG_MODULE_SIG_PROTECT=n`, `CONFIG_MODULE_SIG_FORCE=n`, `CONFIG_MODULE_SIG=y`, `CONFIG_MODVERSIONS=y` |
| Root/feature build config | `KSU=y`, `KSU_SUSFS=y`, `NOMOUNT=y`, `BBG=y`, `NTSYNC=y`, `TCP_CONG_BBR3=y`, `CFI_CLANG=y`, `DEBUG_INFO_BTF=y` |
| Clang in local experiment | Ubuntu clang 18.1.3 |
| Build result | `make -j8 ...` exit code **0**, produced `Image` and `Module.symvers` |
| Image SHA-256 | `c3b39bd66e3555237706b7f91d4136c465d6b80fdd7affc448854dc782d8ee3c` |
| Module.symvers SHA-256 | `67024c659403ca43f06056ab1c2f4beb1128908538b2e85812704ebbad98a2d4` |

The source diff from the clean Theettam commit is saved at `08-tools/resukisu-addon/patches/rooted-6176-uapi5-fullbundle-20261026.patch`, SHA-256 **`2f89b118d9cad9314f88023f1077a8be45493218e913fe86f274719848207012`**. The patch's reverse-apply check against the exact built source passed. The patch contains modified *tracked* source; supplemental GPL driver/SUSFS/NoMount/BBG source trees are **not** bundled in Git and must be pinned and staged separately. This is not a standalone flashable package.

## Actual ABI gate — FAILED

The exact compiled `Module.symvers` was compared against the preserved POCO F6 stock `.ko` `__versions` requirements. The pinned CI archive contains **712** stock module instances (60 `system_dlkm`, 314 `vendor_dlkm`, 338 `vendor_boot`).

| Stock module origin | Modules | CRC mismatch occurrences |
|---|---:|---:|
| system_dlkm | 60 | 2,024 |
| vendor_dlkm | 314 | 8,527 |
| vendor_boot | 338 | 7,351 |
| **Total** | **712** | **17,902** |

The 17,902 incompatible import *occurrences* involve **2,425 distinct symbols**. All **712** module files disagree on `module_layout`; common additional conflicts include `__platform_driver_register`, `platform_driver_unregister`, `devm_kmalloc` and `_dev_err`. The compiled candidate exports 16,008 symbols versus 8,506 in the retained stock baseline. These are **measured incompatibilities from the actual new build**, not hypothetical boot failure or the maintainer's older published KMI.

The fail-closed validator requires correct root UAPI 5, features, CFI and modversions. Module signature enforcement was explicitly relaxed per the owner's instruction, but **ABI/version CRC checks remain mandatory**. The validator initially mishandled valid ELF SHT_NOBITS `.bss` sections. This was corrected and regression-tested before the above result. **26 Python tests passed.**

The earlier broader read-only investigation counted 772 module instances across different source inventories; the **712** here are the precisely pinned CI stock modules actually scanned for this candidate. Do not conflate the two coverage sets.

## Incremental build failures fixed during this work

1. Git 3-way source patch had 17 conflicting paths; each was resolved with explicit documented choices and compiled.
2. Duplicate identical `tcp_set_tx_in_flight()` definitions from a non-conflicting merge area were reduced to one.
3. The owner's ReSukiSU driver requires its original Git metadata to calculate the version. This pinned `.git` provenance was retained instead of disabling that safety check.
4. The GPL-2.0 ADIOS scheduler source was missing `MODULE_LICENSE("GPL")` required for module post-processing; the declaration was added without changing scheduler logic.
5. ReSukiSU UAPI 5, SUSFS, BBRv3, NTSync, NoMount, Baseband Guard and final kernel linking succeeded.

## Actual local artifacts

`C:\Dev\hyperos4-peridot-research\builder\work\rooted-6176-uapi5-ABI-FAIL-20261026\`

Files: `Image`, `Module.symvers`, `kernel.config`, `stock-module-abi.json`, `build-final.log`, `build-manifest.json`, `DO-NOT-FLASH.txt`. This directory is deliberately **not** named or packaged as a flashable ZIP.

## Remaining release gate

**Do not disable `CONFIG_MODVERSIONS` or bypass CRC checks** to get the kernel to load. A compatible release needs a 6.1.176 kernel using the POCO F6's exact vendor module ABI, or a fully validated matching module/kernel replacement stack. Validate camera/graphics, IMS calls, Wi-Fi, stability, SELinux, boot image/AVB, and rollback independently for RI8 and One UI 9 before any production release.

**No GitHub release, signature, flash, install, or successful device boot is claimed.**
