#!/usr/bin/env bash
set -euo pipefail
SRC="$1"
STAGE="$2"
test -d "$SRC/arch/arm64" && test -d "$STAGE/report"
PIN=41ae18b35d20e0c6ac04116785a4a1089528ae94
WK="$STAGE/wildkernel-patches"
git clone --depth=1 https://github.com/WildKernels/kernel_patches.git "$WK"
git -C "$WK" fetch --depth=1 origin "$PIN"
git -C "$WK" checkout --detach "$PIN"
test "$(git -C "$WK" rev-parse HEAD)" = "$PIN"

# Apply only patches that passed individual --fuzz=0 dry-run against the
# pinned Vibranium+SUSFS source. Each step revalidates against its PREDECESSORS.
# These features remain hardware-unverified until the complete image boots.
apply_one() {
  label="$1"
  file="$WK/$2"
  test -s "$file" || { echo "Missing $label: $file" >&2; exit 5; }
  (cd "$SRC" && patch --dry-run --fuzz=0 -p1 --forward < "$file") \
    > "$STAGE/report/wildkernel-$label.log" 2>&1 || {
      cat "$STAGE/report/wildkernel-$label.log" >&2
      echo "$label conflicts after previous patches" >&2
      exit 6
    }
  (cd "$SRC" && patch --fuzz=0 -p1 --forward < "$file")
  printf 'APPLIED %s %s\n' "$label" "$2" >> "$STAGE/report/wildkernel-applied.txt"
}
apply_one NTSYNC_COMPAT common/ntsync/ntsync_compat_android14-6.1.patch
apply_one NTSYNC_BASE common/ntsync/ntsync_base.patch
apply_one UNICODE_FIX common/unicode_bypass_fix_6.1+.patch
apply_one ARM64_PREFETCH common/mem_opt_prefetch.patch
git -C "$SRC" diff --check
echo "Verified WildKernels source pin $PIN" >> "$STAGE/report/wildkernel-applied.txt"
