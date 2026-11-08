"""Exclusive same-volume directory publication on the supported macOS host."""
import ctypes
import os
import sys


def publish_directory(source, destination):
    # macOS sys/stdio.h: RENAME_EXCL also refuses an existing empty directory.
    if sys.platform != 'darwin':
        raise ValueError('Installation publication requires macOS')
    libc=ctypes.CDLL(None,use_errno=True)
    rename=libc.renamex_np
    rename.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.c_uint]
    rename.restype=ctypes.c_int
    if rename(os.fsencode(source),os.fsencode(destination),0x00000004):
        error=ctypes.get_errno()
        raise OSError(error,os.strerror(error),str(destination))
