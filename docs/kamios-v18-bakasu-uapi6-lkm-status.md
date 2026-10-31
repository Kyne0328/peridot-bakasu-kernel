# Kamios V1.1 (peridot) – BakaSU UAPI6 LKM status

## Installed device
- Android 17 Kamios v1.1, POCO F6 (peridot).
- Running: `6.1.176-Vibranium-V18+`, active slot B, original Kamios boot restored.
- Kernel config extracted from verified original boot: `configs/kamios-v1.1-20261027-vibranium-v18.config`.
- `CONFIG_MODULES=y`, `CONFIG_MODVERSIONS=y`, `CONFIG_MODULE_SIG=y`, `CONFIG_MODULE_SIG_FORCE=n`; no current KSU.
- No test module or boot partition change made in this work.

## Results
1. The full-kernel qualification workflow first failed on missing `key_pass` conditional in Vibranium's `certs/extract-cert.c`. The guard was fixed; the subsequent run reached `vmlinux.o` but received a runner shutdown signal and was canceled, not a normal compile error. See runs [41184319713](https://github.com/Kyne0328/peridot-bakasu-kernel/actions/runs/41184319713), [41184790687](https://github.com/Kyne0328/peridot-bakasu-kernel/actions/runs/41184790687).
2. BakaSU UAPI6 **direct generic GKI module** built successfully in [41187857975](https://github.com/Kyne0328/peridot-bakasu-kernel/actions/runs/41187857975). Its `kernelsu.ko` has `vermagic=6.1.166-dirty SMP preempt mod_unload modversions aarch64`, not the Kamios release. **DO NOT INSTALL.**
3. Vibranium-source **headers-only** external module build with generic DDK symbol baseline:
   - [41188069850](https://github.com/Kyne0328/peridot-bakasu-kernel/actions/runs/41188069850): missing generated SELinux `flask.h`; fixed using direct `genheaders` invocation, no full kernel build.
   - [41188339043](https://github.com/Kyne0328/peridot-bakasu-kernel/actions/runs/41188339043): attempted incorrect top-level make target for `flask.h`; fixed.
   - [41188577962](https://github.com/Kyne0328/peridot-bakasu-kernel/actions/runs/41188577962): SELinux headers now generated and BakaSU compilation reaches `modpost`, but borrowed GKI `Module.symvers` lacks ~63 required exports (10 printed + 53 suppressed), such as `seccomp_filter_release`, `alloc_uid`, `set_cred_ucounts`, `strncpy_from_user_nofault`, `__arm64_sys_close`, `path_umount`, `avc_has_perm`, `current_is_single_threaded`, `security_bounded_transition`, and `sidtab_destroy`.

## Gate to working module
- Obtain **actual Kamios/Vibranium V18 kernel build outputs** including `Module.symvers`, `vmlinux` and generated headers, or compile the identical source revision with the verified Kamios config/toolchain to generate the exact symbol database. The candidate source revision is `khargosxh18/android_kernel_xiaomi_sm8635@4b42813174f309838106763126c8d3c8f14e96b2`; identity to shipped V18 remains **unproven**.
- Check every imported `kernelsu.ko` symbol against the actual kernel export table and CRC; address legitimate missing exports with a compatible source rebuild, not `KBUILD_MODPOST_WARN=1`, fabricated CRCs or forced load.
- Verify exact `vermagic`, BakaSU UAPI6, SELinux and preinit/loader support and root behavior with recoverable backup before installation.
- The module-only approach cannot substitute a userspace `.so` for kernel `.ko`.
- No version-match string alone is sufficient to qualify the module; avoid flashing the generic artifact.
