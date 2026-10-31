#!/usr/bin/env bash
set -euo pipefail

# Kamios V1.1 POCO F6 in-tree source qualification. NEVER flashes a device.
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
STAGE="$1"
test -n "$STAGE" && test ! -e "$STAGE" || { echo "Stage must be a new path" >&2; exit 2; }
CONFIG="$ROOT/configs/kamios-v1.1-20261027-vibranium-v18.config"
KSRC=4b42813174f309838106763126c8d3c8f14e96b2
KSU=5785bdb8091304322f597f67d50e0b79f9815cb2
SUS=ee155a1ad4219804a7c54cb39dd4fa1b5c2a3fa4
RELEASE=6.1.176-Vibranium-V18+
echo "4d77d949c21ecbd14d64286c51476fae6091cfa7ed89b1642db18b8eae7258db  $CONFIG" | sha256sum -c -
mkdir -p "$STAGE"
STAGE="$(cd "$STAGE" && pwd)"
SRC="$STAGE/vibranium"
OUT="$STAGE/out"
mkdir -p "$OUT" "$STAGE/report"
git clone --depth=1 --single-branch --branch 17 https://github.com/khargosxh18/android_kernel_xiaomi_sm8635.git "$SRC"
test "$(git -C "$SRC" rev-parse HEAD)" = "$KSRC"
git clone --depth=1 https://github.com/Baka-SU/BakaSU.git "$SRC/KernelSU"
git -C "$SRC/KernelSU" fetch --depth=1 origin "$KSU"
git -C "$SRC/KernelSU" checkout --detach "$KSU"
test "$(git -C "$SRC/KernelSU" rev-parse HEAD)" = "$KSU"
grep -q 'KERNEL_SU_UAPI_VERSION = 6' "$SRC/KernelSU/uapi/supercall.h"
ln -s ../KernelSU/kernel "$SRC/drivers/kernelsu"
printf '\nobj-$(CONFIG_KSU) += kernelsu/\n' >> "$SRC/drivers/Makefile"
printf '\nsource "drivers/kernelsu/Kconfig"\n' >> "$SRC/drivers/Kconfig"

git clone --depth=1 --branch gki-android14-6.1 https://gitlab.com/simonpunk/susfs4ksu.git "$STAGE/susfs4ksu"
git -C "$STAGE/susfs4ksu" fetch --depth=1 origin "$SUS"
git -C "$STAGE/susfs4ksu" checkout --detach "$SUS"
test "$(git -C "$STAGE/susfs4ksu" rev-parse HEAD)" = "$SUS"
P="$STAGE/susfs4ksu/kernel_patches"
PATCH="$P/50_add_susfs_in_gki-android14-6.1.patch"
if test ! -s "$PATCH"; then PATCH="$P/50_add_susfs_in_kernel-6.1.patch"; fi
test -s "$PATCH" || { echo "SUSFS 6.1 patch not found" >&2; exit 3; }
python3 "$ROOT/08-tools/resukisu-addon/port_susfs_v18.py" "$PATCH" "$STAGE/report/susfs-v18-rebased.patch"
PATCH="$STAGE/report/susfs-v18-rebased.patch"
cp -a "$P/fs/." "$SRC/fs/"
cp -a "$P/include/linux/." "$SRC/include/linux/"
if ! (cd "$SRC" && patch -p1 --fuzz=0 --dry-run --forward < "$PATCH") > "$STAGE/report/susfs-check.txt" 2>&1; then
  cat "$STAGE/report/susfs-check.txt"
  echo "SUSFS needs source-specific hand-port; refusing fuzzy patch" >&2
  exit 4
fi
(cd "$SRC" && patch -p1 --fuzz=0 --forward < "$PATCH")
git -C "$SRC" diff --check

cp "$CONFIG" "$OUT/.config"
"$SRC/scripts/config" --file "$OUT/.config" -e KSU -e KSU_SUSFS -d KSU_TRACEPOINT_HOOK -d KSU_MANUAL_HOOK -d LOCALVERSION_AUTO
make -C "$SRC" O="$OUT" ARCH=arm64 LLVM=1 olddefconfig
make -C "$SRC" O="$OUT" ARCH=arm64 LLVM=1 -s kernelrelease > "$STAGE/report/kernelrelease.txt"
grep -qx "CONFIG_KSU=y" "$OUT/.config"
grep -qx "CONFIG_KSU_SUSFS=y" "$OUT/.config"
grep -qx "CONFIG_LTO_CLANG_FULL=y" "$OUT/.config"
grep -qx "CONFIG_MODVERSIONS=y" "$OUT/.config"
grep -qx "CONFIG_MODULE_SIG_PROTECT=y" "$OUT/.config"
grep -qx "$RELEASE" "$STAGE/report/kernelrelease.txt"
git -C "$SRC" diff --stat > "$STAGE/report/diffstat.txt"
printf 'preflight OK: V18 candidate + pinned BakaSU UAPI6 + SUSFS patch + stock Full LTO\n'
BUILD_KERNEL="${BUILD_KERNEL:-0}"
if test "$BUILD_KERNEL" = 1; then
  make -C "$SRC" O="$OUT" ARCH=arm64 LLVM=1 -j2 Image modules
  test -s "$OUT/arch/arm64/boot/Image" && test -s "$OUT/Module.symvers"
  sha256sum "$OUT/arch/arm64/boot/Image" "$OUT/Module.symvers" > "$STAGE/report/SHA256SUMS.txt"
fi
