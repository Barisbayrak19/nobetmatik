"""
Evrensel Yazdırma ve Rapor Önizleme Merkezi (Print & Report Preview Center)
Tüm çıktılar (Haftalık Nöbet Çizelgesi, Boş Ders İkame Çizelgesi, Kişisel Fişler,
Ders Programları ve Devam Takip Raporları) için yüksek çözünürlüklü A4 sayfa önizleme ve yazdırma penceresi.
"""
import os
import shutil
import tempfile
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
from pathlib import Path
from typing import Optional, Dict, Any, List
from PIL import Image, ImageTk

try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

from ui.theme import (
    COLOR_BG, COLOR_CARD, COLOR_PRIMARY, COLOR_SECONDARY, COLOR_SUCCESS,
    COLOR_BORDER, COLOR_BORDER_STRONG, COLOR_TEXT_MAIN, COLOR_TEXT_MUTED,
    FONT_FAMILY, FONT_SIZE_BASE
)
from core.logger import logger

class PrintPreviewDialog(ctk.CTkToplevel):
    def __init__(
        self,
        parent: Any,
        title: str = "Baskı Önizleme ve Yazdırma",
        html_path: Optional[str] = None,
        pdf_path: Optional[str] = None,
        default_filename: str = "Rapor",
        raw_html: Optional[str] = None
    ):
        super().__init__(parent)
        self.title(f"🖨️ {title}")
        self.geometry("1100x820")
        self.minsize(880, 580)
        self.configure(fg_color=COLOR_BG)

        self.html_path = html_path
        self.pdf_path = pdf_path
        self.default_filename = default_filename
        self.raw_html = raw_html
        self.zoom_level = 100
        self.rendered_images: List[Any] = []

        # Eğer raw_html verildiyse ve html_path yoksa geçici HTML oluştur
        if self.raw_html and not self.html_path:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8")
            tmp.write(self.raw_html)
            tmp.close()
            self.html_path = tmp.name

        self.after(100, self.lift)
        self.bind("<Escape>", lambda e: self.destroy())

        self._build_ui()
        self._load_document_preview()

    def _build_ui(self):
        # 1. Üst Başlık Banner
        top_frame = ctk.CTkFrame(self, fg_color="#0F172A", corner_radius=0, height=52)
        top_frame.pack(fill="x", side="top")

        f_inner_top = ctk.CTkFrame(top_frame, fg_color="transparent")
        f_inner_top.pack(fill="x", padx=18, pady=8)

        lbl_head = ctk.CTkLabel(
            f_inner_top,
            text=f"🖨️ YAZDIRMA VE RAPOR ÖNİZLEME: {self.default_filename}",
            font=(FONT_FAMILY, 13, "bold"),
            text_color="#FFFFFF"
        )
        lbl_head.pack(side="left")

        lbl_desc = ctk.CTkLabel(
            f_inner_top,
            text="Yüksek çözünürlüklü A4 sayfa baskı önizlemesi. Yazdırmadan önce sayfa düzenini kontrol edin.",
            font=(FONT_FAMILY, 9),
            text_color="#94A3B8"
        )
        lbl_desc.pack(side="right")

        # 2. Araç Çubuğu (Yazdır, PDF Kaydet, HTML Kaydet, Tarayıcıda Aç, Zoom, Kapat)
        toolbar = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=8, border_width=1, border_color=COLOR_BORDER)
        toolbar.pack(fill="x", padx=16, pady=(10, 6), ipady=4)

        f_tools = ctk.CTkFrame(toolbar, fg_color="transparent")
        f_tools.pack(fill="x", padx=12, pady=6)

        # Doğrudan Yazdır Butonu
        btn_print = ctk.CTkButton(
            f_tools,
            text="🖨️ YAZDIR",
            font=(FONT_FAMILY, 11, "bold"),
            fg_color="#059669",
            hover_color="#047857",
            height=34,
            corner_radius=6,
            command=self.print_document
        )
        btn_print.pack(side="left", padx=(0, 10))

        # PDF Olarak Kaydet Butonu
        btn_save_pdf = ctk.CTkButton(
            f_tools,
            text="📑 PDF Olarak Kaydet",
            font=(FONT_FAMILY, 10, "bold"),
            fg_color="#334155",
            hover_color="#1E293B",
            height=34,
            corner_radius=6,
            command=self.save_as_pdf
        )
        btn_save_pdf.pack(side="left", padx=(0, 8))

        # HTML Olarak Kaydet
        btn_save_html = ctk.CTkButton(
            f_tools,
            text="🌐 HTML Olarak Kaydet",
            font=(FONT_FAMILY, 10, "bold"),
            fg_color="#475569",
            hover_color="#334155",
            height=34,
            corner_radius=6,
            command=self.save_as_html
        )
        btn_save_html.pack(side="left", padx=(0, 12))

        # Tarayıcıda Aç
        btn_browser = ctk.CTkButton(
            f_tools,
            text="↗️ Tarayıcıda Aç",
            font=(FONT_FAMILY, 10),
            fg_color="#E2E8F0",
            hover_color="#CBD5E1",
            text_color="#0F172A",
            height=34,
            corner_radius=6,
            command=self.open_in_browser
        )
        btn_browser.pack(side="left", padx=(0, 16))

        # Ayırıcı
        ttk.Separator(f_tools, orient="vertical").pack(side="left", fill="y", padx=8, pady=2)

        # Sayfa Bilgisi
        self.lbl_page_info = ctk.CTkLabel(
            f_tools,
            text="Sayfa yükleniyor...",
            font=(FONT_FAMILY, 10, "bold"),
            text_color=COLOR_TEXT_MAIN
        )
        self.lbl_page_info.pack(side="left", padx=(8, 12))

        # Ayırıcı
        ttk.Separator(f_tools, orient="vertical").pack(side="left", fill="y", padx=8, pady=2)

        # Zoom Kontrolleri
        ctk.CTkLabel(f_tools, text="Ölçek:", font=(FONT_FAMILY, 10, "bold"), text_color=COLOR_TEXT_MAIN).pack(side="left", padx=(8, 4))
        self.zoom_var = tk.StringVar(value="%100")
        zoom_cb = ttk.Combobox(
            f_tools,
            textvariable=self.zoom_var,
            values=["%75", "%90", "%100", "%120", "%150"],
            state="readonly",
            width=6,
            font=(FONT_FAMILY, 9)
        )
        zoom_cb.pack(side="left", ipady=2)
        zoom_cb.bind("<<ComboboxSelected>>", lambda e: self._on_zoom_changed())

        # Kapat Butonu
        btn_close = ctk.CTkButton(
            f_tools,
            text="Kapat",
            font=(FONT_FAMILY, 10, "bold"),
            fg_color="#94A3B8",
            hover_color="#64748B",
            height=34,
            width=80,
            corner_radius=6,
            command=self.destroy
        )
        btn_close.pack(side="right")

        # 3. Belge Önizleme Alanı (Koyu Zemin Üzerinde Gerçek Beyaz A4 Kağıtlar)
        self.preview_scroll = ctk.CTkScrollableFrame(self, fg_color="#334155", corner_radius=8)
        self.preview_scroll.pack(fill="both", expand=True, padx=16, pady=(4, 14))

    def _load_document_preview(self):
        """Belge sayfalarını yüksek çözünürlüklü A4 sayfalar olarak render eder."""
        for w in self.preview_scroll.winfo_children():
            w.destroy()
        self.rendered_images.clear()

        doc_target = None
        # 1. Öncelikli olarak PDF dosyasını aç (En yüksek kalite vector render)
        if self.pdf_path and os.path.exists(self.pdf_path):
            doc_target = self.pdf_path
        elif self.html_path and os.path.exists(self.html_path):
            doc_target = self.html_path

        if not doc_target or not fitz:
            lbl_err = ctk.CTkLabel(
                self.preview_scroll,
                text="⚠️ Önizleme belgesi bulunamadı veya PyMuPDF modülü eksik.",
                font=(FONT_FAMILY, 12, "bold"),
                text_color="#F8FAFC"
            )
            lbl_err.pack(pady=40)
            self.lbl_page_info.configure(text="Belge Yok")
            return

        try:
            doc = fitz.open(doc_target)
            total_pages = len(doc)
            self.lbl_page_info.configure(text=f"Toplam {total_pages} Sayfa")

            # Zoom seviyesine göre DPI hesapla (Standart ekran DPI: 105)
            scale = self.zoom_level / 100.0
            target_dpi = int(105 * scale)

            for page_idx in range(total_pages):
                page = doc[page_idx]
                pix = page.get_pixmap(dpi=target_dpi)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                photo = ImageTk.PhotoImage(img)
                self.rendered_images.append(photo)

                # Beyaz A4 Sayfa Kartı
                page_card = ctk.CTkFrame(
                    self.preview_scroll,
                    fg_color="#FFFFFF",
                    corner_radius=4,
                    border_width=1,
                    border_color="#94A3B8"
                )
                page_card.pack(pady=14, anchor="center")

                # Sayfa Numarası Rozeti (Birden fazla sayfa varsa)
                if total_pages > 1:
                    f_page_header = ctk.CTkFrame(page_card, fg_color="#F8FAFC", corner_radius=0, height=22)
                    f_page_header.pack(fill="x", side="top")
                    lbl_p = ctk.CTkLabel(
                        f_page_header,
                        text=f"Sayfa {page_idx + 1} / {total_pages}",
                        font=(FONT_FAMILY, 8, "bold"),
                        text_color="#64748B"
                    )
                    lbl_p.pack(side="right", padx=10, pady=2)

                lbl_page = tk.Label(page_card, image=photo, bg="#FFFFFF", bd=0, highlightthickness=0)
                lbl_page.pack(padx=10, pady=10)

            doc.close()

        except Exception as e:
            logger.error(f"Belge önizleme render hatası: {e}", exc_info=True)
            lbl_err = ctk.CTkLabel(
                self.preview_scroll,
                text=f"⚠️ Önizleme oluşturulurken hata meydana geldi:\n{e}",
                font=(FONT_FAMILY, 11),
                text_color="#FCA5A5"
            )
            lbl_err.pack(pady=40)
            self.lbl_page_info.configure(text="Hata")

    def _on_zoom_changed(self):
        val_str = self.zoom_var.get().replace("%", "")
        try:
            val = int(val_str)
            if val != self.zoom_level:
                self.zoom_level = val
                self._load_document_preview()
        except Exception:
            pass

    def print_document(self):
        """Belgeyi sistemin yazıcısına doğrudan yazdırma diyaloğuyla gönderir."""
        if self.html_path and os.path.exists(self.html_path):
            try:
                print_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8")
                with open(self.html_path, "r", encoding="utf-8") as f:
                    html_src = f.read()

                # window.print() otomatik tetikleyici enjekte et
                script_inject = """
                <script type="text/javascript">
                    window.onload = function() {
                        window.print();
                    };
                </script>
                """
                if "</body>" in html_src:
                    html_src = html_src.replace("</body>", f"{script_inject}</body>")
                else:
                    html_src += script_inject

                print_tmp.write(html_src)
                print_tmp.close()

                # Varsayılan tarayıcı üzerinden yazıcı iletişim kutusunu anında tetikle
                webbrowser.open(f"file://{os.path.abspath(print_tmp.name)}")
                return
            except Exception as e:
                logger.error(f"Yazdırma hatası: {e}")

        if self.pdf_path and os.path.exists(self.pdf_path) and os.name == "nt":
            try:
                os.startfile(self.pdf_path, "print")
                messagebox.showinfo("Yazıcıya Gönderildi", "Belge varsayılan sistem yazıcısına gönderildi.", parent=self)
                return
            except Exception as e:
                logger.error(f"PDF yazdırma hatası: {e}")

        # Yedek alternatif
        self.open_in_browser()

    def save_as_pdf(self):
        """Belgeyi PDF olarak kaydeder."""
        default_name = f"{self.default_filename}.pdf" if not self.default_filename.endswith(".pdf") else self.default_filename
        out_path = filedialog.asksaveasfilename(
            parent=self,
            title="PDF Olarak Kaydet",
            initialfile=default_name,
            defaultextension=".pdf",
            filetypes=[("PDF Dosyası", "*.pdf")]
        )
        if not out_path:
            return

        if self.pdf_path and os.path.exists(self.pdf_path):
            shutil.copyfile(self.pdf_path, out_path)
            messagebox.showinfo("Başarılı", f"PDF belgesi kaydedildi:\n{out_path}", parent=self)
        elif self.html_path and os.path.exists(self.html_path) and fitz:
            try:
                doc = fitz.open(self.html_path)
                pdf_bytes = doc.convert_to_pdf()
                with open(out_path, "wb") as f:
                    f.write(pdf_bytes)
                doc.close()
                messagebox.showinfo("Başarılı", f"PDF belgesi kaydedildi:\n{out_path}", parent=self)
            except Exception:
                messagebox.showinfo("Bilgi", "PDF doğrudan tarayıcı üzerinden 'Yazdır -> PDF Olarak Kaydet' ile de alınabilir.", parent=self)
                self.print_document()

    def save_as_html(self):
        """Belgeyi HTML olarak kaydeder."""
        default_name = f"{self.default_filename}.html" if not self.default_filename.endswith(".html") else self.default_filename
        out_path = filedialog.asksaveasfilename(
            parent=self,
            title="HTML Olarak Kaydet",
            initialfile=default_name,
            defaultextension=".html",
            filetypes=[("HTML Dosyası", "*.html")]
        )
        if not out_path:
            return

        if self.html_path and os.path.exists(self.html_path):
            shutil.copyfile(self.html_path, out_path)
            messagebox.showinfo("Başarılı", f"HTML sayfası kaydedildi:\n{out_path}", parent=self)

    def open_in_browser(self):
        """Belgeyi tam ekran web tarayıcısında açar."""
        if self.html_path and os.path.exists(self.html_path):
            webbrowser.open(f"file://{os.path.abspath(self.html_path)}")
        elif self.pdf_path and os.path.exists(self.pdf_path):
            webbrowser.open(f"file://{os.path.abspath(self.pdf_path)}")
        else:
            messagebox.showwarning("Uyarı", "Görüntülenecek dosya bulunamadı.", parent=self)
