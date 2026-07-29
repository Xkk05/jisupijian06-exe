# -*- coding: utf-8 -*-
"""发布构建脚本回归测试。"""


def test_pyinstaller_builds_include_i18n_locales(monkeypatch, tmp_path):
    import build_release

    commands = []
    monkeypatch.setattr(build_release, "run", commands.append)
    monkeypatch.setattr(
        build_release, "clear_stale_authenticode_directory", lambda _path: False
    )

    locales_abs = tmp_path / "ui" / "i18n" / "locales"
    locale_data_arg = f"{locales_abs}{build_release.os.pathsep}ui/i18n/locales"

    build_release.build_portable(
        app_version="1.0.9",
        icon_abs=tmp_path / "icon.ico",
        assets_abs=tmp_path / "assets",
        config_abs=tmp_path / "config",
        locales_abs=locales_abs,
        ffmpeg_abs=None,
        updater_abs=None,
        portable_dir=tmp_path / "portable",
        spec_dir=tmp_path / "spec",
    )
    build_release.build_installer_stage(
        app_name="极速批剪",
        icon_abs=tmp_path / "icon.ico",
        assets_abs=tmp_path / "assets",
        config_abs=tmp_path / "config",
        locales_abs=locales_abs,
        ffmpeg_abs=None,
        updater_abs=None,
        stage_dir=tmp_path / "stage",
        spec_dir=tmp_path / "spec",
    )

    assert len(commands) == 2
    assert all(locale_data_arg in command for command in commands)
