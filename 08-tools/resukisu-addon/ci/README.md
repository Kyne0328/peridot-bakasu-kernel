# POCO F6 BakaSU / SUSFS / WildKernels automation

Workflow: .github/workflows/peridot-bakasu-fullbundle.yml

BakaSU was formerly called ReSukiSU. The upstream is
https://github.com/Baka-SU/BakaSU.

## Automatic behavior

GitHub Actions polls official BakaSU main twice daily at 03:17 and
15:17 UTC (11:17 AM / 11:17 PM Manila). Manual workflow_dispatch
and optional bakasu-updated repository_dispatch are supported.

The watcher checks GitHub Actions artifacts to skip already-built
40-character BakaSU commits. A new revision queues a dedicated,
isolated Linux self-hosted runner with labels:
self-hosted, linux, x64, peridot-kernel.

The full-bundle builder preserves the pinned kernel 6.1.138 source,
SUSFS and WildKernels dependencies, changing only the BakaSU git SHA.
The ten existing features stay selected:
SUSFS, NoMount, Baseband Guard, Networking, DroidSpaces, NTSync,
Ptrace compatibility, Unicode, BPF and Performance.

For Linux 6.1, the WildKernels ptrace patch remains intentionally
unapplied, matching its upstream compatibility contract. The
corresponding feature toggle is still documented in build receipts.

After compilation, the original stock module compatibility verifier
checks kernel release, required config flags and UAPI, public stock
module trust, module import compatibility, and export-symbol CRCs.
Missing evidence or incompatibility aborts the workflow.

A successful check produces three separately downloadable, UNSIGNED
AnyKernel3 ZIP candidates:
- Update, guarded for known stock/UAPI5 kernels and latest verified
  CI artifact Image when that artifact is still available.
- Rollback to the October 4 pinned full WildKernels kernel.
- Rollback to the exact known stock kernel.

All outputs include SHA-256 receipts, feature and source provenance,
plus strict POCO F6 device and boot kernel hash guards. CI neither
auto-installs anything on the phone nor modifies the HyperOS ROM.
No GitHub Release is created automatically.

## Not active remotely yet

The workflow lives in Kyne0328/peridot-bakasu-kernel on main.
The watcher will run in GitHub Actions on its schedule once accepted.
No self-hosted runner is currently confirmed as registered.

### Dedicated runner

Do not use an unattended external-source build runner that can
access private ROM signing keys, personal files, ADB, or privileged
tokens. Use a separate isolated Ubuntu 24.04 x64 runner, with the
label peridot-kernel, a large working disk, the full build toolchain,
and NO private signing keys.

Install git, rsync, patch, GNU make, Clang 18, LLVM utilities,
openssl, Python 3 with cryptography, bc, bison, flex, libelf,
and standard kernel build dependencies.

Provide the existing known-good original UAPI5 base source tree,
previously /home/kyne/peridot-resukisu-uapi5, with common,
susfs4ksu, out-uapi5/.config and
out-uapi5/arch/arm64/boot/Image. Do not modify that source tree.

### Safe stock-module asset provisioning

The local repository stores stock ROM images, old kernel ZIPs,
extracted stock modules and a PUBLIC signing certificate outside
Git, in ignored caches. They will not exist on a GitHub-hosted runner.
Use this manual allowlisted provisioning script on the owner machine:

    python3 08-tools/resukisu-addon/ci/prepare_runner_assets.py --source-root /mnt/c/Dev/hyperos4-peridot-research --dest /srv/peridot-bakasu-assets

It copies only required boot/vendor_boot image, modules,
Module.symvers, publicly distributable signing certificate, and
the old AnyKernel/UAPI5 source ZIPs. It does NOT copy any private
keys, other ROM files or arbitrary source directories. Review
asset-inventory.json and transfer the resulting directory into
your isolated runner VM. Never mount your full private development
directory in an unattended builder.

Provide the three repository-level Actions variables:

    BAKASU_BASE_SOURCE=/srv/peridot-uapi5-base
    BAKASU_ASSET_ROOT=/srv/peridot-bakasu-assets
    BAKASU_STOCK_CERT=/srv/peridot-bakasu-assets/.cache/resukisu-uapi5-finalize/stock-module-public.pem

The paths must exist on the self-hosted runner. The runner account
needs sufficient permission to read them. Its own working folder
and temp drive must have enough room for a full GKI build.

Push the scripts, verifier, CI directory and GitHub workflow to
the default branch. Open Actions > POCO F6 BakaSU + SUSFS +
WildKernels > Run workflow for a first manual check.

## Safety and limits

- BakaSU main is dynamic; kernel/common, SUSFS, WildKernels, BBG,
  NoMount, kernel patches, DroidSpaces and all other dependency SHAs
  are fixed to the last offline-verified source revisions.
- BakaSU may change Kconfig, UAPI version, Kbuild, hooks or symbols.
  The build MUST FAIL on such incompatibility instead of packaging
  unvalidated kernel firmware. Manual code review is then needed.
- ZIPs are explicitly UNSIGNED automated candidates, not trusted
  OrangeFox releases. Stock module checks are not a boot test.
  Sign and device-verify in a separate, trusted release workflow.
- Never put private OTA or kernel signing keys on a runner that
  automatically compiles new third-party source.
- Scheduled workflows poll, do not receive instant upstream events;
  GitHub may delay them or disable schedules on inactive public repos.
- Artifacts expire after 30 days. Rebuilding an old revision after
  artifacts expire is expected.
- Recovery rollback to the last arbitrary CI version requires the
  previous Image; these packages instead include rollback to the
  known-good October 4 full bundle and to stock.

## Offline tests

    python3 -m unittest discover -s 08-tools/resukisu-addon/ci -p "test_*.py" -v
    bash -n 08-tools/resukisu-addon/build_uapi5_full_bundle.sh
    python3 -m py_compile 08-tools/resukisu-addon/ci/*.py

The first smoke test reproduced three unsigned update/rollback ZIP
packages using the October 4 verified kernel Image. It did not
compile a new BakaSU upstream revision or test on the phone.

The preexisting peridot-builder-smoke.yml workflow is unrelated.
