# KamiOS 1.1 / POCO F6 BakaSU kernel audio boot stall — 2026-10-31

## Objective and hard constraints
Device: POCO F6 (peridot), KamiOS 17.0 2026-10-27 v1.1, active slot B, Android 17, kernel release `6.1.176-Vibranium-V18+`.
Restore fully bootable Android *with BakaSU support*. Explicit owner constraint: **do not reflash original/stock kernel**, do not format Data, and avoid unrelated partitions.

## Observed
- Android's `system_server` repeatedly hangs waiting for `IAudioFlingerService` and `IAudioPolicyService`. Boot animation remains running, `sys.boot_completed` stays blank.
- `/proc/asound/cards` reports *no soundcards*; `/sys/class/sound` contains only `timer`.
- `audioserver` thread waits in HIDL `BpHwDevicesFactory::openPrimaryDevice_7_1`. `/vendor/bin/hw/android.hardware.audio.service` sleeps in `libagm.so::device_init`.
- Kernel prints repeated `<msm_asoc_machine_probe><3064>: X, failed.`, followed by `platform soc: spf_core_platform:sound: deferred probe pending`. Qualcomm SoundWire and pinctrl components initially defer, then bind; the Pineapple ASoC sound card remains unregistered.
- The *exact* source line 3064 of `qcom/opensource/audio-kernel/asoc/pineapple.c` in `khargosxh18/android_kernel_xiaomi_sm8635-modules` is the generic error label. **Its message does not identify which earlier call failed.** Need additional probe-return instrumentation.
- Live FDT captured from OrangeFox into `runtime-fdt.dtb` on Windows. Sound node `/soc/spf_core_platform/sound` is compatible `qcom,pineapple-asoc-snd`, with expected codec targets: enabled `msm-stub-codec`, `lpass-cdc`, `wcd937x-codec`; disabled WSA883x codec #1/#2. These states alone do not explain the failure.
- Current kernel command line contains `fw_devlink.strict=1`. Vendor kernel source `drivers/base/core.c` supports `fw_devlink=permissive`; this *may* avoid strict supplier deferral but has not yet been tested successfully.
- A separate `vendor.cnd` crash occurs repeatedly inside `/vendor/lib64/libcne.so`; do not misclassify it as the primary sound-card failure.
- The full BakaSU UAPI6 + SUSFS + optional WildKernels kernel and the BakaSU+SUSFS-only **baseline** both reach ADB but remain on boot animation with the same audio failure. Thus optional WildKernels patches alone are not the root cause.
- Original `boot_b` was **never flashed during this investigation**. The experimental `boot_b` image and custom baseline are saved locally.

## On-device changes and results
1. Installed custom BakaSU+SUSFS baseline to slot B through OrangeFox. Installer verified and Android reached ADB; audio and framework still hung. Kernel Image SHA256 `5dadf7eab8ce403cd71e8c47e2a68d6eb22ce3bb5b4ed2a357f7e351d4451906`.
2. Backed up the full installed `boot_b` as `custom-baseline-boot-b-after-install.img`, SHA256 `7d9e4b5da16768add147d942bd2a5cf2cb748593ae793fe04f85afff44933f26`.
3. Two RAM-only `fastboot boot` attempts (one modified header, one modified kernel command-line string) yielded Android with **unchanged** `/proc/cmdline` and still no sound card. These are **inconclusive**, not successful tests of fw_devlink permissive behavior.
4. Submitted a slot-B `fastboot flash` using the custom baseline with only two equal-length embedded command-line-string substitutions; `fastboot` returned an async operation marker but its final stdout was not captured. A subsequent recovery reboot left the device absent from ADB, Fastboot and Windows Android/Qualcomm USB enumeration. **The write and boot effect must be verified once recovery access is restored; do not claim the flash succeeded.**
5. Prepared an AnyKernel3 OrangeFox ZIP of the patched custom Image using the known baseline installer, but **did not install that diagnostic ZIP**.

## CI and source state
- Branch `experiment/kamios-v18-bakasu-only-audio-probe` deliberately builds **BakaSU UAPI6 without SUSFS and without optional WildKernels** to isolate the remaining patch set.
- First isolation run `41201723338` **compiled Image, modules and Module.symvers successfully** but failed a post-build grep demanding `# CONFIG_NTSYNC is not set` even when NTSYNC has no Kconfig definition. Validation was amended to accept disabled or absent symbols.
- Follow-up run `41204519622` started. Verify GitHub Actions conclusion before treating an artifact as build-qualified; never infer pass from a compilation log alone.
- Workspaces: `D:\peridot-bakasu-ci-assets\builder\work\kamios-v1.1-20261027-kernel\bootloop-diag-20261031\` includes ANR stacks, native tombstones, ADB logs, FDT and copies of experimental images. No source evidence has been attached to a public issue.

## Immediate next actions
1. Re-establish ADB/OrangeFox or Fastboot through physical keys and USB. Until device enumerates, **no further device writes**. If slot B cannot boot after last experiment, restore the backed-up **custom BakaSU+SUSFS baseline**, *not stock*.
2. Verify current slot B boot SHA and whether `fw_devlink=permissive` actually reached `/proc/cmdline`. Collect `/sys/class/sound`, `/proc/asound/cards`, `sys.boot_completed`, and an ANR/audioserver trace.
3. Evaluate the successful BakaSU-only CI image when available and package an AnyKernel3 installer with verified SHA, then make one controlled recovery test.
4. If BakaSU-only also fails, instrument the Pineapple ASoC module around `msm_populate_dai_link_component_of_node` and `devm_snd_soc_register_card` for the *actual error return*; compare current exact module/DT ABI with known working original baseline **by reading, not reflashing stock**.
5. Keep kernel custom and compatible with KamiOS. Do not disable security checks globally, wipe user data, or modify unrelated partitions to hide the symptom.

**Status:** Diagnosis partially complete, boot fix **not verified**.
