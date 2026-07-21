import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
APP_INFO = ROOT / "config" / "app_info.py"
BUILD_RELEASE = ROOT / "build_release.py"
UPDATER_EXE = ROOT / "kq-updates-module" / "universal-updater" / "dist" / "updater.exe"
SIGN_ROOT = ROOT / "build" / "sign_jobs"
SIGNED_DROP_ROOT = ROOT / "signed_drop"
SIGNABLE_EXTENSIONS = {".exe", ".dll", ".pyd", ".sys", ".ocx"}
IGNORED_DROP_FILENAMES = {".gitkeep", ".ds_store", "thumbs.db", "desktop.ini"}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_app_info():
    content = APP_INFO.read_text(encoding="utf-8")
    name_match = re.search(r'^APP_NAME\s*=\s*"([^"]+)"', content, re.M)
    ver_match = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', content, re.M)
    if not name_match or not ver_match:
        raise RuntimeError("Failed to parse APP_NAME/APP_VERSION from config/app_info.py")
    return name_match.group(1), ver_match.group(1)


def run(cmd):
    printable = " ".join([f'"{x}"' if " " in str(x) else str(x) for x in cmd])
    print(f"[CMD] {printable}")
    subprocess.check_call(cmd, cwd=str(ROOT))


def run_build_release(phase: str, set_version: str = ""):
    cmd = [sys.executable, str(BUILD_RELEASE), "--phase", phase]
    if set_version:
        cmd.extend(["--set-version", set_version])
    run(cmd)


def ensure_file(path: Path, desc: str):
    if not path.exists() or not path.is_file():
        raise SystemExit(f"[ERROR] Missing {desc}: {path}")


def relativize(path: Path) -> str:
    return os.path.relpath(path, ROOT).replace("\\", "/")


def abs_from_rel(rel_path: str) -> Path:
    return (ROOT / rel_path).resolve()


def version_root(version: str) -> Path:
    return SIGN_ROOT / version


def state_file(version: str) -> Path:
    return version_root(version) / "manifest.json"


def load_manifest(version: str):
    mf = state_file(version)
    if not mf.exists():
        return None
    return json.loads(mf.read_text(encoding="utf-8"))


def save_manifest(version: str, data: dict):
    root = version_root(version)
    root.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = now_iso()
    tmp = root / "manifest.json.tmp"
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(state_file(version))


def init_manifest(app_name: str, app_version: str):
    data = {
        "schema_version": 1,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "app_name": app_name,
        "app_version": app_version,
        "states": {
            "phase1_built": False,
            "phase1_applied": False,
            "phase2_built": False,
            "phase2_applied": False,
            "finalized": False,
        },
        "phases": {},
    }
    return data


def build_file_record(role: str, source_path: Path, pending_name: str):
    st = source_path.stat()
    return {
        "role": role,
        "source_relpath": relativize(source_path),
        "source_basename": source_path.name,
        "pending_name": pending_name,
        "pre_sha256": sha256_file(source_path),
        "pre_size": st.st_size,
        "pre_mtime": dt.datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
        "signed_sha256": "",
        "signed_size": 0,
        "signature_status": "",
        "applied_at": "",
    }


def stage_pending_name(stage_root: Path, source_path: Path) -> str:
    rel = source_path.relative_to(stage_root).as_posix()
    safe_rel = rel.replace("/", "__")
    return f"stage__{safe_rel}"


def collect_stage_sign_records(stage_root: Path):
    records = []
    seen_pending_names = set()
    for path in sorted(stage_root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SIGNABLE_EXTENSIONS:
            continue
        pending_name = stage_pending_name(stage_root, path)
        if pending_name in seen_pending_names:
            raise SystemExit(f"[ERROR] Duplicate pending file name generated: {pending_name}")
        seen_pending_names.add(pending_name)
        records.append(build_file_record("stage_binary", path, pending_name))
    return records


def build_phase_dirs(version: str, phase: str):
    base = version_root(version) / phase
    pending = base / "pending"
    signed = base / "signed"
    logs = base / "logs"
    pending.mkdir(parents=True, exist_ok=True)
    signed.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)
    return base, pending, signed, logs


def clean_dir_files(target_dir: Path):
    if not target_dir.exists():
        return
    for item in target_dir.iterdir():
        if item.is_file():
            item.unlink()


def ensure_signed_drop_dirs():
    phase1 = SIGNED_DROP_ROOT / "phase1"
    phase2 = SIGNED_DROP_ROOT / "phase2"
    phase1.mkdir(parents=True, exist_ok=True)
    phase2.mkdir(parents=True, exist_ok=True)
    return phase1, phase2


