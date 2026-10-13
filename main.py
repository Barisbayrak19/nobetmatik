"""
Nöbet Yönetim Sistemi - Uygulama Giriş Noktası
Hata yakalama (exception hook) ve güvenli başlatıcı.
"""
import sys
import ctypes
import traceback
import tkinter as tk
from tkinter import messagebox
from core.logger import logger
from core.config import APP_NAME
from core.single_instance import SingleInstance
from ui.app import MainApp


def _enable_high_dpi():
    """Windows yüksek ölçekleme (%125 / %150) ekranlarında yazı bulanıklığını önler."""
    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


def global_exception_handler(exc_type, exc_value, exc_traceback):
    """
    Beklenmeyen hataları logs/app.log dosyasına kaydeder ve kullanıcı isterse Telegram'a iletir.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logger.critical(f"Kritik Beklenmeyen Hata:\n{err_msg}")

    try:
        send_report = messagebox.askyesno(
            "Beklenmeyen Bir Hata Oluştu",
            "Uygulamada beklenmeyen bir sorun ile karşılaşıldı.\n"
            "Detaylar sistem günlüğüne (logs/app.log) kaydedildi.\n\n"
            f"Hata Özeti: {exc_value}\n\n"
            "Bu hatanın çözülmesi için hata kaydını geliştiriciye otomatik iletmek ister misiniz?"
        )
        if send_report:
            from logic.feedback_service import FeedbackService, FeedbackData
            fb = FeedbackData(
                category="🐛 Otomatik Hata Raporu",
                school_name="Otomatik Sistem Raporu",
                sender_name="Sistem",
                contact="",
                subject=f"Hata: {str(exc_value)[:80]}",
                message=f"Otomatik yakalanan çalışma zamanı hatası:\n{exc_value}",
                include_logs=True,
                logs_snippet=err_msg[-800:]
            )
            FeedbackService.send_feedback(fb)
    except Exception:
        pass


def main():
    _enable_high_dpi()
    sys.excepthook = global_exception_handler

    # Tekil uygulama kontrolü (Single Instance): Birden fazla kez açılmayı engelle
    instance_guard = SingleInstance()
    if instance_guard.already_running:
        logger.info("Uygulama zaten çalışıyor. Mevcut pencere öne getiriliyor...")
        instance_guard.bring_existing_window_to_front()
        try:
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            messagebox.showinfo(
                "Uygulama Zaten Açık",
                f"{APP_NAME} zaten açık ve çalışır durumda.\n\n"
                "Açık olan pencere ekranınıza getirildi.",
                parent=root
            )
            root.destroy()
        except Exception:
            pass
        sys.exit(0)

    logger.info("Nöbet Yönetim Sistemi başlatılıyor...")
    try:
        app = MainApp()
        app.mainloop()
        logger.info("Uygulama normal şekilde kapatıldı.")
    except Exception as e:
        logger.critical(f"Uygulama çalışırken hata: {e}", exc_info=True)
        messagebox.showerror(
            "Kritik Hata",
            f"Uygulama başlatılırken bir hata oluştu:\n{e}\n\nAyrıntılar için logs/app.log dosyasını inceleyiniz."
        )
    finally:
        instance_guard.release()

if __name__ == "__main__":
    main()
