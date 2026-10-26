# Rooted 6.1.176 stock-KMI experiment

This branch is **not flashable**. It adds the first fail-closed validation component for a future POCO F6 Android14 GKI Linux 6.1.176 **ReSukiSU + SUSFS** rebuild. The existing pinned 6.1.138 BakaSU UAPI5/WildKernels workflow and rollback artifacts are unchanged.

## Why the gate exists

The Theettam 2.8 rooted release uses a distinct kernel build and KMI. An independent read-only comparison found that the 6.1.138 stock module CRC references disagree with its *published v2.6 rooted KMI baseline* on many imports; these counts are import occurrences, not unique symbols. This is not a byte-accurate ABI result for the v2.8 Image. A new build must instead be checked against the **actual generated Module.symvers** and every preserved POCO module before packaging.

## Usage

The gate is deliberately **not** wired to the old 6.1.138 packaging workflow. In an isolated build producing a rooted Linux 6.1.176 candidate, with the existing stock input archive unpacked and a verified stock certificate:

```bash
python3 08-tools/resukisu-addon/ci/verify_rooted_6176.py \
  --image /isolated/out/arch/arm64/boot/Image \
  --config /isolated/out/.config \
  --symvers /isolated/out/Module.symvers \
  --release 'ACTUAL_VERIFIED_6.1.176_KERNEL_RELEASE' \
  --report /isolated/reports/rooted-6176-abi.json
```

`BAKASU_CI_ASSET_ROOT` must point at the **pinned stock hardware inputs**. The tool reuses the existing stock-module collector, ELF parser and signature checks. It requires ReSukiSU and SUSFS config options, `CONFIG_MODVERSIONS`, `CONFIG_MODULE_SIG_PROTECT`, `CONFIG_CFI_CLANG`, the stock public trust certificate in config **and Image**, an exact kernel release banner, and passing module imports and signatures. The report is written even when a check fails. A passing report is only an **offline result**, never proof of runtime support.

## Remaining work before an Image can be considered

1. Pin a 6.1.176 kernel source revision and exact root/SUSFS integration commits compatible with the owner's maintained UAPI5 and WildKernels features. Verify license and dependency provenance.
2. Produce a separately staged source/config build without modifying the working 6.1.138 tree; retain the original kernel KMI (or prove a replacement module set is compatible).
3. Run this gate on the **actual compiled** `Image` and `Module.symvers`; fix incompatibilities in source/config, not by disabling kernel module CRC/signature checks.
4. Check root manager UAPI and full ten-feature set. Verify separate boot/init_boot/vendor_boot/AVB packaging for RI8 and One UI 9, without overwriting either existing image.
5. Require safe on-device boot, module loading, camera, graphics, calls/IMS, Wi-Fi, suspend and thermal regressions before approval.

**No device flash, ROM modification, signing, release, or successful 6.1.176 compilation is represented by this branch.**
