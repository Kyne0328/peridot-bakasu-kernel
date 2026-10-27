#!/usr/bin/env python3
"""Peridot-only, ROM-version-agnostic AnyKernel3 packaging.

Removes ONLY previous-current-kernel SHA allowlist + ROM brand language.
Retains codename gate, active-slot boot-only, ramdisk and vbmeta protection.
No assertion of universal vendor-module compatibility or boot success.
Never overwrites previously signed originals.
"""
from __future__ import annotations
import copy,hashlib,json,pathlib,re,sys,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
CI=ROOT/"08-tools/installer-ri3/zip-signing"
sys.path.insert(0,str(CI))
from sign_zip import sign_generated_zip
from verify_zip import verify_zip
SOURCE=pathlib.Path("D:/hyperos4-peridot-kyneos-ri8-20261014/outputs/kernel-recovery")
OUTPUT=SOURCE/"peridot-rom-agnostic-20261027"
SIGNING=ROOT/"builder/work/installer-ri5-recoveryfix-20261004/signing-public.json"
WORK=ROOT/"builder/work/peridot-rom-agnostic-20261027"
STAMP="20261027"
MANIFEST="PERIDOT-ROM-AGNOSTIC-KERNEL-MANIFEST.json"
README="PERIDOT-ROM-AGNOSTIC-README.txt"
FILES=[
("Stable-Rooted-6.1.138",
 "BakaSU-UAPI6-WildKernels-RI8-Update-20261027.zip",
 "9f691186f1b552cdc91399f9eccdf14363f9fcef8be43024f2566d897856dc9e",
 "POCO-F6-Rooted-BakaSU-UAPI6-6.1.138-AnyPeridotROM-20261027.zip",
 "POCO F6 stable rooted Linux 6.1.138 UAPI6",False),
("DRMFix-Test1-6.1.176",
 "BakaSU-UAPI6-WildKernels-RI8-6.1.176-DRMFix-Test1-20261027.zip",
 "4b42e2ea7361d8c67dfea5c4ec9f35e9ffcb389290426f145406bdaf6ac3c4bc",
 "POCO-F6-DRMFix-Test1-BakaSU-UAPI6-6.1.176-AnyPeridotROM-20261027.zip",
 "POCO F6 EXPERIMENTAL rooted Linux 6.1.176 DRMFix Test1",True),
("Rollback-Rooted-6.1.138",
 "BakaSU-UAPI6-WildKernels-RI8-6.1.176-DRMFix-Test1-Rollback-Rooted-6.1.138.zip",
 "a62e55a933c56bf415b5355b21c879e56775c52515aad245d4f07431eaf77984",
 "POCO-F6-Rollback-Rooted-BakaSU-UAPI6-6.1.138-AnyPeridotROM-20261027.zip",
 "POCO F6 rollback to rooted Linux 6.1.138 UAPI6",False),
("Rollback-Stock-6.1.138",
 "BakaSU-UAPI6-WildKernels-RI8-6.1.176-DRMFix-Test1-Rollback-Stock-6.1.138.zip",
 "3c461da792954e1e749026b3bbf0c1410879f9f51f015790c5ba4dc2e5a10283",
 "POCO-F6-Rollback-Stock-6.1.138-AnyPeridotROM-20261027.zip",
 "POCO F6 rollback to stock Linux 6.1.138 (no root)",False)
]
def sha(p):
 with p.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def sha_bytes(x):return hashlib.sha256(x).hexdigest()
def require(ok,msg):
 if not ok:raise RuntimeError(msg)
def info(name,mode=0o644):
 i=zipfile.ZipInfo(name,date_time=(2026,10,27,0,0,0))
 i.create_system=3;i.external_attr=mode<<16
 i.compress_type=zipfile.ZIP_DEFLATED
 return i
