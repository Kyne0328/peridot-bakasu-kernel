# Kamios V18 — in-tree BakaSU UAPI 6 and SUSFS qualification

## Provenance and scope
- Target: first-party POCO F6 (peridot), Kamios v1.1 Android 17.
- Running and recovered: `6.1.176-Vibranium-V18+`, slot B, stock original boot.
- Kernel candidate: `khargosxh18/android_kernel_xiaomi_sm8635` branch `17`, commit `4b42813174f309838106763126c8d3c8f14e96b2`. Public POCO F6 references credit this source as Vibranium base; **exact build-commit equivalence to the shipped Kamios boot image is not yet established**.
- BakaSU UAPI6 commit: `5785bdb8091304322f597f67d50e0b79f9815cb2`.
- SUSFS android14-6.1 commit: `ee155a1ad4219804a7c54cb39dd4fa1b5c2a3fa4`.
- Original kernel configuration: `configs/kamios-v1.1-20261027-vibranium-v18.config`, SHA256 `4d77d949c21ecbd14d64286c51476fae6091cfa7ed89b1642db18b8eae7258db`.
- Original kernel built with Android Clang 21 release `r563880c`; **Full LTO** (`CONFIG_LTO_CLANG_FULL=y`), not ThinLTO. Retain module signature protection and modversions.

## Observed CI qualification
- [First source preflight](https://github.com/Kyne0328/peridot-bakasu-kernel/actions/runs/41189636375): one SUSFS patch hunk rejected for `fs/proc/task_mmu.c`; Vibranium changes the function preceding `show_map_vma` from a void seq formatter to an optimized int-returning formatter.
- `08-tools/resukisu-addon/port_susfs_v18.py`: tightly scoped rebase of this upstream patch's declaration-block placement. No fuzzy or forced application of rejected hunks.
- [Successful BakaSU + SUSFS preflight](https://github.com/Kyne0328/peridot-bakasu-kernel/actions/runs/41189863458): source integration, zero-fuzz SUSFS patching, Kconfig `CONFIG_KSU=y`, `CONFIG_KSU_SUSFS=y`, `CONFIG_LTO_CLANG_FULL=y`, modversions and module signature protection, exact local kernel-release string **passed**.
- [WildKernels patch probe](https://github.com/Kyne0328/peridot-bakasu-kernel/actions/runs/41190074505) against integrated source, pinned `WildKernels/kernel_patches@41ae18b35d20e0c6ac04116785a4a1089528ae94`:

| Feature patch | Dry-run result |
|---|---|
| NTSync compatibility | applies (must assess with base in order) |
| NTSync base | applies (must assess with compatibility in order) |
| Unicode fix | applies |
| Memory prefetch | applies |
| BBRv3 networking | needs source-specific port or may already overlap with source |
| F2FS congestion reduction | needs source-specific port |
| Freeze timeout reduction | needs source-specific port; upstream kernel recently changed freeze behavior |

Applying cleanly is **not** a functionality, KMI, performance, or hardware-compatibility test. BBG, NoMount, DroidSpaces, BPF, and other WildKernels features are not integrated by this probe. Do not bulk-apply every WildKernels patch to a stable device kernel without per-feature qualification.

## Open critical gates
1. Establish exact source identity: reproduce unmodified stock `Image` as closely as possible, record build reproducibility limits (compiler, timestamps, built-in build keys), compare the stock ABI and shipped vendor/system modules. The source is a credible Vibranium family candidate, not a proven bit-for-bit V18 provenance match.
2. Review the optimized `show_vma_header_prefix()` return-value handling in the SUSFS open-redirect branch; original SUSFS patch assumes the older API.
3. Build BakaSU+SUSFS in-tree with the pinned Clang 21 **Full LTO** and sufficient memory. Prior vanilla-source CI progressed through many objects but received a hosted-runner shutdown at the `vmlinux.o` link; this did not establish a compiler error. Local Windows host has ~16 GiB RAM and was under memory pressure at inspection.
4. Compare resulting `Module.symvers` and kernel exports against every shipped stock `.ko` dependency and original kernel ABI; changing a version string is not an ABI guarantee.
5. Validate resulting kernel Image format and original boot v4 packaging; test only on explicitly recoverable unlocked POCO F6 with the confirmed stock `boot_b` rollback, then test camera, calls, display, fingerprint, audio, modem, Wi-Fi, encryption, charging and suspend/resume.
6. Only then select the WildKernels patches for production use and repeat the qualification. No flashed, rooted, or boot-verified full kernel exists from this track yet.

## Repository implementation
- `08-tools/resukisu-addon/build_kamios_v18_in_tree.sh`: clones pinned source into new non-overwriting working directory; integrates pinned BakaSU and SUSFS, verifies exact stock config contract; optionally compiles `Image modules` with `BUILD_KERNEL=1`. No device flashing or automatic publishing.
- `08-tools/resukisu-addon/port_susfs_v18.py`: source-specific proc-maps patch context adaptation, with fail-closed match.
- `08-tools/resukisu-addon/probe_wildkernels_v18.sh`: selective dry-run patch applicability, does not modify source.
- `.github/workflows/kamios-v18-in-tree-preflight.yml`: verifies preflight and uploads diagnostics, not a flashable artifact.

This is an isolated integration branch in `Kyne0328/peridot-bakasu-kernel`, **not a literal hosted GitHub fork of the upstream kernel repository**.
