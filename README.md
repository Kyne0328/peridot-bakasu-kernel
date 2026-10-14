# POCO F6 BakaSU Kernel

Independent kernel build automation for **POCO F6 (peridot)**, separate from the [HyperOS 4 ROM port](https://github.com/Kyne0328/peridot-hyperos4-port).

This repository hosts a reproducible build *candidate* pipeline for the BakaSU project (formerly ReSukiSU), Android 14 GKI 6.1.138, SUSFS UAPI 5, and the ten features retained from the October 2026 WildKernels build.

## Current status

- **CI source migrated:** GitHub Actions watcher, pinned kernel recipe, stock-module compatibility validator, AnyKernel update/rollback packager and offline tests.
- **Tested locally:** upstream watcher logic and reproduction of three **unsigned** AnyKernel candidates from an already-built known-good kernel.
- **Not yet operational end to end:** GitHub-hosted Ubuntu builds are configured, but the one-time owner-prepared checksum-pinned stock/source input archive still must be hosted and repository input variables configured before full kernel compilation can start.
- **Not tested on device:** CI artifacts are neither signed for recovery nor automatically flashed. No automatic GitHub Releases.

## Workflow

[POCO F6 BakaSU + SUSFS + WildKernels](.github/workflows/peridot-bakasu-fullbundle.yml) polls [Baka-SU/BakaSU](https://github.com/Baka-SU/BakaSU) `main` twice daily and skips commits with a still-available successful Actions artifact.

On a new commit, a standard **GitHub-hosted `ubuntu-24.04` runner** builds against the **pinned** kernel, SUSFS and WildKernels dependency set, provided its checksum-verified stock/source input archive is configured. Changes to BakaSU alone are tracked automatically. If the new upstream revision breaks the expected UAPI 5 kernel layout, source integration, kernel ABI, module signature validation or build, the job fails instead of publishing an unverified update.

Only when all checks pass does it upload **three unsigned candidates**: an update and rollback archives for the pinned full WildKernels kernel and the original stock kernel. These candidates must be independently reviewed, signed and device-tested before flashing.

## Repository layout

- `.github/workflows/peridot-bakasu-fullbundle.yml` — scheduled watcher and isolated build job.
- `08-tools/resukisu-addon/build_uapi5_full_bundle.sh` — source-pinned Android GKI, BakaSU, SUSFS and WildKernels build.
- `08-tools/resukisu-addon/verify_uapi5_full_bundle.py` — offline stock-module ABI and kernel configuration checks.
- `08-tools/resukisu-addon/ci/` — revision watcher, test suite, standalone module helpers, unsigned packaging and setup instructions.

## Setup

See [the CI setup and security guide](08-tools/resukisu-addon/ci/README.md).

This public repo **does not contain** ROM images, extracted vendor modules, source kernel worktrees, signing keys, personal files, or a flash-ready proprietary release. Device/vendor artifacts are intentionally absent from Git. The owner must provide a privately stored checksum-pinned input archive to the temporary GitHub-hosted runner; uploading proprietary material into the public repository is not required.

**Kernel flash order:** install and verify the compatible HyperOS ROM first, then install a separately approved BakaSU kernel ZIP. BakaSU is intentionally not bundled in the ROM.

Third-party kernel and patch sources are fetched at their pinned upstream revisions; their respective licenses and author credits remain with their original projects.
