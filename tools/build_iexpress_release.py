import hashlib
import shutil
import subprocess
import textwrap
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "极速批剪"
APP_VERSION = "1.0.7"
STAGE_DIR = ROOT / "build" / "installer_stage" / APP_NAME
UPDATER_EXE = ROOT / "kq-updates-module" / "universal-updater" / "dist" / "updater.exe"
RELEASE_ROOT = ROOT / "release" / APP_VERSION
INSTALLER_DIR = RELEASE_ROOT / "installer"
UPDATE_DIR = RELEASE_ROOT / "update"
WORK_DIR = ROOT / "build" / "iexpress_installer"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_stage() -> None:
    app_exe = STAGE_DIR / f"{APP_NAME}.exe"
    if not app_exe.exists():
        raise SystemExit(f"Missing stage executable: {app_exe}")
    if not UPDATER_EXE.exists():
        raise SystemExit(f"Missing updater executable: {UPDATER_EXE}")

    target = STAGE_DIR / "_internal" / "updater.exe"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(UPDATER_EXE, target)


def zip_directory(source_dir: Path, zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in source_dir.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(source_dir))


def build_update_package() -> Path:
    update_zip = UPDATE_DIR / f"极速批剪_v{APP_VERSION}_update.zip"
    zip_directory(STAGE_DIR, update_zip)
    (UPDATE_DIR / f"{update_zip.name}.sha256").write_text(
        sha256_file(update_zip),
        encoding="utf-8",
    )
    return update_zip


def write_installer_scripts(app_zip: Path) -> Path:
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    packaged_zip = WORK_DIR / "app.zip"
    shutil.copy2(app_zip, packaged_zip)

    install_ps1 = WORK_DIR / "install.ps1"
    install_ps1.write_text(
        textwrap.dedent(
            f"""
            $ErrorActionPreference = "Stop"
            $appName = "{APP_NAME}"
            $installDir = Join-Path $env:LocalAppData "Programs\\$appName"
            $sourceZip = Join-Path $PSScriptRoot "app.zip"

            New-Item -ItemType Directory -Force -Path $installDir | Out-Null
            Expand-Archive -LiteralPath $sourceZip -DestinationPath $installDir -Force

            $exePath = Join-Path $installDir "{APP_NAME}.exe"
            $shell = New-Object -ComObject WScript.Shell

            $programs = [Environment]::GetFolderPath("Programs")
            $programDir = Join-Path $programs $appName
            New-Item -ItemType Directory -Force -Path $programDir | Out-Null
            $shortcut = $shell.CreateShortcut((Join-Path $programDir "$appName.lnk"))
            $shortcut.TargetPath = $exePath
            $shortcut.WorkingDirectory = $installDir
            $shortcut.Save()

            $desktop = [Environment]::GetFolderPath("Desktop")
            $desktopShortcut = $shell.CreateShortcut((Join-Path $desktop "$appName.lnk"))
            $desktopShortcut.TargetPath = $exePath
            $desktopShortcut.WorkingDirectory = $installDir
            $desktopShortcut.Save()

            Start-Process -FilePath $exePath -WorkingDirectory $installDir
            """
        ).strip(),
        encoding="utf-8-sig",
    )

    install_cmd = WORK_DIR / "install.cmd"
    install_cmd.write_text(
        '@echo off\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"\r\n',
        encoding="utf-8",
    )
    return install_cmd


def build_iexpress(installer_cmd: Path) -> Path:
    INSTALLER_DIR.mkdir(parents=True, exist_ok=True)
    target = INSTALLER_DIR / f"极速批剪-installer-{APP_VERSION}.exe"
    sed_path = WORK_DIR / "installer.sed"
    icon_path = ROOT / "assets" / "icon.ico"

    sed_path.write_text(
        textwrap.dedent(
            f"""
            [Version]
            Class=IEXPRESS
            SEDVersion=3
            [Options]
            PackagePurpose=InstallApp
            ShowInstallProgramWindow=0
            HideExtractAnimation=1
            UseLongFileName=1
            InsideCompressed=0
            CAB_FixedSize=0
            CAB_ResvCodeSigning=0
            RebootMode=N
            InstallPrompt=
            DisplayLicense=
            FinishMessage=
            TargetName={target}
            FriendlyName={APP_NAME} {APP_VERSION}
            AppLaunched=install.cmd
            PostInstallCmd=<None>
            AdminQuietInstCmd=install.cmd
            UserQuietInstCmd=install.cmd
            SourceFiles=SourceFiles
            SetupIconFile={icon_path}
            [SourceFiles]
            SourceFiles0={WORK_DIR}
            [SourceFiles0]
            %FILE0%=
            %FILE1%=
            [Strings]
            FILE0=install.cmd
            FILE1=install.ps1
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    # app.zip is intentionally added after text generation to keep the SED readable.
    content = sed_path.read_text(encoding="utf-8")
    content = content.replace("%FILE1%=\n[Strings]", "%FILE1%=\n%FILE2%=\n[Strings]")
    content = content.replace("FILE1=install.ps1\n", "FILE1=install.ps1\nFILE2=app.zip\n")
    sed_path.write_text(content, encoding="utf-8")

    if target.exists():
        target.unlink()
    subprocess.check_call(["iexpress.exe", "/N", str(sed_path)])
    return target


def main() -> None:
    ensure_stage()
    update_zip = build_update_package()
    installer_cmd = write_installer_scripts(update_zip)
    installer = build_iexpress(installer_cmd)

    (INSTALLER_DIR / f"{installer.name}.sha256").write_text(
        sha256_file(installer),
        encoding="utf-8",
    )
    print(f"Installer: {installer}")
    print(f"Update: {update_zip}")


if __name__ == "__main__":
    main()
