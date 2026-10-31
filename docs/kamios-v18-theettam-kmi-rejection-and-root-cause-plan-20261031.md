# KamiOS 1.1 Vibranium V18 root-kernel regression — source-equivalence and Theettam comparison

Date: 2026-10-31. Device POCO F6 peridot, Android 17, KamiOS 1.1 October 27, active slot B. User authorizes root integration and recovery experiments but **forbids flashing the original stock kernel or wiping Data**.

## Confirmed boot regression

The shipped KamiOS v1.1 stock kernel boots and has functioning Qualcomm audio. Our rebuilt Vibranium V18 with (1) BakaSU UAPI6 + SUSFS + WildKernels, (2) BakaSU+SUSFS only, and (3) BakaSU-only all reach ADB but stay stuck at boot animation, `sys.boot_completed` empty, `/sys/class/sound` contains only `timer`. `system_server` waits for AudioFlinger/AudioPolicy, audio HAL blocks waiting for a primary sound device. Pineapple ASoC card `soc:spf_core_platform:sound` never binds, even though pinctrl, LPASS CDC, VA/TX/RX macros, WCD937x and AW882xx drivers eventually bind. The generic `msm_asoc_machine_probe` failure does not print a failing DAI/component/return code.

The source of the **exact shipped kernel binary** has NOT been proven. The public kernel source branch 17 at `khargosxh18/android_kernel_xiaomi_sm8635@4b42813174f309838106763126c8d3c8f14e96b2` was last updated October 24, whereas shipped ROM is October 27. Build configuration matches except BakaSU/SUSFS additions and build environment conditional. Both stock and rebuilt kernels use Android Clang 21 r563880c and BTF; stock raw kernel Image SHA256 `4f2f0c6dcbbd26b9cd696e24268d77e50dae5c5e20bbff82a259fa7f031913fb`, size 42,588,672; BakaSU-only Image SHA256 `a96818f46138cefcf3861c973e450557e3d7f58e5407ae2885af4efc94cb898a`, size 42,789,376. Size difference alone doesn't prove source mismatch.

### Theettam alternative: **DO NOT FLASH directly on KamiOS**

Theettam v2.8 `Mohithash/kernel_xiaomi_sm8635@theettam-2.8` (2026-09-05) is based on the GuidixX GKI kernel with Neutron Clang 23, BORE and ADIOS. It offers KernelSU-Next, SukiSU-Ultra and ReSukiSU — **not BakaSU UAPI6**. Its boot kernel release and scheduling stack differ from KamiOS Vibranium V18 (WALT).

Fetched the project's **own published** `scripts/ci/kmi-baseline/ksun-susfs.symvers` (15,990 name/CRC pairs, SHA256 `e5e895fa4354c833149962a10f407bafedfab3f813f5b597676d5d21e9ad8b0f`) and independently compared against the `__versions` imports in all **463 original KamiOS stock modules** extracted from integrity-checked OTA `vendor_dlkm` and `system_dlkm`:

- 26,542 versioned symbol references total.
- 11,319 names and CRCs match Theettam's baseline.
- **12,336 CRC mismatches** (2,389 unique names), affecting **all 463 modules**.
- **2,887 references** absent from Theettam's baseline (some are stock module-to-module exports, so absence alone is not conclusive).
- **`module_layout` mismatches for every one of the 463 stock modules.**

Therefore the Theettam release cannot be considered binary-compatible with the current KamiOS vendor module set. Do not use its AnyKernel3 release without a requalification/rebuild against the correct hardware/vendor sources. The **new BakaSU V18 build**, by contrast, had zero CRC mismatches vs original modules, though this does not prove runtime compatibility. This is direct evidence against substituting the whole Theettam kernel, but Theettam's build/testing techniques can be borrowed.

## Follow-on actions started

1. Isolated BakaSU UAPI6-only diagnostic `sound/soc/soc-core.c` branch `experiment/kamios-v18-asoc-diagnostics` CI run [41208298975](https://github.com/Kyne0328/peridot-bakasu-kernel/actions/runs/41208298975) **succeeded**. Five source-context-checked rate-limited prints identify missing codec, CPU DAI, platform, failed link, or card bind return. Raw Image SHA256 `53af7d12729303fd24770999c82b3ba969faa5ff59db35280a8658403f74688e`, `Module.symvers` exactly same as prior BakaSU builds. Prepared matching 64-bit AnyKernel3 ZIP locally but **NOT flashed**: `D:\peridot-bakasu-ci-assets\builder\work\kamios-v1.1-20261027-kernel\bootloop-diag-20261031\Kamios-V18-BakaSU-UAPI6-ASoC-DIAGNOSTICS-OrangeFox-BOOT-UNTESTED.zip`, SHA256 `808197bf6e0375c29de8cfc6443795d5eeceeb128ee81f540744d490e378f6c9`.
2. Created `experiment/kamios-v18-plain-source-control` to build the same pinned Vibranium source/stock config/Clang 21 with **`CONFIG_KSU=n`**, SUSFS and WildKernels off: CI run [41211432673](https://github.com/Kyne0328/peridot-bakasu-kernel/actions/runs/41211432673) started at 2026-10-31 14:43 UTC. Source control build is **diagnostic only, not a production root candidate**. If plain rebuild also breaks audio then source/build mismatch is established independent of BakaSU; if it boots audio successfully, investigate BakaSU LSM/hooks and their effect on ASoC/SELinux. **No claim about result until it finishes and can be boot-tested.**
3. Device last checked from Windows was not enumerating over ADB/Fastboot. The last confirmed state from previous work was OrangeFox recovery on slot B with custom BakaSU-only image `boot_b` SHA256 `14bab1e7047c4b032418a4cb1cbac7cd506081d76a06a3b5a40c79656d50e1f9`. Both a previous BakaSU+SUSFS baseline and the BakaSU-only image have Windows backups. No original boot restored.
4. Next discriminating real-world test is to install the read-only-diagnostic ASoC image from OrangeFox *only after* verifying recovery, slot, and current boot backup. Capture `ASoC_DIAG` kernel log, identify missing DAI/return code; patch actual root cause, rebuild, validate ABI, and test Android boot. Do not patch all device links or bypass SELinux to mask a probe failure.

**Status**: production fix not yet confirmed. The public source may differ from the shipped binary; alternate Theettam kernel is not safe as direct substitute. Maintain user's original-stock-flash prohibition.
