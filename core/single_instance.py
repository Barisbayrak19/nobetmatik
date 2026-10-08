"""
Tekil Uygulama (Single Instance) Yöneticisi
Uygulamanın aynı anda birden fazla kez açılmasını engeller,
çalışan mevcut pencereyi ön plana getirir.
"""
import sys
import os
import atexit
from typing import Optional
from core.logger import logger
from core.config import APP_NAME

class SingleInstance:
    def __init__(self, mutex_name: str = "NobetMatik_App_SingleInstance_Mutex"):
        self.mutex_name = mutex_name
        self.mutex_handle = None
        self.already_running = False
        self._lock_file = None

        if sys.platform.startswith("win"):
            self._init_windows()
        else:
            self._init_posix()

    def _init_windows(self):
        import ctypes
        try:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            self.mutex_handle = kernel32.CreateMutexW(None, False, self.mutex_name)
            last_err = ctypes.get_last_error()
            if last_err == 183:  # ERROR_ALREADY_EXISTS
                self.already_running = True
            else:
                atexit.register(self.release)
        except Exception as e:
            logger.warning(f"Windows Named Mutex oluşturulamadı: {e}")
            self.already_running = False

    def _init_posix(self):
        import tempfile
        try:
            import fcntl
            lock_path = os.path.join(tempfile.gettempdir(), "nobetmatik.lock")
            self._lock_file = open(lock_path, "w")
            fcntl.lockf(self._lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            atexit.register(self.release)
        except (IOError, OSError, ImportError):
            self.already_running = True

    def bring_existing_window_to_front(self, title_keyword: str = APP_NAME) -> bool:
        """Windows üzerinde çalışan mevcut ana pencereyi bulup öne getirir."""
        if not sys.platform.startswith("win"):
            return False

        try:
            import ctypes
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            found_hwnds = []

            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

            def enum_cb(hwnd, lparam):
                if user32.IsWindowVisible(hwnd):
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buff = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buff, length + 1)
                        if title_keyword.lower() in buff.value.lower():
                            found_hwnds.append(hwnd)
                return True

            user32.EnumWindows(WNDENUMPROC(enum_cb), 0)

            if found_hwnds:
                hwnd = found_hwnds[0]
                user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                user32.SetForegroundWindow(hwnd)
                return True
        except Exception as e:
            logger.error(f"Pencere öne getirilirken hata: {e}")
        return False

    def release(self):
        """Mutex veya kilit dosyasını serbest bırakır."""
        if self.mutex_handle and sys.platform.startswith("win"):
            try:
                import ctypes
                kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
                kernel32.CloseHandle(self.mutex_handle)
            except Exception:
                pass
            self.mutex_handle = None

        if self._lock_file:
            try:
                self._lock_file.close()
            except Exception:
                pass
            self._lock_file = None