def resolve_signed_dir(value: str | None, phase: str) -> Path:
    phase1_dir, phase2_dir = ensure_signed_drop_dirs()
    default_map = {"phase1": phase1_dir, "phase2": phase2_dir}
    if value:
        target = Path(value).resolve()
        target.mkdir(parents=True, exist_ok=True)
        return target
    return default_map[phase]


def export_pending_files(pending_dir: Path, records):
    for rec in records:
        src = abs_from_rel(rec["source_relpath"])
        ensure_file(src, rec["role"])
        dst = pending_dir / rec["pending_name"]
        shutil.copy2(src, dst)


def get_authenticode_status(path: Path) -> str:
    ps = (
        "$sig = Get-AuthenticodeSignature -FilePath '{0}'; "
        "if ($null -eq $sig) {{ 'Unknown' }} else {{ $sig.Status.ToString() }}"
    ).format(str(path).replace("'", "''"))
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", ps],
            cwd=str(ROOT),
            text=True,
            stderr=subprocess.STDOUT,
        )
        value = out.strip().splitlines()
        return value[-1].strip() if value else "Unknown"
    except Exception:
        return "Unknown"


def apply_signed_files(
    phase_name: str,
    phase_data: dict,
    signed_dir: Path,
    allow_unsigned: bool,
    force: bool,
):
    records = phase_data["files"]
    signed_archive_dir = abs_from_rel(phase_data["signed_dir_rel"])
    signed_archive_dir.mkdir(parents=True, exist_ok=True)

    expected = {rec["pending_name"] for rec in records}
    actual_files = {
        p.name
        for p in signed_dir.iterdir()
        if p.is_file() and p.name.lower() not in IGNORED_DROP_FILENAMES
    }
    unexpected = sorted(actual_files - expected)
    if unexpected:
        raise SystemExit(
            "[ERROR] signed-dir contains unexpected files:\n  - " + "\n  - ".join(unexpected)
        )

    missing = []
    for rec in records:
        candidate = signed_dir / rec["pending_name"]
        if not candidate.exists():
            missing.append(rec["pending_name"])
    if missing:
        raise SystemExit(
            "[ERROR] Missing signed files:\n  - " + "\n  - ".join(missing)
        )

    for rec in records:
        if rec.get("applied_at") and not force:
            continue
        signed_input = signed_dir / rec["pending_name"]
        archive_target = signed_archive_dir / rec["pending_name"]
        shutil.copy2(signed_input, archive_target)

        sig_status = get_authenticode_status(archive_target)
        if (sig_status == "NotSigned") and (not allow_unsigned):
            raise SystemExit(
                f"[ERROR] {rec['pending_name']} 未检测到签名。"
                "如需本地模拟演练可加 --allow-unsigned-signed-input。"
            )

        source_abs = abs_from_rel(rec["source_relpath"])
        ensure_file(source_abs, f"apply target ({rec['role']})")
        shutil.copy2(archive_target, source_abs)

        rec["signed_sha256"] = sha256_file(archive_target)
        rec["signed_size"] = archive_target.stat().st_size
        rec["signature_status"] = sig_status
        rec["applied_at"] = now_iso()

    phase_data["applied_at"] = now_iso()
    print(f"[INFO] Applied signed files for {phase_name}.")


def cmd_phase1_build(args):
    app_name, app_version = read_app_info()
    pre_manifest = load_manifest(app_version)
    phase1_files = pre_manifest.get("phases", {}).get("phase1", {}).get("files", []) if pre_manifest else []
    has_stage_binary = any(item.get("role") == "stage_binary" for item in phase1_files)
    has_updater_source = any(item.get("role") == "updater_source_exe" for item in phase1_files)
    if (
        pre_manifest
        and pre_manifest.get("states", {}).get("phase1_built")
        and has_stage_binary
        and has_updater_source
        and (not args.force)
        and (not args.set_version)
    ):
        pending_rel = pre_manifest.get("phases", {}).get("phase1", {}).get("pending_dir_rel", "")
        print("[INFO] phase1 already built, skip. Use --force to rebuild.")
        if pending_rel:
            print(f"[INFO] Existing pending files: {abs_from_rel(pending_rel)}")
        return

    if args.set_version:
        run([sys.executable, str(BUILD_RELEASE), "--set-version", args.set_version, "--phase", "stage"])
        app_name, app_version = read_app_info()
    else:
        run_build_release("stage")

    stage_exe = ROOT / "build" / "installer_stage" / app_name / f"{app_name}.exe"
    ensure_file(stage_exe, "stage main exe")
    ensure_file(UPDATER_EXE, "updater.exe")

    base, pending, signed, _logs = build_phase_dirs(app_version, "phase1")
    clean_dir_files(pending)
    stage_root = ROOT / "build" / "installer_stage" / app_name
    stage_records = collect_stage_sign_records(stage_root)
    if not stage_records:
        raise SystemExit(
            "[ERROR] No signable binaries found in installer stage. "
            f"Expected extensions: {sorted(SIGNABLE_EXTENSIONS)}"
        )

    records = stage_records + [
        # 签名源 updater.exe，保证后续构建链路引用的是已签版本。
        build_file_record("updater_source_exe", UPDATER_EXE, f"updater_source__{UPDATER_EXE.name}"),
    ]
    export_pending_files(pending, records)

    data = load_manifest(app_version) or init_manifest(app_name, app_version)
    data["app_name"] = app_name
    data["app_version"] = app_version
    data["phases"]["phase1"] = {
        "phase_dir_rel": relativize(base),
        "pending_dir_rel": relativize(pending),
        "signed_dir_rel": relativize(signed),
        "built_at": now_iso(),
        "applied_at": "",
        "files": records,
    }
    data["states"]["phase1_built"] = True
    data["states"]["phase1_applied"] = False
    data["states"]["phase2_built"] = False
    data["states"]["phase2_applied"] = False
    data["states"]["finalized"] = False
    save_manifest(app_version, data)

    print("[DONE] phase1-build finished.")
    print(f"[INFO] Pending files: {pending}")
    print(f"[INFO] Phase1 sign files count: {len(records)}")
    phase1_drop, _phase2_drop = ensure_signed_drop_dirs()
    print(f"[INFO] 默认签名回传目录: {phase1_drop}")
    print("[NEXT] 复制 pending 文件到签名机工具输入目录，签名后再拷回。")
    print("[NEXT] 执行: python tools/distributed_sign_pipeline.py phase1-apply")


