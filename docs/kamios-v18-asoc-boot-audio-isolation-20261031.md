# KamiOS V18 / POCO F6: BakaSU-only boot isolation and ASoC diagnostics

**Recorded:** 2026-10-31. **Target:** owner-authorized POCO F6 peridot, KamiOS 1.1 Android 17, active slot `_b`, `6.1.176-Vibranium-V18+`.

## User safety requirement
Do **not** flash original/stock kernel and do **not** format Data. Keep original boot image separately as evidence; do not deploy it. All on-device work to date targeted only current slot `boot_b`, using the known AnyKernel3 recovery installer or read-only ADB.

## Recovery from POCO-logo hang
- OrangeFox ADB resumed normally in slot B.
- Read-only `sha256sum /dev/block/by-name/boot_b` returned `7d9e4b5da16768add147d942bd2a5cf2cb748593ae793fe04f85afff44933f26`, **identical to the already backed-up 100,663,296-byte custom BakaSU+SUSFS baseline**. Therefore the experimental built-in commandline patch did *not* persist to `boot_b`; do not repeat ad hoc binary string patches.
- First-party baseline recovery file: `D:\peridot-bakasu-ci-assets\builder\work\kamios-v1.1-20261027-kernel\bootloop-diag-20261031\custom-baseline-boot-b-after-install.img` (not stock).

## BakaSU-only isolation test
- [Clang21 Full-LTO full build passed](https://github.com/Kyne0328/peridot-bakasu-kernel/actions/runs/41204519622); no SUSFS, no WildKernels. Raw Image SHA256 `a96818f46138cefcf3861c973e450557e3d7f58e5407ae2885af4efc94cb898a`; `Module.symvers` SHA256 `11567abf02997de71fb49b2a434087d70823ab089dfd99209e9843f5d326c776`.
- An independent working-directory archive check verified both, plus the embedded config. Same 17,786-symbol CRC export list as prior custom builds.
- A dedicated active-slot AnyKernel3 OrangeFox ZIP was assembled and SHA-validated: `Kamios-V18-BakaSU-UAPI6-ONLY-Audio-Isolation-OrangeFox.zip`, ZIP SHA256 `cf8640e0b86405d4bd4d55ab7f0d0cc93d48df54cdc47a8aae4a9d7a01056689`. No stock image included.
- Recovery installer completed without errors. ADB read-back of the full `boot_b` verified new Image SHA256 `a96818...` and actual boot SHA256 `14bab1e7047c4b032418a4cb1cbac7cd506081d76a06a3b5a40c79656d50e1f9`. Verified `CONFIG_KSU=y`, `# CONFIG_KSU_SUSFS is not set`, and NTSync absent.
- Android starts `system_server`, `audioserver`, and the boot animation; **`sys.boot_completed` remains empty**. `/sys/class/sound` still contains only `timer`, no ALSA sound card. This reproduces the failure with **BakaSU only**, thereby ruling out SUSFS and WildKernels as sole causes. The phone was sent back to OrangeFox after capturing logs.

## Audio probe evidence
- Boot logs contain `msm_cdc_pinctrl_get_gpiodata: platform device not found!`, `lpass_cdc_va_macro_probe: failed to get swr pin state`, followed by `<msm_asoc_machine_probe><3064>: X, failed.` and the sound platform's deferred-probe report. These early errors may be caused by initialization ordering.
- Later read-only sysfs inspection confirms each *platform driver is bound*: `rx-macro`, `tx-macro`, `va-macro`, `wcd937x-codec`, `soc:spf_core_platform:lpass-cdc`, both `rx_swr_clk_data_pinctrl` and `tx_swr_clk_data_pinctrl`, and the AW882xx smart amplifier I2C devices `4-0034`/`4-0035`. **The exception is `soc:spf_core_platform:sound`, which never binds.**
- The exact module source `qcom/opensource/audio-kernel/asoc/pineapple.c` prints generic line 3064 from the catch-all error label. It doesn't expose which earlier operation returned `-EPROBE_DEFER`. No conclusive evidence yet for a specific missing DAI, platform component, CPU component, or actual internal return.
- Stock Kamios `vendor_dlkm` + `system_dlkm` 463-module versioned symbol check: 25,608 new-kernel export CRCs match exactly, 934 additional imports provided by other existing modules, 0 mismatched. **Symbol CRC agreement does not prove runtime behavior or source equivalence.**

## New diagnostic instrumentation
- Isolated branch: `experiment/kamios-v18-asoc-diagnostics`.
- Source build script adds five **fail-closed, source-context-checked diagnostic changes** to `sound/soc/soc-core.c`: make missing codec/platform/CPU component debug lines error-ratelimited; report failed per-DAI link and `snd_soc_bind_card` return code. No skipped driver checks, disabled security enforcement, altered device-tree overlays, or behavior changes intended.
- [Full diagnostics build workflow](https://github.com/Kyne0328/peridot-bakasu-kernel/actions/runs/41208298975), start 2026-10-31T14:02:48Z. **A successful CI build and boot of this kernel have not yet been established.** Do not flash until its kernel Image, boot v4 installer, ABI/checksums and rollback are qualified.
- Diagnostics should identify the missing ASoC component or error code. Only then make a source-specific fix; avoid repeated speculative boot toggles or blanket changes to `fw_devlink`.

## Current device and rollback
- At last verified read: OrangeFox ADB online, `peridot`, slot B; original/stock kernel has **not** been flashed. Data was not formatted.
- Custom BakaSU-only `boot_b` read-back saved to `D:\peridot-bakasu-ci-assets\builder\work\kamios-v1.1-20261027-kernel\bootloop-diag-20261031\bakasu-only-flashed-boot-b.img`, SHA256 `14bab1...`.
- Previous custom BakaSU+SUSFS `boot_b` read-back saved as `custom-baseline-boot-b-after-install.img`, SHA256 `7d9e4b...`; it reaches ADB but fails audio startup, not a complete working ROM boot.
- Do not describe any of these candidates as boot-qualified production. The original KamiOS boot worked before experimental kernel changes but the owner explicitly forbids restoring it.
