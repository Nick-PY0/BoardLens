"""Choose a board source from the active application, without activating it."""
import os,sys

def foreground_kind():
    try:
        if sys.platform=='darwin':
            from AppKit import NSWorkspace
            app=NSWorkspace.sharedWorkspace().frontmostApplication()
            if app.processIdentifier()==os.getpid():return 'self'
            bundle=app.bundleIdentifier() or ''
            if bundle in ('com.google.Chrome','com.google.Chrome.beta','com.microsoft.edgemac','com.brave.Browser'):return 'browser'
            if bundle=='com.apple.Chess':return 'native'
        elif sys.platform=='win32':
            import ctypes
            from ctypes import wintypes
            user=ctypes.windll.user32;user.GetForegroundWindow.restype=wintypes.HWND;user.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
            process=wintypes.DWORD();user.GetWindowThreadProcessId(user.GetForegroundWindow(),ctypes.byref(process))
            if process.value==os.getpid():return 'self'
            kernel=ctypes.windll.kernel32;kernel.OpenProcess.restype=wintypes.HANDLE;kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
            kernel.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)];kernel.CloseHandle.argtypes=[wintypes.HANDLE]
            handle=kernel.OpenProcess(0x1000,False,process.value)
            if handle:
                try:
                    length=wintypes.DWORD(32768);name=ctypes.create_unicode_buffer(length.value)
                    if kernel.QueryFullProcessImageNameW(handle,0,name,ctypes.byref(length)) and name.value.lower().endswith(('chrome.exe','msedge.exe','brave.exe')):return 'browser'
                finally:kernel.CloseHandle(handle)
    except Exception:pass
    return 'other'
