# Rooted 6.1.176 release qualification — blocked (2026-10-26)

**Release decision: NO ZIP / NO RELEASE.** An incomplete or wrong-UAPI rooted kernel must not be published as installable for KyneOS RI8 or the One UI 9 port.

## Source and evidence

- Pinned upstream reference: Mohithash Theettam `theettam-2.8` commit `38d491869bb5d4b4f5337548535f2f1dd3c834a1`. Verified `make kernelversion` = **6.1.176**. A full 1.7 GiB source checkout completed in isolated WSL staging at `/home/kyne/peridot-rooted-6176-experiment/source`.
- Existing owner's working rooted fullbundle source: POCO F6 stock kernel **6.1.138**, pinned common `0c3d559bcd85c64dae9c9c9687abbe5347fff3ad`, **ReSukiSU UAPI 5**, stock module trust configuration `CONFIG_MODULE_SIG_PROTECT=y` and `CONFIG_SYSTEM_TRUSTED_KEYS="certs/peridot-stock-public.pem"`.
- Upstream Theettam ReSukiSU pin `3c1882886dbbb54f4aae7ddf205f8ccde32c2a34` declares **KERNEL_SU_UAPI_VERSION = 2**, incompatible with the existing UAPI 5 root-management contract. The upstream `gki_defconfig` also has `CONFIG_MODULE_SIG_PROTECT=n` and `CONFIG_MODULE_SIG=n`, unlike the target hardware trust configuration.
- Existing owner's 6.1.138 fullbundle *tracked* kernel changes were captured as an isolated, local patch (SHA-256 `25ef523b1cb7fb7a925827c7fc7a614358d18ebc5c083c919ea973eea7775d02`, 140 KiB). Do not mistake this tracked patch alone for the full source/feature bundle; untracked sources, subtrees and dependencies must be staged and pinned separately.
- Direct `git apply --check` onto Theettam fails across **34** paths. With access to the original common Git blobs, a three-way merge applies most changes, but **17 files remain conflicted**; a separate isolated `mergeprobe` worktree retains these conflicts for investigation. No conflict was force-resolved by selecting one side automatically.

## Unresolved three-way merge paths

```text
drivers/Kconfig
drivers/Makefile
drivers/base/power/wakeup.c
fs/f2fs/f2fs.h
fs/proc/base.c
include/linux/tcp.h
include/net/tcp.h
include/uapi/linux/inet_diag.h
include/uapi/linux/rtnetlink.h
kernel/power/process.c
kernel/time/alarmtimer.c
lib/string.c
net/ipv4/sysctl_net_ipv4.c
net/ipv4/tcp_input.c
net/ipv4/tcp_ipv4.c
net/ipv4/tcp_output.c
net/ipv4/tcp_rate.c
```

## Prior module qualification

The stock-import comparison from the preceding investigation covered **772** preserved stock module instances and **42,978** import records. Against the maintainer's **older rooted KMI baseline** (not the exact v2.8 Image symvers), **19,926 import occurrences** disagree with the candidate reference, despite matching the old POCO kernel's CRCs. This does not substitute for an actual compiled 6.1.176 `Module.symvers`; it is an explicit reason to fail closed until a built candidate passes the repo's exact stock-module validator.

## Build attempt and safe stopping condition

The experimental build staging copied the stock configuration and module trust certificate into the isolated source. It was stopped after inspecting the actual cloned root driver's UAPI version 2: compiling it would create the wrong root flavor. There is **no completed 6.1.176 Image**, **no passing candidate stock ABI report**, **no ROM-specific boot/AVB package**, and **no device boot test**.

## Required work to unblock

1. Preserve the user's **ReSukiSU/BakaSU UAPI 5** driver and SUSFS integration, without silently downgrading to UAPI 2.
2. Manually reconcile and review all 17 three-way kernel conflicts; incorporate all required WildKernels dependencies (SUSFS, NoMount, BBG, NET, DS, NTSync, Ptrace, Unicode, BPF, Perf) and stock thermal/modem/camera/display behavior.
3. Compile a real Linux 6.1.176 kernel with trusted stock module certificate and CFI/config invariants.
4. Run `verify_rooted_6176.py` against the **actual compiled** `Module.symvers` and pinned stock vendor_boot, vendor_dlkm and system_dlkm modules. Reject any mismatched or unresolved imports.
5. Prepare independent guarded and rollback-aware KyneOS RI8 and One UI 9 installers; verify AVB and per-ROM boot chain. Finish device boot, radio/IMS, camera, GPU, thermal and root tests before shipping.

The main 6.1.138 workflow, existing root addon, ROM images and device were not modified. **No GitHub kernel release has been created.**
