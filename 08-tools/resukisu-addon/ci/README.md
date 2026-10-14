# GitHub-hosted POCO F6 BakaSU / SUSFS / WildKernels CI

**No self-hosted runner is necessary.** The kernel job uses the standard
`ubuntu-24.04` GitHub Actions virtual machine. The public repository's
runner currently has 4 vCPU, 16 GB RAM and a 14 GB SSD. This is a reasonable
starting point; builds that exceed disk/memory need further optimization.

The workflow watches the official
[ Baka-SU/BakaSU ](https://github.com/Baka-SU/BakaSU)
`main` branch twice daily, at 03:17 and 15:17 UTC (11:17 AM and 11:17 PM
Manila). For a new revision, the watcher **first checks the exact BakaSU
commit's SUSFS integration contract**. It only starts a kernel build when
there is no upstream hard-stop, no successful previous artifact, and the
SHA-256-pinned stock input bundle is configured.

## Current upstream SUSFS suspension (October 14, 2026)

The first GitHub-hosted build (run 38571059200) successfully downloaded
and verified the stock/source input archive, checked its kernel prerequisites,
and applied the pinned 10-feature WildKernels patch set. It then **failed
inside BakaSU's own kernel build** after approximately 25 minutes:

    kernel/tools/susfs_compat.mk:20: *** Please wait susfs update. Stop.

This is intentional. [BakaSU commit 48fa4bb](https://github.com/Baka-SU/BakaSU/commit/48fa4bb7ec8bddb8ea932a8c9be0877f89a1fa73)
on October 10 suspended SUSFS inline compilation pending synchronization
with upstream KernelSU. Simply bumping our pinned SUSFS commit cannot bypass
this unconditional guard safely.

**New fail-closed behavior:** the watcher fetches
`kernel/tools/susfs_compat.mk` at the **exact BakaSU commit being watched**,
rejects an explicit upstream `$(error ...)` stop, and emits a GitHub Actions
warning explaining that the upstream combination is unavailable. The 10
pinned SUSFS/WildKernels features stay enabled and unchanged. The expensive
kernel compilation is **skipped, not marked successful**. Even `force: true`
will not bypass upstream's compatibility suspension. Every scheduled check
retries automatically; when upstream removes the stop, CI may attempt full
compilation and all original stock module/ABI checks. A passing source
preflight is not itself a compatibility or device-boot guarantee.

## Why do we need an input bundle?

We **already have all required inputs locally**, but each GitHub-hosted job
starts on a fresh machine and cannot access files on the owner's PC.

The existing October 4 working build depends on the *precise patched kernel
source*, not just the stock `boot.img`. It also needs the stock kernel
configuration and public module verification certificate, original stock
images, the exact previous validated update ZIPs, kernel Module.symvers,
and proprietary system/vendor module files for CRC/import checks.

Because this is a public repository, **do not commit, publish as GitHub
Release assets, or upload proprietary vendor modules or personal files
to the public repository without distribution permission**. The clean
alternative is a private, owner-controlled HTTPS object store.

The original 688.8 MB input bundle was published in the user-owned
[CI inputs Release](https://github.com/Kyne0328/peridot-bakasu-kernel/releases/tag/ci-stock-inputs-20261014),
and its URL/SHA-256 are configured in repository Actions variables. Because
that repository is public, the archived original stock module and firmware
references are also publicly downloadable; their redistribution terms should
be reviewed separately.

The runner has **no OTA/private signing key**. The produced packages are
clearly UNSIGNED, not device tested, and do not modify the HyperOS ROM.

## One-time preparation on your PC

The original files are in `C:\Dev\hyperos4-peridot-research`, and the
known-good WSL source lives in `/home/kyne/peridot-resukisu-uapi5`.

First, prepare the allowlisted firmware/module inputs using Windows Python:

```powershell
cd C:\Dev\hyperos4-peridot-research
python 08-tools\resukisu-addon\ci\prepare_runner_assets.py --source-root C:\Dev\hyperos4-peridot-research --dest D:\peridot-bakasu-ci-assets
```

Then create the checksum-recorded source + stock bundle in WSL. The script
includes the preserved common and SUSFS source trees, config and known-good
Image, and the allowlisted stock module inputs; it excludes private signing
keys. It may take time because the preserved source tree is approximately
1.7 GB.

```bash
python3 /mnt/c/Dev/hyperos4-peridot-research/08-tools/resukisu-addon/ci/create_hosted_bundle.py \
  --preserved-source /home/kyne/peridot-resukisu-uapi5 \
  --prepared-assets /mnt/d/peridot-bakasu-ci-assets \
  --output /mnt/d/peridot-bakasu-stock-inputs.tar.gz
```

The command prints the resulting SHA-256. Store this package in a
**privately controlled HTTPS location** that the runner can download. The
URL must be stable and downloadable non-interactively; if it requires
authentication, configure a suitable expiring signed URL renewal process
or a small authenticated downloader **without putting credentials in the
repository**. The current downloader accepts an HTTPS URL, not a bearer
token, and verifies every byte against the expected SHA before extraction.

## GitHub configuration

Go to the kernel repository Settings -> Secrets and variables -> Actions
-> Variables and configure:

- `BAKASU_INPUT_BUNDLE_URL` — stable HTTPS URL to the owner-prepared
  stock/source input tar.gz, preferably a private signed URL.
- `BAKASU_INPUT_BUNDLE_SHA256` — full 64-character lowercase SHA-256
  printed by the bundler.

The kernel job intentionally **does not start until both variables are
configured**. The upstream watcher still runs and shows a clear warning,
rather than queuing forever for a non-existent self-hosted runner.

Then open Actions -> POCO F6 BakaSU + SUSFS + WildKernels ->
Run workflow; choose `force: true` if you want to rebuild the same
upstream revision. Builds only happen for scheduled/manual/dispatch runs;
source-code pushes validate the watcher and never flash/compile kernels.

## What will build and be verified

The existing pinned 6.1.138 Android GKI + pinned SUSFS and WildKernels
sources stay unchanged across BakaSU revisions. The builder requires
the existing ten feature flags:

SUSFS, NoMount, BBG, NET, DS, NTSync, Ptrace, Unicode, BPF, Perf.

Ptrace is correctly a no-op patch on Linux 6.1 (its compatibility patch
only applies to older kernels). Required UAPI 5, module signing contract,
kernel release, export ABI CRCs, import checks and trusted public module
certificate are validated before packaging.

Three rollback-aware, unsigned AnyKernel3 ZIP candidates are uploaded as
GitHub Actions artifacts: new BakaSU update, rollback to the pinned full
WildKernels build, and rollback to the original stock kernel. SHA-256 and
device/kernel hash guards are embedded and read back.

**Do not flash unverified CI candidates directly**. They still require
independent review, signing/recovery trust validation and a phone boot
test. If a new upstream BakaSU revision breaks source compatibility, the
job fails instead of silently disabling patches.

## Local workflow tests

```bash
python3 -m unittest discover -s 08-tools/resukisu-addon/ci -p 'test_*.py' -v
bash -n 08-tools/resukisu-addon/build_uapi5_full_bundle.sh
```

GitHub Actions watcher tests passed, and the existing known-good kernel
was used for a packaging smoke test. A *new BakaSU upstream full compile*
on GitHub has not yet succeeded, because the stock bundle is not
configured there.
