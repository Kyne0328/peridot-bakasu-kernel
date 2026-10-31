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

# Audio-boot isolation: no SUSFS kernel patch set; retain BakaSU UAPI6 only.
if test "${ENABLE_WILDKERNELS:-0}" = 1; then
  bash "$ROOT/08-tools/resukisu-addon/apply_wildkernels_v18.sh" "$SRC" "$STAGE"
fi
# Instrument ASoC missing component / deferred PCM link on this diagnostics-only branch.
# This changes diagnostic printk levels, not error codes, module interfaces or
# hardware controls. Always check exact source context before applying.
python3 - "$SRC/sound/soc/soc-core.c" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1])
source=p.read_text()
patterns=[
    ('dev_dbg(card->dev,\n\t\t\t\t"ASoC: codec component %s not found for link %s\\n",',
     'dev_err_ratelimited(card->dev,\n\t\t\t\t"ASoC_DIAG: codec component %s not found for link %s\\n",'),
    ('dev_dbg(card->dev,\n\t\t\t\t"ASoC: platform component %s not found for link %s\\n",',
     'dev_err_ratelimited(card->dev,\n\t\t\t\t"ASoC_DIAG: platform component %s not found for link %s\\n",'),
    ('dev_dbg(card->dev,\n\t\t\t\t"ASoC: cpu component %s not found for link %s\\n",',
     'dev_err_ratelimited(card->dev,\n\t\t\t\t"ASoC_DIAG: cpu component %s not found for link %s\\n",'),
    ('\t\tret = snd_soc_add_pcm_runtime(card, dai_link);\n\t\tif (ret < 0)\n\t\t\tgoto probe_end;',
     '\t\tret = snd_soc_add_pcm_runtime(card, dai_link);\n'
     '\t\tif (ret < 0) {\n'
     '\t\t\tdev_err_ratelimited(card->dev,\n'
     '\t\t\t\t"ASoC_DIAG: card %s DAI link %s failed: %d\\n",\n'
     '\t\t\t\tcard->name, dai_link->name, ret);\n'
     '\t\t\tgoto probe_end;\n\t\t}'),
    ('probe_end:\n\tif (ret < 0)\n\t\tsoc_cleanup_card_resources(card);',
     'probe_end:\n\tif (ret < 0) {\n'
     '\t\tdev_err_ratelimited(card->dev,\n'
     '\t\t\t"ASoC_DIAG: snd_soc_bind_card %s failed: %d\\n",\n'
     '\t\t\tcard->name, ret);\n'
     '\t\tsoc_cleanup_card_resources(card);\n\t}')
]
for before,after in patterns:
    if source.count(before)!=1 or after in source:
        raise SystemExit('ASoC diagnostic source context mismatch: '+repr(before[:95]))
    source=source.replace(before,after,1)
p.write_text(source)
print('ASoC diagnostic points installed:',len(patterns))
PY
git -C "$SRC" diff --check
cp "$CONFIG" "$OUT/.config"
"$SRC/scripts/config" --file "$OUT/.config" -e KSU -d KSU_SUSFS -d KSU_TRACEPOINT_HOOK -d KSU_MANUAL_HOOK -d LOCALVERSION_AUTO
if test "${ENABLE_WILDKERNELS:-0}" = 1; then "$SRC/scripts/config" --file "$OUT/.config" -e NTSYNC; fi
make -C "$SRC" O="$OUT" ARCH=arm64 LLVM=1 olddefconfig
make -C "$SRC" O="$OUT" ARCH=arm64 LLVM=1 -s kernelrelease > "$STAGE/report/kernelrelease.txt"
grep -qx "CONFIG_KSU=y" "$OUT/.config"
grep -qx "# CONFIG_KSU_SUSFS is not set" "$OUT/.config"
if test "${ENABLE_WILDKERNELS:-0}" = 1; then grep -qx "CONFIG_NTSYNC=y" "$OUT/.config"; fi
grep -qx "CONFIG_LTO_CLANG_FULL=y" "$OUT/.config"
grep -qx "CONFIG_MODVERSIONS=y" "$OUT/.config"
grep -qx "CONFIG_MODULE_SIG_PROTECT=y" "$OUT/.config"
grep -qx "$RELEASE" "$STAGE/report/kernelrelease.txt"
git -C "$SRC" diff --stat > "$STAGE/report/diffstat.txt"
printf 'preflight OK: V18 candidate + pinned BakaSU UAPI6 only + stock Full LTO\n'
BUILD_KERNEL="${BUILD_KERNEL:-0}"
if test "$BUILD_KERNEL" = 1; then
  # Pinned Vibranium source has a reproducible PKCS11 host-tool bug.
  # Fail closed if upstream code changed.
  python3 - "$SRC/certs/extract-cert.c" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]); source=p.read_text()
before='\t\tif (key_pass)\n\t\t\tERR(!ENGINE_ctrl_cmd_string(e, "PIN", key_pass, 0), "Set PKCS#11 PIN");'
after='#ifdef USE_PKCS11_ENGINE\n'+before+'\n#endif'
if source.count(before)!=1 or after in source:
    raise SystemExit("Unexpected certs/extract-cert.c; refusing PKCS11 patch")
p.write_text(source.replace(before, after, 1))
PY
  make -C "$SRC" O="$OUT" ARCH=arm64 LLVM=1 -j2 Image modules
  test -s "$OUT/arch/arm64/boot/Image" && test -s "$OUT/Module.symvers"
  sha256sum "$OUT/arch/arm64/boot/Image" "$OUT/Module.symvers" > "$STAGE/report/SHA256SUMS.txt"
fi