def modified_installer(raw,title):
 s=raw.decode("utf-8")
 for token in ("do.devicecheck=1","device.name1=peridot","block=boot",
               "is_slot_device=auto","do.modules=0","do.systemless=0",
               "patch_vbmeta_flag=0","ramdisk_compression=auto",
               "no_magisk_check=1",". tools/ak3-core.sh",
               "split_boot","current_sha=","flash_boot"):
  require(token in s,"Source installer missing safety anchor: "+token)
 p=s.index(". tools/ak3-core.sh")+len(". tools/ak3-core.sh")
 s=s[:p]
 s=re.sub(r"^kernel\.string=.*$", "kernel.string="+title, s, count=1, flags=re.M)
 s=s.replace("## POCO F6 / peridot HyperOS 4 guarded ReSukiSU+SUSFS add-on",
             "## POCO F6 / peridot ROM-version-agnostic AnyKernel3")
 s+='''

ui_print " "
ui_print "POCO F6 (peridot) kernel installer"
ui_print "ROM/version SHA allowlist: DISABLED"
ui_print "This is NOT a guarantee of cross-ROM driver compatibility."
ui_print "Keep a current-slot boot backup and recovery available."

split_boot
flash_boot
ui_print "Active-slot boot kernel replaced; ramdisk and vbmeta flags preserved."
'''
 require("current_sha" not in s and "case " not in s,
         "Old kernel SHA allowlist not fully removed")
 require("do.devicecheck=1" in s and "device.name1=peridot" in s and
         "patch_vbmeta_flag=0" in s and "block=boot" in s,
         "Preserved safety invariants missing")
 require(s.count("split_boot")==1 and s.count("flash_boot")==1,
         "Unexpected number of boot write operations")
 return s.encode()
