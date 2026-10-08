"""
Nöbet Yönetim Sistemi - Uygulama Giriş Noktası
Hata yakalama (exception hook) ve güvenli başlatıcı.
"""
import sys
import traceback
import tkinter as tk
from core.logger import logger
from core.config import APP_NAME
from core.single_instance import SingleInstance
from ui.app import MainApp

def global_exception_handler(exc_type, exc_value, exc_traceback):
    """
    Beklenmeyen hataları logs/app.log dosyasına kaydeder ve kullanıcıya nazik bir mesaj gösterir.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logger.critical(f"Kritik Beklenmeyen Hata:\n{err_msg}")

    try:
        messagebox.showerror(
            "Beklenmeyen Bir Hata Oluştu",
            "Uygulamada beklenmeyen bir sorun ile karşılaşıldı.\n"
            "Detaylar sistem günlüğüne (logs/app.log) kaydedildi.\n\n"
            f"Hata Özeti: {exc_value}"
        )
    except Exception:
        pass

def main():
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
