"""Blank host HDD layout, without private captures or saved progress.

Retail partition-table layout from xbox_build_partition_table in the pinned
XboxRecomp src/kernel/kernel_path.c (MIT, copyright 2026 sp00nz).
No title-specific guest addresses. The runtime creates/formats devices 1..5.
"""
from pathlib import Path
import struct


def partition_table():
    sector = bytearray(512)
    sector[:16] = b'****PARTINFO****'
    parts = [('XBOX_PART_X', 0x400, 0x177000), ('XBOX_PART_Y', 0x177400, 0x177000),
             ('XBOX_PART_Z', 0x2ee400, 0x177000), ('XBOX_PART_C', 0x465400, 0xfa000),
             ('XBOX_PART_E', 0x55f400, 0x465400)]
    for i, (name, start, size) in enumerate(parts):
        offset = 48+i*32
        sector[offset:offset+16] = name.encode('ascii').ljust(16, b' ')
        struct.pack_into('<IIII', sector, offset+16, 0x80000000, start, size, 0)
    return bytes(sector)


def create_hdd(destination, title_id):
    destination = Path(destination)
    destination.mkdir()  # Must be new: never reset an existing HDD.
    (destination/'Partition0.img').write_bytes(bytes(0x800)+partition_table())
    for name in ('Cache', 'TitleData', 'UserData', 'SystemData',
                 'UDATA/%08X' % title_id, 'TDATA/%08X' % title_id):
        (destination/name).mkdir(parents=True, exist_ok=True)
