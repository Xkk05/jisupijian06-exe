import struct
from pathlib import Path


class PEFormatError(ValueError):
    pass


def clear_stale_authenticode_directory(path: Path) -> bool:
    """Clear an inherited certificate-table pointer after data was appended."""
    data = bytearray(path.read_bytes())
    if len(data) < 0x40 or data[:2] != b"MZ":
        raise PEFormatError(f"Not a DOS executable: {path}")

    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    if pe_offset + 24 > len(data) or data[pe_offset:pe_offset + 4] != b"PE\0\0":
        raise PEFormatError(f"Not a PE executable: {path}")

    optional_size = struct.unpack_from("<H", data, pe_offset + 20)[0]
    optional_offset = pe_offset + 24
    optional_end = optional_offset + optional_size
    if optional_end > len(data):
        raise PEFormatError(f"Truncated PE optional header: {path}")

    magic = struct.unpack_from("<H", data, optional_offset)[0]
    if magic == 0x20B:
        directory_count_offset = optional_offset + 108
        directory_offset = optional_offset + 112
    elif magic == 0x10B:
        directory_count_offset = optional_offset + 92
        directory_offset = optional_offset + 96
    else:
        raise PEFormatError(f"Unsupported PE optional-header magic 0x{magic:04X}: {path}")

    if directory_count_offset + 4 > optional_end:
        raise PEFormatError(f"Missing PE data-directory count: {path}")
    if struct.unpack_from("<I", data, directory_count_offset)[0] <= 4:
        return False

    security_directory_offset = directory_offset + (4 * 8)
    if security_directory_offset + 8 > optional_end:
        raise PEFormatError(f"Missing PE security directory: {path}")

    certificate_offset, certificate_size = struct.unpack_from(
        "<II", data, security_directory_offset
    )
    if certificate_offset == 0 and certificate_size == 0:
        return False

    certificate_end = certificate_offset + certificate_size
    if certificate_offset > 0 and certificate_size > 0 and certificate_end == len(data):
        return False

    struct.pack_into("<II", data, security_directory_offset, 0, 0)
    path.write_bytes(data)
    return True