def cmd_phase1_apply(args):
    _app_name, app_version = read_app_info()
    data = load_manifest(app_version)
    if not data:
        raise SystemExit("[ERROR] No manifest found. run phase1-build first.")
    if not data["states"].get("phase1_built"):
        raise SystemExit("[ERROR] phase1 not built.")
    phase = data["phases"].get("phase1")
    if not phase:
        raise SystemExit("[ERROR] phase1 manifest missing.")

    signed_dir = resolve_signed_dir(args.signed_dir, phase="phase1")
    if not signed_dir.exists():
        raise SystemExit(f"[ERROR] signed-dir not found: {signed_dir}")

    apply_signed_files(
        phase_name="phase1",
        phase_data=phase,
        signed_dir=signed_dir,
        allow_unsigned=args.allow_unsigned_signed_input,
        force=args.force,
    )
    data["states"]["phase1_applied"] = True
    data["states"]["phase2_built"] = False
    data["states"]["phase2_applied"] = False
    data["states"]["finalized"] = False
    save_manifest(app_version, data)
    print("[DONE] phase1-apply finished.")
    print("[NEXT] 执行: python tools/distributed_sign_pipeline.py phase2-build")


def cmd_phase2_build(args):
    _app_name, app_version = read_app_info()
    data = load_manifest(app_version)
    if not data:
        raise SystemExit("[ERROR] No manifest found. run phase1-build first.")
    if not data["states"].get("phase1_applied"):
        raise SystemExit("[ERROR] phase1 signed files are not applied. run phase1-apply first.")
    if data.get("states", {}).get("phase2_built") and (not args.force):
        pending_rel = data.get("phases", {}).get("phase2", {}).get("pending_dir_rel", "")
        print("[INFO] phase2 already built, skip. Use --force to rebuild.")
        if pending_rel:
            print(f"[INFO] Existing pending files: {abs_from_rel(pending_rel)}")
        return

    run_build_release("installer")
    installer_exe = ROOT / "release" / app_version / "installer" / f"极速批剪-installer-{app_version}.exe"
    ensure_file(installer_exe, "installer exe")

    base, pending, signed, _logs = build_phase_dirs(app_version, "phase2")
    clean_dir_files(pending)
    records = [build_file_record("installer_exe", installer_exe, installer_exe.name)]
    export_pending_files(pending, records)

    data["phases"]["phase2"] = {
        "phase_dir_rel": relativize(base),
        "pending_dir_rel": relativize(pending),
        "signed_dir_rel": relativize(signed),
        "built_at": now_iso(),
        "applied_at": "",
        "files": records,
    }
    data["states"]["phase2_built"] = True
    data["states"]["phase2_applied"] = False
    data["states"]["finalized"] = False
    save_manifest(app_version, data)

    print("[DONE] phase2-build finished.")
    print(f"[INFO] Pending files: {pending}")
    _phase1_drop, phase2_drop = ensure_signed_drop_dirs()
    print(f"[INFO] 默认签名回传目录: {phase2_drop}")
    print("[NEXT] 执行: python tools/distributed_sign_pipeline.py phase2-apply")


