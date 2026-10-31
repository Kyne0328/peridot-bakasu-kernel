# Kamios v1.1 POCO F6 / Vibranium V18 — compiled kernel and stock module ABI qualification

Date: 2026-10-31. Target: user-owned `peridot`, Kamios v1.1 Android 17, running kernel `6.1.176-Vibranium-V18+`, slot B.

## Build completed

- [Successful full in-tree BakaSU UAPI6 + SUSFS + selected WildKernels build (GitHub Actions #41192072295)](https://github.com/Kyne0328/peridot-bakasu-kernel/actions/runs/41192072295).
- Build source candidate: `khargosxh18/android_kernel_xiaomi_sm8635@4b42813174f309838106763126c8d3c8f14e96b2`; BakaSU `5785bdb8091304322f597f67d50e0b79f9815cb2`; SUSFS `ee155a1ad4219804a7c54cb39dd4fa1b5c2a3fa4`; WildKernels patches `41ae18b35d20e0c6ac04116785a4a1089528ae94`.
- Toolchain: Android Clang r563880c, `CONFIG_LTO_CLANG_FULL=y`.
- `Image`: 42,789,376 bytes; SHA256 `a7553b02b86928f28e95fb396de15de4f8ee29f3e055389aa56d4aedb7cf0fdd`.
- `Module.symvers`: 1,110,245 bytes; SHA256 `11567abf02997de71fb49b2a434087d70823ab089dfd99209e9843f5d326c776`. 17,786 exported-symbol records.
- Kernel config extracted independently from embedded `IKCFG_ST/IKCFG_ED` compressed configuration: `CONFIG_KSU=y`, `CONFIG_KSU_SUSFS=y`, `CONFIG_NTSYNC=y`, `CONFIG_MODVERSIONS=y`, `CONFIG_MODULE_SIG_PROTECT=y`, `CONFIG_LTO_CLANG_FULL=y`.
- Selected integrated WildKernels patches: NTSync compatibility/base (built-in `CONFIG_NTSYNC=y` because the external module used an unexported kernel symbol), Unicode fix, ARM64 prefetch. **Not** the entire WildKernels bundle: BBRv3, F2FS congestion and freeze-timeout patches need additional source-specific adaptation.
- Compiled Image is raw ARM64 `Image`, not a flashable boot.img or installer.

## Stock OTA extraction evidence

Original OTA `D:\Downloads\KamiOS-17.0-20261027-peridot-v1.1.zip`; original OTA SHA256 previously verified: `d089b8b1ed938b14bc82840500d40820e77177e9987335fb4a32f289edebaeba`.

Using existing `08-tools/global-build/linux-assembly/payload_stream.py` source extraction with operation blob hash and final partition hash validation, we recovered:

- `system_dlkm`: 6,811,648 bytes; SHA256 `e02fb59945746a283bd6b02183f7f56bf84f2643318cc05933c8cd48057b7dad`.
- `vendor_dlkm`: 32,964,608 bytes; SHA256 `9bd0fa06b91a13482a2781b9abab056971963c9f7ea326925f0cd08f168443b8`.

Both partitions were EROFS and extracted using installed `extract.erofs.exe`. Their contents include 60 stock system_dlkm `.ko` and 403 stock vendor_dlkm `.ko` modules.

## Exact stock module CRC comparison

Source: the `__versions` sections of all 463 shipped ELF64 AArch64 `.ko` modules. Every module contains matching `vermagic=6.1.176-Vibranium-V18+` metadata. Compared each import's symbol name and 32-bit version CRC to the actual `Module.symvers` from the new kernel.

| Comparison | Observed |
|---|---:|
| Stock modules inspected | **463** |
| Versioned imported symbol references | **26,542** |
| References matching compiled export CRC | **25,608** |
| CRC mismatches on matched names | **0** |
| References not present in new kernel `Module.symvers` | **934** (514 unique symbol names) |
| Missing references supplied by exports in unchanged stock modules | **934 / 934** |
| Remaining unresolved symbol names (across build plus stock modules) | **0** |
| Stock module kernel-release mismatches | **0** |

The 934 external references were independently cross-checked against `__ksymtab_` names in all 463 stock modules. All 514 absent names are provided by another unchanged stock module (examples: `msm_cdc_pinctrl_select_active_state` from `wcd_core_dlkm.ko`; `swr_get_logical_dev_num` from `swr_dlkm.ko`). This correctly distinguishes proprietary stock module-to-module exports from missing new-kernel exports.

**Conclusion: The symbol-name and version-CRC compatibility gate PASSES for the complete extracted stock `vendor_dlkm` and `system_dlkm` module set, subject to the limits below.** This is much stronger than a Linux release-string match.

## Qualification boundaries

- **Not yet tested:** actual device boot on the new kernel, BakaSU manager supercall and root granting, SUSFS behavior, WildKernels runtime behavior, SELinux integration, all vendor drivers, modem, display, camera, vibration, audio, storage, and power management.
- **Not yet proven:** exact binary provenance of the Vibranium source revision used for the original Kamios boot image. Matching all observed module CRCs is strong ABI evidence, not proof that the new Image is an identical base.
- This check covered `vendor_dlkm` and `system_dlkm` partitions. It did **not** prove `vendor_boot` first-stage modules, device-tree overlay correctness, or kernel runtime symbol behavior.
- No patch was flashed to the user's running slot. The known-good original Kamios `boot_b` recovery remains available. **Do not flash raw `Image` into the boot partition**; it requires correct boot v4 packaging, and the first boot test needs a verified rollback.

Local machine evidence:
`D:\peridot-bakasu-ci-assets\builder\work\kamios-v1.1-20261027-kernel\stock-dlkm-abi\stock-vs-new-kernel-module-abi-report.json` and `stock-vs-new-kernel-cross-module-abi.json`.