def main():
 require(SOURCE.is_dir(),"Missing owner RI8 recovery source folder")
 require(not OUTPUT.exists(),"Will not overwrite existing generic ZIP directory")
 require(not WORK.exists(),"Will not overwrite existing build scratch")
 signing=json.loads(SIGNING.read_text())
 cert=ROOT/signing["certificate_path"]
 key=ROOT/signing["private_key_path"]
 require(cert.is_file() and key.is_file(),"Development signing cert or key missing")
 WORK.mkdir(parents=True)
 OUTPUT.mkdir(parents=True)
 rows=[]
 for kind,source_name,source_sha,target_name,title,experimental in FILES:
  src=SOURCE/source_name
  require(src.is_file() and sha(src)==source_sha,"Pinned source ZIP changed: "+source_name)
  target=OUTPUT/target_name
  with zipfile.ZipFile(src) as srczip:
   require(srczip.testzip() is None,"Source ZIP member CRC invalid")
   members=srczip.infolist()
   old_manifests=[i.filename for i in members if "MANIFEST" in i.filename and i.filename.endswith(".json")]
   old_readmes=[i.filename for i in members if "README" in i.filename and i.filename.lower().endswith(".txt")]
   require(len(old_manifests)==1 and len(old_readmes)==1,"Unexpected input metadata layout")
   image=srczip.read("Image")
   old=json.loads(srczip.read(old_manifests[0]))
   require(old.get("bundled_image_sha256")==sha_bytes(image),
           "Input metadata/kernel mismatch")
   installer=modified_installer(srczip.read("anykernel.sh"),title)
   manifest={**old,
      "schema_version":3,"package_kind":kind,
      "release_class":"EXPERIMENTAL-unverified-on-ROM" if experimental else "cross-ROM-install-without-compatibility-guarantee",
      "original_package_sha256":source_sha,
      "device_codename_required":"peridot",
      "rom_build_restriction":False,
      "current_kernel_sha256_allowlist_enabled":False,
      "accepted_input_image_sha256":[],
      "requires_compatible_device_vendor_modules":True,
      "boot_slot_mode":"active_only",
      "ramdisk_preserved":True,"vbmeta_flags_patched":False,
      "device_boot_tested":False,
      "warning":"Any peridot ROM can ATTEMPT install; vendor/module KMI and boot compatibility are NOT guaranteed. Back up current boot. Stock kernel comes from POCO F6 global base."}
   readme=title+"""
Target: POCO F6 (peridot) only.
No existing kernel SHA allowlist and no Android ROM/build version restriction.
AnyKernel3 replaces only kernel Image in ACTIVE boot; ramdisk retained;
vendor_boot, super, userdata and vbmeta not touched.
IMPORTANT: Installer acceptance DOES NOT prove that this kernel works on
any POCO F6 ROM. Different ROMs may require different vendor/vendor_dlkm,
dtb, init/ramdisk, AVB or kernel interfaces. Possible bootloop/display errors.
Back up the CURRENT ACTIVE boot partition, keep recovery/fastboot available.
Do not flash on a different phone. No on-device boot validation for this
cross-ROM configuration has been performed.
"""
   if experimental:
    readme+="Known: original 6.1.176 flickered. This Theettam DRMFix Test1 has NOT been screen-tested; keep 6.1.138 rollback on hand.\\n"
   with zipfile.ZipFile(target,"w",allowZip64=True) as z:
    omitted={old_manifests[0],old_readmes[0],"anykernel.sh"}
    for entry in members:
     if entry.filename in omitted:continue
     z.writestr(copy.copy(entry),srczip.read(entry.filename))
    z.writestr(info("anykernel.sh",0o755),installer)
    z.writestr(info(MANIFEST),json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    z.writestr(info(README),readme)
  sign_dir=WORK/("signing-"+kind)
  sign_dir.mkdir()
  receipt=sign_generated_zip(target,cert,key,generated_root=OUTPUT,
    generated_parent=OUTPUT.parent,work_dir=sign_dir,
    expected_cert_sha256=signing["certificate_der_sha256"],
    reserve_bytes=4*1024**3)
  validity=verify_zip(target,cert,signing["certificate_der_sha256"])
  require(receipt["verified"] and validity["verified"],"Signed ZIP did not verify")
  with zipfile.ZipFile(target) as z:
   require(z.testzip() is None and len(z.namelist())==len(set(z.namelist())),
           "Output ZIP member CRC or duplicate entries")
   require(z.read("Image")==image,"Kernel payload changed")
   require(z.read("anykernel.sh")==installer,"Installer script changed")
   require(json.loads(z.read(MANIFEST))==manifest,"Manifest changed")
  row={"kind":kind,"name":target_name,"bytes":target.stat().st_size,
       "sha256":sha(target),"payload_sha256":sha_bytes(image),
       "preexisting_kernel_hash_check":False,"device_guard":"peridot",
       "zip_signature_verified":True,"tested_on_target_rom":False}
  rows.append(row)
  print("PACKAGE_VERIFIED",kind,row["sha256"],row["bytes"],flush=True)
 receipt={"status":"peridot-cross-rom-installers-packaged-not-device-tested","date":"2026-10-27",
   "source_pins":[a[2] for a in FILES],"device":"peridot","outputs":rows,
   "compatibility_note":"No ROM/build/SHA input restrictions; module/boot compatibility across ROMs unverified."}
 (OUTPUT/"ANYROM-DELIVERY.json").write_text(json.dumps(receipt,indent=2)+"\n")
 (OUTPUT/"SHA256SUMS.txt").write_text(
   "".join(x["sha256"]+"  "+x["name"]+"\n" for x in rows))
 (OUTPUT/"README-CROSS-ROM-IMPORTANT.txt").write_text(
   "POCO F6 PERIDOT ONLY. Cross-ROM installer: input SHA restrictions removed from normal AND rollback ZIPs.\n"
   "This does not make a kernel binary compatible with every ROM. Save active boot backup.\n"
   "Use rooted 6.1.138 as baseline/rollback; 6.1.176 DRMFix Test1 is untested on-device.\n"
   "A stock rollback uses the Global POCO F6 stock kernel, not a backup of arbitrary ROM's own boot kernel.\n"
   "To restore the exact ROM-original kernel, restore YOUR active boot image backup.\n")
 print("ALL_PACKAGES_SIGNED_AND_VERIFIED",len(rows),flush=True)
if __name__=="__main__":main()