def cmd_phase2_apply(args):
    _app_name, app_version = read_app_info()
    data = load_manifest(app_version)
    if not data:
        raise SystemExit("[ERROR] No manifest found. run phase1-build first.")
    if not data["states"].get("phase2_built"):
        raise SystemExit("[ERROR] phase2 not built.")
    phase = data["phases"].get("phase2")
    if not phase:
        raise SystemExit("[ERROR] phase2 manifest missing.")

    signed_dir = resolve_signed_dir(args.signed_dir, phase="phase2")
    if not signed_dir.exists():
        raise SystemExit(f"[ERROR] signed-dir not found: {signed_dir}")

    apply_signed_files(
        phase_name="phase2",
        phase_data=phase,
        signed_dir=signed_dir,
        allow_unsigned=args.allow_unsigned_signed_input,
        force=args.force,
    )
    data["states"]["phase2_applied"] = True
    data["states"]["finalized"] = False
    save_manifest(app_version, data)
    print("[DONE] phase2-apply finished.")
    print("[NEXT] 执行: python tools/distributed_sign_pipeline.py finalize")


def cmd_finalize(_args):
    _app_name, app_version = read_app_info()
    data = load_manifest(app_version)
    if not data:
        raise SystemExit("[ERROR] No manifest found. run phase1-build first.")
    if not data["states"].get("phase2_applied"):
        raise SystemExit("[ERROR] phase2 signed installer not applied. run phase2-apply first.")

    run_build_release("update")
    data["states"]["finalized"] = True
    save_manifest(app_version, data)
    print("[DONE] finalize finished. update package generated.")


def cmd_status(_args):
    _app_name, app_version = read_app_info()
    data = load_manifest(app_version)
    if not data:
        print("[INFO] No sign manifest for current app version.")
        return

    print(f"[INFO] App: {data['app_name']}  Version: {data['app_version']}")
    phase1_drop, phase2_drop = ensure_signed_drop_dirs()
    print("[INFO] Default signed-drop dirs:")
    print(f"  - phase1: {phase1_drop}")
    print(f"  - phase2: {phase2_drop}")
    print("[INFO] States:")
    for k, v in data.get("states", {}).items():
        print(f"  - {k}: {v}")

    for phase_name in ("phase1", "phase2"):
        phase = data.get("phases", {}).get(phase_name)
        if not phase:
            continue
        print(f"[INFO] {phase_name}:")
        print(f"  pending: {abs_from_rel(phase['pending_dir_rel'])}")
        print(f"  signed archive: {abs_from_rel(phase['signed_dir_rel'])}")
        for rec in phase.get("files", []):
            status = rec.get("signature_status") or "N/A"
            applied = "yes" if rec.get("applied_at") else "no"
            print(
                f"  - {rec['role']} -> {rec['pending_name']} "
                f"(signature={status}, applied={applied})"
            )


def build_parser():
    parser = argparse.ArgumentParser(
        description="Distributed signing pipeline for staged build/sign/release workflow."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p1b = sub.add_parser("phase1-build", help="Build stage artifacts and export pending sign files.")
    p1b.add_argument("--set-version", default="", help="Optional version override before phase1 build.")
    p1b.add_argument("--force", action="store_true", help="Rebuild and overwrite existing phase1 outputs.")
    p1b.set_defaults(func=cmd_phase1_build)

    p1a = sub.add_parser("phase1-apply", help="Apply signed files from signer machine back to source artifacts.")
    p1a.add_argument("--signed-dir", default="", help="Directory containing signed copies for phase1. Default: ./signed_drop/phase1")
    p1a.add_argument("--allow-unsigned-signed-input", action="store_true", help="Allow unsigned files for local dry-run.")
    p1a.add_argument("--force", action="store_true", help="Re-apply even if already applied.")
    p1a.set_defaults(func=cmd_phase1_apply)

    p2b = sub.add_parser("phase2-build", help="Build installer and export installer pending sign file.")
    p2b.add_argument("--force", action="store_true", help="Rebuild and overwrite existing phase2 outputs.")
    p2b.set_defaults(func=cmd_phase2_build)

    p2a = sub.add_parser("phase2-apply", help="Apply signed installer from signer machine.")
    p2a.add_argument("--signed-dir", default="", help="Directory containing signed copies for phase2. Default: ./signed_drop/phase2")
    p2a.add_argument("--allow-unsigned-signed-input", action="store_true", help="Allow unsigned files for local dry-run.")
    p2a.add_argument("--force", action="store_true", help="Re-apply even if already applied.")
    p2a.set_defaults(func=cmd_phase2_apply)

    fin = sub.add_parser("finalize", help="Generate update package after signed installer is applied.")
    fin.set_defaults(func=cmd_finalize)

    st = sub.add_parser("status", help="Show current distributed-sign pipeline status for current version.")
    st.set_defaults(func=cmd_status)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
