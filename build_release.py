import argparse
import hashlib
import os
import re
import subprocess
import zipfile
from pathlib import Path
from typing import Optional

from utils.pe_signing import clear_stale_authenticode_directory


APP_INFO = Path("config/app_info.py")
ICON = Path("assets/icon.ico")
ENTRY = Path("launch_application.py")
UPDATER_EXE = Path("kq-updates-module/universal-updater/dist/updater.exe")
I18N_LOCALES = Path("ui/i18n/locales")


def read_app_info():
    content = APP_INFO.read_text(encoding="utf-8")
    name_match = re.search(r'^APP_NAME\s*=\s*"([^"]+)"', content, re.M)
    ver_match = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', content, re.M)
    if not name_match or not ver_match:
        raise RuntimeError("Failed to parse APP_NAME/APP_VERSION from config/app_info.py")
    return name_match.group(1), ver_match.group(1), content


def update_version(content: str, new_version: str) -> str:
    return re.sub(r'^APP_VERSION\s*=\s*"[^"]+"', f'APP_VERSION = "{new_version}"', content, flags=re.M)


def run(cmd):
    subprocess.check_call(cmd)


def build_portable(app_version: str, icon_abs: Path, assets_abs: Path, config_abs: Path,
                   locales_abs: Optional[Path], ffmpeg_abs: Optional[Path],
                   updater_abs: Optional[Path], portable_dir: Path, spec_dir: Path):
    print("[INFO] Building portable (onefile)...")
    portable_name = f"极速批剪-portable-{app_version}"
    portable_cmd = [
        os.sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean", "--windowed", "--onefile",
        "--name", portable_name,
        "--icon", str(icon_abs),
        "--add-data", f"{assets_abs}{os.pathsep}assets",
        "--add-data", f"{config_abs}{os.pathsep}config",
        "--distpath", str(portable_dir.resolve()),
        "--workpath", "build/portable_work",
        "--specpath", str(spec_dir),
        str(ENTRY),
    ]
    if locales_abs:
        portable_cmd.extend(["--add-data", f"{locales_abs}{os.pathsep}ui/i18n/locales"])
    if ffmpeg_abs:
        portable_cmd.extend(["--add-data", f"{ffmpeg_abs}{os.pathsep}ffmpeg"])
    if updater_abs:
        portable_cmd.extend(["--add-data", f"{updater_abs}{os.pathsep}."])
    run(portable_cmd)
    portable_exe = portable_dir / f"{portable_name}.exe"
    if clear_stale_authenticode_directory(portable_exe):
        print(f"[INFO] Cleared inherited Authenticode directory: {portable_exe}")


def build_installer_stage(app_name: str, icon_abs: Path, assets_abs: Path, config_abs: Path,
                          locales_abs: Optional[Path], ffmpeg_abs: Optional[Path],
                          updater_abs: Optional[Path], stage_dir: Path, spec_dir: Path):
    print("[INFO] Building installer stage (onedir)...")
    installer_cmd = [
        os.sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean", "--windowed", "--onedir",
        "--name", app_name,
        "--icon", str(icon_abs),
        "--add-data", f"{assets_abs}{os.pathsep}assets",
        "--add-data", f"{config_abs}{os.pathsep}config",
        "--distpath", str(stage_dir.resolve()),
        "--workpath", "build/installer_work",
        "--specpath", str(spec_dir),
        str(ENTRY),
    ]
    if locales_abs:
        installer_cmd.extend(["--add-data", f"{locales_abs}{os.pathsep}ui/i18n/locales"])
    if ffmpeg_abs:
        installer_cmd.extend(["--add-data", f"{ffmpeg_abs}{os.pathsep}ffmpeg"])
    if updater_abs:
        installer_cmd.extend(["--add-data", f"{updater_abs}{os.pathsep}."])
    run(installer_cmd)
    stage_exe = stage_dir / app_name / f"{app_name}.exe"
    if clear_stale_authenticode_directory(stage_exe):
        print(f"[INFO] Cleared inherited Authenticode directory: {stage_exe}")


def build_installer(app_name: str, app_version: str, icon_abs: Path, stage_dir: Path, installer_dir: Path):
    iss_file = Path("build/installer.iss")
    stage_dir_abs = (stage_dir / app_name).resolve()
    output_dir_abs = installer_dir.resolve()
    installer_filename = f"极速批剪-installer-{app_version}"
    iss = f"""#define AppName "{app_name}"
#define AppVersion "{app_version}"
#define AppExeName "{app_name}.exe"
#define StageDir "{stage_dir_abs}"

[Setup]
AppId={{{{B0E2F4B8-9D2C-4F3B-9A5A-000000000001}}}}
AppName={{#AppName}}
AppVersion={{#AppVersion}}
DefaultDirName={{autopf}}\\{{#AppName}}
DefaultGroupName={{#AppName}}
OutputDir={output_dir_abs}
OutputBaseFilename={installer_filename}
SetupIconFile={icon_abs}
Compression=lzma
SolidCompression=yes

[Files]
Source: "{{#StageDir}}\\*"; DestDir: "{{app}}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{{group}}\\{{#AppName}}"; Filename: "{{app}}\\{{#AppExeName}}"
Name: "{{commondesktop}}\\{{#AppName}}"; Filename: "{{app}}\\{{#AppExeName}}"

[Run]
Filename: "{{app}}\\{{#AppExeName}}"; Description: "Launch {{#AppName}}"; Flags: nowait postinstall skipifsilent
"""
    iss_file.write_text(iss, encoding="utf-8")

    inno_path = os.environ.get("INNO_SETUP_PATH") or r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    if not Path(inno_path).exists():
        raise SystemExit(f"Inno Setup compiler not found: {inno_path}")

    print("[INFO] Building installer with Inno Setup...")
    run([inno_path, str(iss_file)])


