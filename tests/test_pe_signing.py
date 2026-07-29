import struct

import pytest

from utils.pe_signing import PEFormatError, clear_stale_authenticode_directory


def _write_pe(path, *, certificate_offset=0, certificate_size=0, size=1024):
    data = bytearray(size)
    data[:2] = b"MZ"
    pe_offset = 0x80
    struct.pack_into("<I", data, 0x3C, pe_offset)
    data[pe_offset:pe_offset + 4] = b"PE\0\0"
    struct.pack_into("<H", data, pe_offset + 20, 0xF0)

    optional_offset = pe_offset + 24
    struct.pack_into("<H", data, optional_offset, 0x20B)
    struct.pack_into("<I", data, optional_offset + 108, 16)
    struct.pack_into(
        "<II",
        data,
        optional_offset + 112 + (4 * 8),
        certificate_offset,
        certificate_size,
    )
    path.write_bytes(data)


def _security_directory(path):
    data = path.read_bytes()
    return struct.unpack_from("<II", data, 0x80 + 24 + 112 + (4 * 8))


def test_clears_certificate_directory_left_before_appended_data(tmp_path):
    exe = tmp_path / "app.exe"
    _write_pe(exe, certificate_offset=400, certificate_size=16)

    assert clear_stale_authenticode_directory(exe) is True
    assert _security_directory(exe) == (0, 0)
    assert exe.stat().st_size == 1024


def test_preserves_certificate_table_at_end_of_file(tmp_path):
    exe = tmp_path / "signed.exe"
    _write_pe(exe, certificate_offset=1008, certificate_size=16)
    original = exe.read_bytes()

    assert clear_stale_authenticode_directory(exe) is False
    assert exe.read_bytes() == original


def test_unsigned_pe_is_unchanged(tmp_path):
    exe = tmp_path / "unsigned.exe"
    _write_pe(exe)
    original = exe.read_bytes()

    assert clear_stale_authenticode_directory(exe) is False
    assert exe.read_bytes() == original


def test_rejects_non_pe_input(tmp_path):
    invalid = tmp_path / "invalid.exe"
    invalid.write_bytes(b"not a PE")

    with pytest.raises(PEFormatError):
        clear_stale_authenticode_directory(invalid)
