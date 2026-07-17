import ctypes
import subprocess
import sys


def copy_text(text):
    """Copy text through the host OS rather than the restricted palette web view."""
    if sys.platform == 'darwin':
        subprocess.run(['pbcopy'], input=text, text=True, check=True)
        return
    if sys.platform != 'win32':
        raise RuntimeError('Clipboard copying is only supported by Fusion on Windows and macOS.')

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalFree.argtypes = [ctypes.c_void_p]
    user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    user32.SetClipboardData.restype = ctypes.c_void_p
    if not user32.OpenClipboard(None):
        raise RuntimeError('Unable to open the system clipboard.')
    try:
        user32.EmptyClipboard()
        payload = (text + '\0').encode('utf-16-le')
        handle = kernel32.GlobalAlloc(0x0002, len(payload))  # GMEM_MOVEABLE
        if not handle:
            raise RuntimeError('Unable to allocate clipboard memory.')
        pointer = kernel32.GlobalLock(handle)
        if not pointer:
            kernel32.GlobalFree(handle)
            raise RuntimeError('Unable to access clipboard memory.')
        ctypes.memmove(pointer, payload, len(payload))
        kernel32.GlobalUnlock(handle)
        if not user32.SetClipboardData(13, handle):  # CF_UNICODETEXT
            kernel32.GlobalFree(handle)
            raise RuntimeError('Unable to write to the system clipboard.')
    finally:
        user32.CloseClipboard()