def create_update_package(stage_dir: Path, app_name: str, app_version: str, release_root: Path):
    """从 installer stage 目录创建全量更新包 (ZIP)"""
    source_dir = stage_dir / app_name
    if not source_dir.exists():
        print(f"[WARN] Stage dir not found: {source_dir}, skipping update package")
        return

    update_dir = release_root / "update"
    update_dir.mkdir(parents=True, exist_ok=True)
    zip_name = f"极速批剪_v{app_version}_update.zip"
    zip_path = update_dir / zip_name

    print(f"[INFO] Creating update package: {zip_path}")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(source_dir):
            for f in files:
                file_path = Path(root) / f
                arcname = file_path.relative_to(source_dir)
                zf.write(file_path, arcname)

    # 计算 SHA256
    sha256 = hashlib.sha256()
    with open(zip_path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            sha256.update(chunk)
    hash_val = sha256.hexdigest()
    size_mb = zip_path.stat().st_size / 1024 / 1024

    print(f"[INFO] Update package created:")
    print(f"  File: {zip_path}")
    print(f"  Size: {size_mb:.2f} MB")
    print(f"  SHA256: {hash_val}")

    # 写入 hash 文件方便上传时使用
    hash_file = update_dir / f"{zip_name}.sha256"
    hash_file.write_text(hash_val, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--set-version", dest="set_version", default="")
    parser.add_argument("--build-update", dest="build_update", action="store_true",
                        help="Build update package (ZIP) from installer stage")
    parser.add_argument(
        "--phase",
        choices=["all", "portable", "stage", "installer", "update"],
        default="all",
        help="Run a specific build phase. Default: all",
    )
    args = parser.parse_args()

    if not APP_INFO.exists():
        raise SystemExit(f"Missing {APP_INFO}")

    app_name, app_version, content = read_app_info()
    if args.set_version:
        content = update_version(content, args.set_version)
        APP_INFO.write_text(content, encoding="utf-8")
        app_name, app_version, _ = read_app_info()

    release_root = Path("release") / app_version
    portable_dir = release_root / "portable"
    installer_dir = release_root / "installer"
    stage_dir = Path("build/installer_stage")
    spec_dir = Path("build/spec")
    portable_dir.mkdir(parents=True, exist_ok=True)
    installer_dir.mkdir(parents=True, exist_ok=True)
    stage_dir.mkdir(parents=True, exist_ok=True)
    spec_dir.mkdir(parents=True, exist_ok=True)

    icon_abs = ICON.resolve()
    assets_abs = Path("assets").resolve()
    config_abs = Path("config").resolve()
    locales_abs = I18N_LOCALES.resolve() if I18N_LOCALES.exists() else None
    ffmpeg_dir = Path("ffmpeg")
    ffmpeg_abs = ffmpeg_dir.resolve() if ffmpeg_dir.exists() else None
    updater_abs = UPDATER_EXE.resolve() if UPDATER_EXE.exists() else None

    if not updater_abs:
        print("[WARN] updater.exe not found, update functionality will not be available in build")
    if not locales_abs:
        print(f"[WARN] i18n locales not found: {I18N_LOCALES}")

    phase = args.phase
    if args.build_update:
        phase = "update"

    # 只构建更新包（跳过编译）
    if phase == "update":
        create_update_package(stage_dir, app_name, app_version, release_root)
        return

    if phase in ("all", "portable"):
        build_portable(
            app_version=app_version,
            icon_abs=icon_abs,
            assets_abs=assets_abs,
            config_abs=config_abs,
            locales_abs=locales_abs,
            ffmpeg_abs=ffmpeg_abs,
            updater_abs=updater_abs,
            portable_dir=portable_dir,
            spec_dir=spec_dir,
        )

    if phase in ("all", "stage"):
        build_installer_stage(
            app_name=app_name,
            icon_abs=icon_abs,
            assets_abs=assets_abs,
            config_abs=config_abs,
            locales_abs=locales_abs,
            ffmpeg_abs=ffmpeg_abs,
            updater_abs=updater_abs,
            stage_dir=stage_dir,
            spec_dir=spec_dir,
        )

    if phase in ("all", "installer"):
        build_installer(
            app_name=app_name,
            app_version=app_version,
            icon_abs=icon_abs,
            stage_dir=stage_dir,
            installer_dir=installer_dir,
        )

    if phase == "all":
        # 自动创建更新包
        create_update_package(stage_dir, app_name, app_version, release_root)

    print("[DONE] Output:")
    print(f"  Portable: {portable_dir}")
    print(f"  Installer: {installer_dir}")
    print(f"  Update: {release_root / 'update'}")


if __name__ == "__main__":
    main()
