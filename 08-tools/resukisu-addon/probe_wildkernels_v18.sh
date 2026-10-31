#!/usr/bin/env bash
set -euo pipefail
STAGE="$1"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SRC="$STAGE/vibranium"
REPORT="$STAGE/report"
test -d "$SRC/fs" && test -d "$REPORT"
WKP=41ae18b35d20e0c6ac04116785a4a1089528ae94
git clone --depth=1 https://github.com/WildKernels/kernel_patches.git "$STAGE/wildkernel-patches"
git -C "$STAGE/wildkernel-patches" fetch --depth=1 origin "$WKP"
git -C "$STAGE/wildkernel-patches" checkout --detach "$WKP"
test "$(git -C "$STAGE/wildkernel-patches" rev-parse HEAD)" = "$WKP"

OUT="$REPORT/wildkernels-compatibility.tsv"
printf 'feature\tresult\tpatch\n' > "$OUT"

probe() {
  local label="$1" relative="$2" file="$STAGE/wildkernel-patches/$2" tag
  if test ! -s "$file"; then
    tag=MISSING
  elif (cd "$SRC" && patch --dry-run --fuzz=0 -p1 --forward < "$file") \
        > "$REPORT/wildkernel-$(echo "$label" | tr / _).log" 2>&1; then
    tag=PATCH_APPLIES
  else
    tag=REQUIRES_PORT
  fi
  printf '%s\t%s\t%s\n' "$label" "$tag" "$relative" | tee -a "$OUT"
}
probe BBRv3 common/bbrv3/0001-net-tcp-backport-BBRv3-to-android14-6.1.patch
probe NTSync_compat common/ntsync/ntsync_compat_android14-6.1.patch
probe NTSync_base common/ntsync/ntsync_base.patch
probe Unicode_fix common/unicode_bypass_fix_6.1+.patch
probe memory_prefetch common/mem_opt_prefetch.patch
probe f2fs_reduce_congestion common/f2fs_reduce_congestion.patch
probe reduce_freeze_timeout common/reduce_freeze_timeout.patch
printf '%s\n' \
  'Note: dry-run applies means a patch can apply, NOT hardware compatibility or a validated feature.' \
  'NTSync patches have ordering dependencies and must be re-evaluated as a group.' \
  'DroidSpaces, Baseband Guard, NoMount and other WildKernels components need separate integration review.' \
  > "$REPORT/wildkernels-limitations.txt"
