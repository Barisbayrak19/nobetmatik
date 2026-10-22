"""
Çıktı (Dışa Aktarım) Servisi
PDF, Excel (.xlsx), Word (.docx), HTML ve CSV formatlarını üretir.
En üste tarih aralığı ve müdür imza bloğunun üstüne günün tarihi eklenir.
"""
import os
import csv
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from core.models import SchoolInfo, Day, Location, Teacher, Assignment, AttendanceRecord, TeacherLesson
from core.database import Database
from core.logger import logger

PERIOD_TIMES = {
    1: "07:40 - 08:20",
    2: "08:30 - 09:10",
    3: "09:20 - 10:00",
    4: "10:10 - 10:50",
    5: "11:00 - 11:40",
    6: "11:50 - 12:30",
    7: "12:40 - 13:20"
}

# Font kayıtları (Türkçe karakter desteği için sistem Arial fontu)
_FONT_REGISTERED = False
def _register_pdf_fonts() -> bool:
    global _FONT_REGISTERED
    if _FONT_REGISTERED:
        return True
    font_path = Path("C:/Windows/Fonts/arial.ttf")
    font_bold_path = Path("C:/Windows/Fonts/arialbd.ttf")
    if font_path.exists():
        try:
            pdfmetrics.registerFont(TTFont("CustomArial", str(font_path)))
            if font_bold_path.exists():
                pdfmetrics.registerFont(TTFont("CustomArial-Bold", str(font_bold_path)))
            else:
                pdfmetrics.registerFont(TTFont("CustomArial-Bold", str(font_path)))
            from reportlab.pdfbase.pdfmetrics import registerFontFamily
            registerFontFamily("CustomArial", normal="CustomArial", bold="CustomArial-Bold", italic="CustomArial", boldItalic="CustomArial-Bold")
            _FONT_REGISTERED = True
            return True
        except Exception as e:
            logger.warning(f"Arial font yüklenirken hata: {e}")
    return False

class ExportService:
    def __init__(self, db: Database):
        self.db = db

    def get_period_times(self) -> Dict[int, str]:
        """Kayıtlı veya ayarlanmış ders saatlerini döndürür."""
        if hasattr(self.db, "get_period_times"):
            return self.db.get_period_times()
        return PERIOD_TIMES

    def _prepare_table_data(self, week_start: str) -> Dict[str, Any]:
        school = self.db.get_school_info()
        days = self.db.get_days()
        locations = self.db.get_locations(active_only=True)
        assignments = self.db.get_assignments_for_week(week_start)
        teachers = {t.id: t for t in self.db.get_teachers()}

        # Tarih aralığı ve günün tarihi hesaplama
        try:
            start_dt = datetime.date.fromisoformat(week_start)
            end_dt = start_dt + datetime.timedelta(days=4)
            date_range_str = f"{start_dt.strftime('%d.%m.%Y')} - {end_dt.strftime('%d.%m.%Y')}"
        except Exception:
            date_range_str = week_start

        today_str = datetime.date.today().strftime("%d.%m.%Y")

        # (day_id, loc_id) -> list of teacher names
        table_matrix: Dict[str, Dict[str, List[str]]] = {}
        for d in days:
            table_matrix[d.id] = {loc.id: [] for loc in locations}

        for a in assignments:
            if a.day_id in table_matrix and a.location_id in table_matrix[a.day_id]:
                if a.teacher_id and a.teacher_id in teachers:
                    t_name = teachers[a.teacher_id].name
                    table_matrix[a.day_id][a.location_id].append(t_name)

        return {
            "school": school,
            "days": days,
            "locations": locations,
            "matrix": table_matrix,
            "week_start": week_start,
            "date_range_str": date_range_str,
            "today_str": today_str
        }

    # 1. EXCEL (.xlsx)
    def export_excel(self, week_start: str, output_path: Path) -> Path:
        data = self._prepare_table_data(week_start)
        school = data["school"]
        days = data["days"]
        locations = data["locations"]
        matrix = data["matrix"]
        date_range_str = data["date_range_str"]
        today_str = data["today_str"]

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Haftalık Nöbet Çizelgesi"

        # Başlık Stilleri
        header_font = Font(name="Calibri", size=14, bold=True, color="1F497D")
        sub_font = Font(name="Calibri", size=11, bold=True)
        date_font = Font(name="Calibri", size=10, bold=True, color="2F5597")
        tbl_hdr_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        tbl_fill = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid")
        day_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
        cell_font = Font(name="Calibri", size=10)
        
        thin_border = Border(
            left=Side(style='thin', color='A6A6A6'),
            right=Side(style='thin', color='A6A6A6'),
            top=Side(style='thin', color='A6A6A6'),
            bottom=Side(style='thin', color='A6A6A6')
        )

        col_count = len(locations) + 1

        # Başlık satırları
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=col_count)
        ws.cell(row=1, column=1, value="T.C.").alignment = Alignment(horizontal="center")
        ws.cell(row=1, column=1).font = sub_font

        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=col_count)
        ws.cell(row=2, column=1, value=f"{school.district.upper()} KAYMAKAMLIĞI").alignment = Alignment(horizontal="center")
        ws.cell(row=2, column=1).font = sub_font

        ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=col_count)
        ws.cell(row=3, column=1, value=f"{school.name} Müdürlüğü").alignment = Alignment(horizontal="center")
        ws.cell(row=3, column=1).font = header_font

        ws.merge_cells(start_row=4, start_column=1, end_row=4, end_column=col_count)
        ws.cell(row=4, column=1, value=f"HAFTALIK NÖBET ÇİZELGESİ ({school.academic_year})").alignment = Alignment(horizontal="center")
        ws.cell(row=4, column=1).font = sub_font

        # En Üst Tarih Aralığı Satırı
        ws.merge_cells(start_row=5, start_column=1, end_row=5, end_column=col_count)
        ws.cell(row=5, column=1, value=f"Tarih Aralığı: {date_range_str}").alignment = Alignment(horizontal="center")
        ws.cell(row=5, column=1).font = date_font

        # Tablo Başlığı
        start_row = 7
        ws.cell(row=start_row, column=1, value="Günler / Yerler").font = tbl_hdr_font
        ws.cell(row=start_row, column=1).fill = tbl_fill
        ws.cell(row=start_row, column=1).alignment = Alignment(horizontal="center", vertical="center")
        ws.cell(row=start_row, column=1).border = thin_border

        for col_idx, loc in enumerate(locations, start=2):
            c = ws.cell(row=start_row, column=col_idx, value=loc.name)
            c.font = tbl_hdr_font
            c.fill = tbl_fill
            c.alignment = Alignment(horizontal="center", vertical="center")
            c.border = thin_border

        # Satırlar (Günler)
        current_row = start_row + 1
        for d in days:
            c = ws.cell(row=current_row, column=1, value=d.name)
            c.font = Font(name="Calibri", size=10, bold=True)
            c.fill = day_fill
            c.alignment = Alignment(horizontal="center", vertical="center")
            c.border = thin_border

            for col_idx, loc in enumerate(locations, start=2):
                teachers_list = matrix[d.id].get(loc.id, [])
                cell_value = "\n".join(teachers_list) if teachers_list else "-"
                cell = ws.cell(row=current_row, column=col_idx, value=cell_value)
                cell.font = cell_font
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                cell.border = thin_border
            current_row += 1

        # Nöbet Kuralları
        current_row += 1
        ws.cell(row=current_row, column=1, value="NÖBETÇİ ÖĞRETMENLERİN GÖREVLERİ").font = Font(name="Calibri", size=10, bold=True)
        current_row += 1
        for rule_line in school.duty_rules.split("\n"):
            if rule_line.strip():
                ws.cell(row=current_row, column=1, value=rule_line.strip()).font = Font(name="Calibri", size=9)
                current_row += 1

        # İmza Bloğu (Müdürün üstüne günün tarihi eklenir)
        current_row += 1
        ws.cell(row=current_row, column=col_count, value=today_str).alignment = Alignment(horizontal="center")
        ws.cell(row=current_row, column=col_count).font = Font(name="Calibri", size=10, italic=True)
        current_row += 1
        ws.cell(row=current_row, column=col_count, value=school.principal_name).alignment = Alignment(horizontal="center")
        ws.cell(row=current_row, column=col_count).font = Font(name="Calibri", size=10, bold=True)
        current_row += 1
        ws.cell(row=current_row, column=col_count, value="Müdür").alignment = Alignment(horizontal="center")
        ws.cell(row=current_row, column=col_count).font = Font(name="Calibri", size=10)

        # Sütun genişliklerini ayarla
        ws.column_dimensions["A"].width = 18
        for col_idx in range(2, col_count + 1):
            col_letter = get_column_letter(col_idx)
            ws.column_dimensions[col_letter].width = 24

        output_path.parent.mkdir(parents=True, exist_ok=True)
        wb.save(output_path)
        logger.info(f"Excel çıktısı oluşturuldu: {output_path}")
        return output_path

    # 2. WORD (.docx)
    def export_word(self, week_start: str, output_path: Path) -> Path:
        data = self._prepare_table_data(week_start)
        school = data["school"]
        days = data["days"]
        locations = data["locations"]
        matrix = data["matrix"]
        date_range_str = data["date_range_str"]
        today_str = data["today_str"]

        doc = Document()
        
        # Sayfa kenar boşlukları
        sections = doc.sections
        for section in sections:
            section.top_margin = Inches(0.6)
            section.bottom_margin = Inches(0.6)
            section.left_margin = Inches(0.6)
            section.right_margin = Inches(0.6)

        # Başlıklar
        p1 = doc.add_paragraph()
        p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r1 = p1.add_run(f"T.C.\n{school.district.upper()} KAYMAKAMLIĞI\n{school.name} Müdürlüğü\n")
        r1.bold = True
        r1.font.size = Pt(11)

        p2 = doc.add_paragraph()
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r2 = p2.add_run(f"HAFTALIK NÖBET ÇİZELGESİ ({school.academic_year})\n")
        r2.bold = True
        r2.font.size = Pt(12)

        # En Üste Tarih Aralığı
        p_dates = doc.add_paragraph()
        p_dates.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_dates = p_dates.add_run(f"Tarih Aralığı: {date_range_str}\n")
        r_dates.font.size = Pt(10)
        r_dates.font.color.rgb = RGBColor(0x2F, 0x55, 0x97)
        r_dates.bold = True

        # Tablo
        table = doc.add_table(rows=len(days) + 1, cols=len(locations) + 1)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.style = 'Table Grid'

        # Tablo Başlığı
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = "Nöbet Yerleri ->"
        hdr_cells[0].paragraphs[0].runs[0].font.bold = True
        hdr_cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

        for col_idx, loc in enumerate(locations, start=1):
            hdr_cells[col_idx].text = loc.name
            hdr_cells[col_idx].paragraphs[0].runs[0].font.bold = True
            hdr_cells[col_idx].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Tablo Verileri
        for row_idx, d in enumerate(days, start=1):
            row_cells = table.rows[row_idx].cells
            row_cells[0].text = d.name
            row_cells[0].paragraphs[0].runs[0].font.bold = True
            row_cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

            for col_idx, loc in enumerate(locations, start=1):
                teachers_list = matrix[d.id].get(loc.id, [])
                cell_text = "\n".join(teachers_list) if teachers_list else "-"
                row_cells[col_idx].text = cell_text
                row_cells[col_idx].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in row_cells[col_idx].paragraphs[0].runs:
                    run.font.size = Pt(9.5)

        # Nöbet Kuralları
        doc.add_paragraph()
        p_rules_title = doc.add_paragraph()
        r_title = p_rules_title.add_run("NÖBETÇİ ÖĞRETMENLERİN GÖREVLERİ")
        r_title.bold = True
        r_title.font.size = Pt(10)

        for rule in school.duty_rules.split("\n"):
            if rule.strip():
                p_rule = doc.add_paragraph(rule.strip())
                p_rule.paragraph_format.space_after = Pt(2)
                p_rule.paragraph_format.line_spacing = 1.15
                if p_rule.runs:
                    p_rule.runs[0].font.size = Pt(8.5)

        # İmza (Müdürün üstüne günün tarihi eklenir)
        p_sign = doc.add_paragraph()
        p_sign.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r_sign = p_sign.add_run(f"\n{today_str}\n{school.principal_name}\nMüdür")
        r_sign.bold = True
        r_sign.font.size = Pt(10)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(output_path)
        logger.info(f"Word çıktısı oluşturuldu: {output_path}")
        return output_path

    # 3. PDF (.pdf)
    def export_pdf(self, week_start: str, output_path: Path) -> Path:
        _register_pdf_fonts()
        data = self._prepare_table_data(week_start)
        school = data["school"]
        days = data["days"]
        locations = data["locations"]
        matrix = data["matrix"]
        date_range_str = data["date_range_str"]
        today_str = data["today_str"]

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=landscape(A4),
            rightMargin=30,
            leftMargin=30,
            topMargin=25,
            bottomMargin=25
        )

        styles = getSampleStyleSheet()
        font_family = "CustomArial" if _FONT_REGISTERED else "Helvetica"
        font_bold = "CustomArial-Bold" if _FONT_REGISTERED else "Helvetica-Bold"

        title_style = ParagraphStyle(
            name="PdfTitle",
            fontName=font_bold,
            fontSize=11,
            alignment=1, # Center
            leading=14
        )
        subtitle_style = ParagraphStyle(
            name="PdfSubTitle",
            fontName=font_bold,
            fontSize=12,
            alignment=1,
            leading=15
        )
        date_style = ParagraphStyle(
            name="PdfDateRange",
            fontName=font_bold,
            fontSize=9.5,
            alignment=1,
            textColor=colors.HexColor("#2F5597"),
            leading=13
        )
        cell_style = ParagraphStyle(
            name="PdfCell",
            fontName=font_family,
            fontSize=8.5,
            alignment=1,
            leading=10
        )
        hdr_cell_style = ParagraphStyle(
            name="PdfHdrCell",
            fontName=font_bold,
            fontSize=9,
            alignment=1,
            leading=11
        )
        rules_style = ParagraphStyle(
            name="PdfRules",
            fontName=font_family,
            fontSize=7.5,
            leading=9.5
        )
        rules_title_style = ParagraphStyle(
            name="PdfRulesTitle",
            fontName=font_bold,
            fontSize=8,
            leading=10
        )
        sign_style = ParagraphStyle(
            name="PdfSign",
            fontName=font_bold,
            fontSize=9,
            alignment=2, # Right
            leading=12
        )

        elements = []

        elements.append(Paragraph(f"T.C.<br/>{school.district.upper()} KAYMAKAMLIĞI<br/>{school.name} Müdürlüğü", title_style))
        elements.append(Spacer(1, 4))
        elements.append(Paragraph(f"HAFTALIK NÖBET ÇİZELGESİ ({school.academic_year})", subtitle_style))
        elements.append(Spacer(1, 2))
        # En üste tarih aralığı
        elements.append(Paragraph(f"Tarih Aralığı: {date_range_str}", date_style))
        elements.append(Spacer(1, 6))

        # Tablo
        table_data = []
        # Başlık satırı
        header_row = [Paragraph("<b>Nöbet Yerleri -></b>", hdr_cell_style)]
        for loc in locations:
            header_row.append(Paragraph(f"<b>{loc.name}</b>", hdr_cell_style))
        table_data.append(header_row)

        for d in days:
            row = [Paragraph(f"<b>{d.name}</b>", hdr_cell_style)]
            for loc in locations:
                t_list = matrix[d.id].get(loc.id, [])
                cell_text = "<br/>".join(t_list) if t_list else "-"
                row.append(Paragraph(cell_text, cell_style))
            table_data.append(row)

        # Tablo stil ve genişlikleri
        col_w = 780 / (len(locations) + 1)
        col_widths = [col_w] * (len(locations) + 1)
        pdf_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        pdf_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EAECEE")),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#7F8C8D")),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#2C3E50")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(pdf_table)
        elements.append(Spacer(1, 6))

        # Kurallar
        elements.append(Paragraph("<b>NÖBETÇİ ÖĞRETMENLERİN GÖREVLERİ</b>", rules_title_style))
        elements.append(Spacer(1, 2))
        for r_line in school.duty_rules.split("\n"):
            if r_line.strip():
                elements.append(Paragraph(r_line.strip(), rules_style))

        elements.append(Spacer(1, 4))
        # Müdürün üstüne günün tarihi
        elements.append(Paragraph(f"{today_str}<br/>{school.principal_name}<br/>Müdür", sign_style))

        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.build(elements)
        logger.info(f"PDF çıktısı oluşturuldu: {output_path}")
        return output_path

    # 4. HTML (.html)
    def export_html(self, week_start: str, output_path: Path) -> Path:
        data = self._prepare_table_data(week_start)
        school = data["school"]
        days = data["days"]
        locations = data["locations"]
        matrix = data["matrix"]
        date_range_str = data["date_range_str"]
        today_str = data["today_str"]

        html_rows = []
        for d in days:
            cells_html = [f"<td class='day-col'><b>{d.name}</b></td>"]
            for loc in locations:
                t_list = matrix[d.id].get(loc.id, [])
                t_str = "<br>".join(t_list) if t_list else "-"
                cells_html.append(f"<td>{t_str}</td>")
            html_rows.append(f"<tr>{''.join(cells_html)}</tr>")

        hdr_cells = "".join([f"<th>{loc.name}</th>" for loc in locations])
        rules_html = "".join([f"<li>{r.strip()}</li>" for r in school.duty_rules.split("\n") if r.strip()])

        html_content = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>Haftalık Nöbet Çizelgesi - {school.name}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            color: #333;
        }}
        .header {{
            text-align: center;
            margin-bottom: 15px;
        }}
        .header h3, .header h2 {{
            margin: 3px 0;
        }}
        .date-range {{
            font-size: 14px;
            color: #2F5597;
            font-weight: bold;
            margin-top: 5px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 15px;
        }}
        th, td {{
            border: 1px solid #444;
            padding: 8px 6px;
            text-align: center;
            font-size: 13px;
        }}
        th {{
            background-color: #2F5597;
            color: white;
            font-weight: bold;
        }}
        .day-col {{
            background-color: #D9E1F2;
            font-weight: bold;
            width: 120px;
        }}
        .rules {{
            font-size: 11px;
            line-height: 1.4;
            margin-top: 10px;
        }}
        .signature {{
            float: right;
            text-align: center;
            margin-top: 20px;
            font-weight: bold;
            font-size: 13px;
            line-height: 1.4;
        }}
        .signature .date {{
            font-weight: normal;
            margin-bottom: 4px;
        }}
        @media print {{
            body {{ margin: 0; }}
            @page {{ size: landscape; margin: 10mm; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h3>T.C.</h3>
        <h3>{school.district.upper()} KAYMAKAMLIĞI</h3>
        <h2>{school.name} Müdürlüğü</h2>
        <h3>HAFTALIK NÖBET ÇİZELGESİ ({school.academic_year})</h3>
        <div class="date-range">Tarih Aralığı: {date_range_str}</div>
    </div>

    <table>
        <thead>
            <tr>
                <th>Nöbet Yerleri -></th>
                {hdr_cells}
            </tr>
        </thead>
        <tbody>
            {''.join(html_rows)}
        </tbody>
    </table>

    <div class="rules">
        <h4>NÖBETÇİ ÖĞRETMENLERİN GÖREVLERİ</h4>
        <ol style="padding-left: 20px;">
            {rules_html}
        </ol>
    </div>

    <div class="signature">
        <div class="date">{today_str}</div>
        <div>{school.principal_name}</div>
        <div>Müdür</div>
    </div>
</body>
</html>
"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info(f"HTML çıktısı oluşturuldu: {output_path}")
        return output_path

    # 5. CSV (.csv)
    def export_csv(self, week_start: str, output_path: Path) -> Path:
        data = self._prepare_table_data(week_start)
        school = data["school"]
        days = data["days"]
        locations = data["locations"]
        matrix = data["matrix"]
        date_range_str = data["date_range_str"]
        today_str = data["today_str"]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, delimiter=";")
            # Başlık satırları
            writer.writerow(["T.C.", f"{school.district.upper()} KAYMAKAMLIĞI"])
            writer.writerow([school.name, "Müdürlüğü"])
            writer.writerow(["HAFTALIK NÖBET ÇİZELGESİ", school.academic_year])
            writer.writerow(["Tarih Aralığı:", date_range_str])
            writer.writerow([])

            # Tablo başlığı
            header = ["Gün"] + [loc.name for loc in locations]
            writer.writerow(header)

            for d in days:
                row = [d.name]
                for loc in locations:
                    t_list = matrix[d.id].get(loc.id, [])
                    row.append(", ".join(t_list) if t_list else "")
                writer.writerow(row)

            writer.writerow([])
            writer.writerow(["NÖBETÇİ ÖĞRETMENLERİN GÖREVLERİ"])
            for r in school.duty_rules.split("\n"):
                if r.strip():
                    writer.writerow([r.strip()])

            writer.writerow([])
            writer.writerow(["", "", "", today_str])
            writer.writerow(["", "", "", school.principal_name])
            writer.writerow(["", "", "", "Müdür"])

        logger.info(f"CSV çıktısı oluşturuldu: {output_path}")
        return output_path

    def _get_record_sub_info(self, record: Any, teachers_map: Dict[str, Any]) -> Dict[str, Any]:
        """Devamsızlık kaydına ait ikame ders görevlendirmelerini ve ek ders hak ediş durumunu inceler."""
        try:
            subs = self.db.get_substitutions(date_str=record.date_str, absent_teacher_id=record.teacher_id)
        except Exception:
            subs = []

        if not subs:
            return {"has_sub": False, "ek_ders_hours": 0, "supervision_hours": 0, "duty_names": [], "text": "-"}

        from logic.substitution_service import is_same_branch
        ek_ders_h = 0
        sup_h = 0
        duty_names = []
        absent_t = teachers_map.get(record.teacher_id)

        for s in subs:
            if not s.duty_teacher_id:
                continue
            duty_t = teachers_map.get(s.duty_teacher_id)
            d_name = duty_t.name if duty_t else "Öğretmen"
            if d_name not in duty_names:
                duty_names.append(d_name)

            is_branch_match = is_same_branch(duty_t.branch, absent_t.branch) if (duty_t and absent_t) else False
            if s.is_ek_ders or is_branch_match:
                ek_ders_h += 1
            else:
                sup_h += 1

        names_str = ", ".join(duty_names) if duty_names else "Görevli"
        if ek_ders_h > 0:
            text = f"⭐ {ek_ders_h} Saat Ek Ders ({names_str})"
        elif sup_h > 0:
            text = f"👁️ {sup_h} Saat Nezaret ({names_str})"
        else:
            text = "-"

        return {
            "has_sub": True,
            "ek_ders_hours": ek_ders_h,
            "supervision_hours": sup_h,
            "duty_names": duty_names,
            "text": text
        }

    # 6. PERSONEL DEVAM TAKİP EXCEL (.xlsx)
    def export_attendance_excel(self, records: Any, output_path: Any = None, title_or_path: Any = None, title: str = "PERSONEL DEVAM-DEVAMSIZLIK TAKİP ÇİZELGESİ") -> Path:
        if isinstance(records, int):  # export_attendance_excel(year, month, Path(output_path), [title])
            year = records
            month = int(output_path)
            output_path = Path(title_or_path)
            month_str = f"{year}-{month:02d}"
            records = self.db.get_attendance_records(month_str=month_str)
            title = f"PERSONEL DEVAM-DEVAMSIZLIK TAKİP ÇİZELGESİ ({month:02d}/{year})"
        else:
            output_path = Path(output_path)
            if isinstance(title_or_path, str):
                title = title_or_path

        school = self.db.get_school_info()
        today_str = datetime.date.today().strftime("%d.%m.%Y")
        teachers_list = self.db.get_teachers(active_only=False)
        teachers_map = {t.id: t for t in teachers_list}

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Devam Takip"

        header_font = Font(name="Calibri", size=13, bold=True, color="1F497D")
        sub_font = Font(name="Calibri", size=10, bold=True)
        tbl_hdr_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        tbl_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        cell_font = Font(name="Calibri", size=9.5)
        bold_cell_font = Font(name="Calibri", size=9.5, bold=True)
        fill_ek_ders = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")

        status_colors = {
            "Raporlu": PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid"),
            "İzinli": PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid"),
            "Sevkli": PatternFill(start_color="E0F2FE", end_color="E0F2FE", fill_type="solid"),
            "Görevli": PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid"),
            "Mazeretli": PatternFill(start_color="F3E8FF", end_color="F3E8FF", fill_type="solid"),
        }

        thin_border = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1')
        )

        col_count = 9
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=col_count)
        ws.cell(row=1, column=1, value="T.C.").alignment = Alignment(horizontal="center")
        ws.cell(row=1, column=1).font = sub_font

        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=col_count)
        ws.cell(row=2, column=1, value=f"{school.district.upper()} KAYMAKAMLIĞI / İLÇE MİLLÎ EĞİTİM MÜDÜRLÜĞÜ").alignment = Alignment(horizontal="center")
        ws.cell(row=2, column=1).font = sub_font

        ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=col_count)
        ws.cell(row=3, column=1, value=f"{school.name} Müdürlüğü").alignment = Alignment(horizontal="center")
        ws.cell(row=3, column=1).font = header_font

        ws.merge_cells(start_row=4, start_column=1, end_row=4, end_column=col_count)
        ws.cell(row=4, column=1, value=title).alignment = Alignment(horizontal="center")
        ws.cell(row=4, column=1).font = Font(name="Calibri", size=11, bold=True, color="2563EB")

        headers = ["Sıra No", "Tarih", "Öğretmen Adı Soyadı", "Branşı", "Devamsızlık Nedeni", "Ders Saatleri", "Girmediği Şubeler / Dersler", "İkame / Ek Ders Hak Edişi", "Açıklama"]
        hdr_row = 6
        for col_idx, h_text in enumerate(headers, start=1):
            c = ws.cell(row=hdr_row, column=col_idx, value=h_text)
            c.font = tbl_hdr_font
            c.fill = tbl_fill
            c.alignment = Alignment(horizontal="center", vertical="center")
            c.border = thin_border

        curr_row = hdr_row + 1
        for idx, r in enumerate(records, start=1):
            c_no = ws.cell(row=curr_row, column=1, value=idx)
            c_no.alignment = Alignment(horizontal="center")
            c_no.font = cell_font
            c_no.border = thin_border

            try:
                d_obj = datetime.date.fromisoformat(r.date_str)
                d_formatted = d_obj.strftime("%d.%m.%Y")
            except Exception:
                d_formatted = r.date_str

            c_date = ws.cell(row=curr_row, column=2, value=d_formatted)
            c_date.alignment = Alignment(horizontal="center")
            c_date.font = cell_font
            c_date.border = thin_border

            c_name = ws.cell(row=curr_row, column=3, value=r.teacher_name)
            c_name.alignment = Alignment(horizontal="left")
            c_name.font = bold_cell_font
            c_name.border = thin_border

            c_branch = ws.cell(row=curr_row, column=4, value=r.branch)
            c_branch.alignment = Alignment(horizontal="center")
            c_branch.font = cell_font
            c_branch.border = thin_border

            c_status = ws.cell(row=curr_row, column=5, value=r.status)
            c_status.alignment = Alignment(horizontal="center")
            c_status.font = bold_cell_font
            c_status.border = thin_border
            if r.status in status_colors:
                c_status.fill = status_colors[r.status]

            c_periods = ws.cell(row=curr_row, column=6, value=r.periods_missed)
            c_periods.alignment = Alignment(horizontal="center")
            c_periods.font = cell_font
            c_periods.border = thin_border

            c_lessons = ws.cell(row=curr_row, column=7, value=r.lessons_missed or "-")
            c_lessons.alignment = Alignment(horizontal="left")
            c_lessons.font = cell_font
            c_lessons.border = thin_border

            # İkame & Ek ders durumu
            sub_info = self._get_record_sub_info(r, teachers_map)
            c_sub = ws.cell(row=curr_row, column=8, value=sub_info["text"])
            c_sub.alignment = Alignment(horizontal="center")
            c_sub.border = thin_border
            if sub_info["ek_ders_hours"] > 0:
                c_sub.fill = fill_ek_ders
                c_sub.font = bold_cell_font
            else:
                c_sub.font = cell_font

            c_notes = ws.cell(row=curr_row, column=9, value=r.notes)
            c_notes.alignment = Alignment(horizontal="left")
            c_notes.font = cell_font
            c_notes.border = thin_border

            curr_row += 1

        # İmza Satırı
        curr_row += 2
        ws.cell(row=curr_row, column=8, value=today_str).alignment = Alignment(horizontal="center")
        ws.cell(row=curr_row, column=8).font = sub_font
        ws.cell(row=curr_row + 1, column=8, value=school.principal_name).alignment = Alignment(horizontal="center")
        ws.cell(row=curr_row + 1, column=8).font = header_font
        ws.cell(row=curr_row + 2, column=8, value="Okul Müdürü").alignment = Alignment(horizontal="center")
        ws.cell(row=curr_row + 2, column=8).font = sub_font

        # Sütun Genişlikleri
        widths = [8, 13, 25, 18, 18, 15, 25, 28, 26]
        for col_idx, width in enumerate(widths, start=1):
            col_letter = get_column_letter(col_idx)
            ws.column_dimensions[col_letter].width = width

        output_path.parent.mkdir(parents=True, exist_ok=True)
        wb.save(output_path)
        logger.info(f"Personel Devam Takip Excel çıktısı oluşturuldu: {output_path}")
        return output_path

    # 7. PERSONEL DEVAM TAKİP PDF (.pdf)
    def export_attendance_pdf(self, records: Any, output_path: Any = None, title_or_path: Any = None, title: str = "PERSONEL DEVAM TAKİP ÇİZELGESİ") -> Path:
        if isinstance(records, int):  # export_attendance_pdf(year, month, Path(output_path), [title])
            year = records
            month = int(output_path)
            output_path = Path(title_or_path)
            month_str = f"{year}-{month:02d}"
            records = self.db.get_attendance_records(month_str=month_str)
            title = f"PERSONEL DEVAM TAKİP ÇİZELGESİ ({month:02d}/{year})"
        else:
            output_path = Path(output_path)
            if isinstance(title_or_path, str):
                title = title_or_path

        _register_pdf_fonts()
        school = self.db.get_school_info()
        today_str = datetime.date.today().strftime("%d.%m.%Y")

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=24,
            leftMargin=24,
            topMargin=25,
            bottomMargin=25
        )

        font_family = "CustomArial" if _FONT_REGISTERED else "Helvetica"
        font_bold = "CustomArial-Bold" if _FONT_REGISTERED else "Helvetica-Bold"

        title_style = ParagraphStyle(
            name="AttPdfTitle",
            fontName=font_bold,
            fontSize=11,
            alignment=1,
            leading=14
        )
        subtitle_style = ParagraphStyle(
            name="AttPdfSubTitle",
            fontName=font_bold,
            fontSize=12,
            alignment=1,
            textColor=colors.HexColor("#1E3A8A"),
            leading=15
        )
        hdr_cell_style = ParagraphStyle(
            name="AttHdrCell",
            fontName=font_bold,
            fontSize=8,
            alignment=1,
            textColor=colors.white,
            leading=10
        )
        cell_style = ParagraphStyle(
            name="AttCell",
            fontName=font_family,
            fontSize=7.5,
            alignment=1,
            leading=9.5
        )
        cell_bold_style = ParagraphStyle(
            name="AttCellBold",
            fontName=font_bold,
            fontSize=7.5,
            alignment=1,
            leading=9.5
        )
        cell_left_style = ParagraphStyle(
            name="AttCellLeft",
            fontName=font_family,
            fontSize=7.5,
            alignment=0,
            leading=9.5
        )
        sign_style = ParagraphStyle(
            name="AttSign",
            fontName=font_bold,
            fontSize=8.5,
            alignment=1,
            leading=11
        )

        story = []
        story.append(Paragraph("T.C.", title_style))
        story.append(Paragraph(f"{school.district.upper()} KAYMAKAMLIĞI / İLÇE MİLLÎ EĞİTİM MÜDÜRLÜĞÜ", title_style))
        story.append(Paragraph(f"{school.name} Müdürlüğü", subtitle_style))
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 10))

        headers = ["No", "Tarih", "Öğretmen Adı Soyadı", "Branşı", "Durumu", "Ders Saatleri", "Girmediği Şubeler", "Açıklama / İkame"]
        table_data = [[Paragraph(h, hdr_cell_style) for h in headers]]
        teachers_list = self.db.get_teachers(active_only=False)
        teachers_map = {t.id: t for t in teachers_list}

        if not records:
            empty_row = [
                Paragraph("-", cell_style),
                Paragraph(today_str, cell_style),
                Paragraph("Bu döneme ait personel devamsızlık / sevk kaydı bulunmamaktadır.", cell_left_style),
                Paragraph("-", cell_style),
                Paragraph("-", cell_style),
                Paragraph("-", cell_style),
                Paragraph("-", cell_style),
                Paragraph("Kayıt yok", cell_left_style)
            ]
            table_data.append(empty_row)
        else:
            for idx, r in enumerate(records, start=1):
                try:
                    d_obj = datetime.date.fromisoformat(r.date_str)
                    d_formatted = d_obj.strftime("%d.%m.%Y")
                except Exception:
                    d_formatted = r.date_str

                sub_info = self._get_record_sub_info(r, teachers_map)
                if sub_info["has_sub"]:
                    color_tag = "#166534" if sub_info["ek_ders_hours"] > 0 else "#475569"
                    sub_badge = f"<font color='{color_tag}'><b>[{sub_info['text']}]</b></font>"
                    note_html = f"{r.notes}<br/>{sub_badge}" if r.notes else sub_badge
                else:
                    note_html = r.notes or "-"

                row = [
                    Paragraph(str(idx), cell_style),
                    Paragraph(d_formatted, cell_style),
                    Paragraph(r.teacher_name, cell_bold_style),
                    Paragraph(r.branch, cell_style),
                    Paragraph(r.status, cell_bold_style),
                    Paragraph(r.periods_missed, cell_style),
                    Paragraph(r.lessons_missed or "-", cell_left_style),
                    Paragraph(note_html, cell_left_style)
                ]
                table_data.append(row)

        col_widths = [20, 50, 95, 68, 50, 55, 92, 117]
        tbl = Table(table_data, colWidths=col_widths, repeatRows=1)

        t_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E293B")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]

        for i in range(1, len(table_data)):
            if i % 2 == 0:
                t_style.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor("#F8FAFC")))

        tbl.setStyle(TableStyle(t_style))
        story.append(tbl)
        story.append(Spacer(1, 20))

        # İmza Bloğu (Müdür Yardımcısı & Okul Müdürü)
        sign_table_data = [
            [Paragraph(f"{today_str}<br/>Düzenleyen<br/>Müdür Yardımcısı", sign_style),
             Paragraph(f"{today_str}<br/>{school.principal_name}<br/>Okul Müdürü", sign_style)]
        ]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.build(story)
        logger.info(f"Personel Devam Takip PDF çıktısı oluşturuldu: {output_path}")
        return output_path

    # =========================================================================
    # DERS PROGRAMI ÇIKTILARI (TIMETABLE EXPORTS)
    # =========================================================================

    def _get_timetable_days(self) -> List[str]:
        return ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]

    # 8. ÖĞRETMEN HAFTALIK DERS PROGRAMI PDF (.pdf)
    def export_teacher_timetable_pdf(self, output_path: Path, teacher_id: Optional[str] = None) -> Path:
        _register_pdf_fonts()
        school = self.db.get_school_info()
        today_str = datetime.date.today().strftime("%d.%m.%Y")
        days = self._get_timetable_days()

        teachers_list: List[Teacher] = []
        if teacher_id:
            t = self.db.get_teacher(teacher_id)
            if t:
                teachers_list.append(t)
        else:
            teachers_list = self.db.get_teachers(active_only=True)

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=25,
            leftMargin=25,
            topMargin=25,
            bottomMargin=25
        )

        font_family = "CustomArial" if _FONT_REGISTERED else "Helvetica"
        font_bold = "CustomArial-Bold" if _FONT_REGISTERED else "Helvetica-Bold"

        title_style = ParagraphStyle("TTPdfTitle", fontName=font_bold, fontSize=11, alignment=1, leading=14)
        subtitle_style = ParagraphStyle("TTPdfSubTitle", fontName=font_bold, fontSize=11.5, alignment=1, textColor=colors.HexColor("#1E3A8A"), leading=14)
        doc_title_style = ParagraphStyle("TTDocTitle", fontName=font_bold, fontSize=11, alignment=1, textColor=colors.HexColor("#2563EB"), leading=14)
        info_style = ParagraphStyle("TTInfo", fontName=font_bold, fontSize=9.5, alignment=0, leading=12)
        info_right_style = ParagraphStyle("TTInfoRight", fontName=font_bold, fontSize=9.5, alignment=2, leading=12)
        hdr_style = ParagraphStyle("TTHdr", fontName=font_bold, fontSize=8, alignment=1, textColor=colors.white, leading=10)
        day_hdr_style = ParagraphStyle("TTDayHdr", fontName=font_bold, fontSize=8.5, alignment=1, textColor=colors.HexColor("#0F172A"), leading=10)
        cell_class_style = ParagraphStyle("TTCellClass", fontName=font_bold, fontSize=8.5, alignment=1, textColor=colors.HexColor("#1E3A8A"), leading=10)
        cell_subj_style = ParagraphStyle("TTCellSubj", fontName=font_family, fontSize=7, alignment=1, textColor=colors.HexColor("#475569"), leading=9)
        free_style = ParagraphStyle("TTCellFree", fontName=font_family, fontSize=7.5, alignment=1, textColor=colors.HexColor("#94A3B8"), leading=9)
        sign_style = ParagraphStyle("TTSign", fontName=font_bold, fontSize=9, alignment=1, leading=12)

        story = []

        for idx, t in enumerate(teachers_list):
            if idx > 0:
                story.append(PageBreak())

            lessons = self.db.get_teacher_lessons(t.id)
            # Map (day_name, period) -> TeacherLesson
            l_map: Dict[Tuple[str, int], TeacherLesson] = {(l.day_name, l.period): l for l in lessons}
            total_active_hours = sum(1 for l in lessons if not l.is_free and (l.class_name or l.subject_code))

            # Header
            story.append(Paragraph("T.C.", title_style))
            story.append(Paragraph(f"{school.district.upper()} KAYMAKAMLIĞI", title_style))
            story.append(Paragraph(f"{school.name} Müdürlüğü", subtitle_style))
            story.append(Spacer(1, 2))
            story.append(Paragraph(f"ÖĞRETMEN HAFTALIK DERS PROGRAMI ({school.academic_year})", doc_title_style))
            story.append(Spacer(1, 6))

            # Öğretmen Bilgi Satırı
            info_data = [
                [Paragraph(f"<b>Öğretmen:</b> {t.name} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Branş:</b> {t.branch or '-'}", info_style),
                 Paragraph(f"<b>Toplam Ders:</b> {total_active_hours} Saat &nbsp;&nbsp;|&nbsp;&nbsp; <b>Tarih:</b> {today_str}", info_right_style)]
            ]
            t_info = Table(info_data, colWidths=[360, 185])
            t_info.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(t_info)
            story.append(Spacer(1, 4))

            # Tablo: Günler (Sütunlar) x Saatler (Satırlar)
            daily_periods = school.daily_periods if (school and school.daily_periods) else 7
            period_times = self.get_period_times()
            col_widths = [75] + [94] * 5
            headers = [Paragraph("Ders Saati", hdr_style)] + [Paragraph(d, hdr_style) for d in days]
            table_data = [headers]

            for p in range(1, daily_periods + 1):
                time_range = period_times.get(p, "")
                row = [Paragraph(f"<b>{p}. Ders</b><br/><font size=6.5 color='#64748B'>{time_range}</font>", day_hdr_style)]
                for d in days:
                    item = l_map.get((d, p))
                    if item and not item.is_free and (item.class_name or item.subject_code):
                        c_text = item.class_name
                        s_text = item.subject_code
                        cell_p = [
                            Paragraph(c_text, cell_class_style),
                            Paragraph(s_text, cell_subj_style)
                        ]
                    else:
                        cell_p = [Paragraph("—", free_style)]
                    row.append(cell_p)
                table_data.append(row)

            tbl = Table(table_data, colWidths=col_widths)
            row_pad = 4 if daily_periods <= 7 else (3 if daily_periods <= 8 else 2)
            tbl_style = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E293B")),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ('TOPPADDING', (0, 0), (-1, -1), row_pad),
                ('BOTTOMPADDING', (0, 0), (-1, -1), row_pad),
            ]
            for r in range(1, daily_periods + 1):
                # Birinci sütun zemin rengi
                tbl_style.append(('BACKGROUND', (0, r), (0, r), colors.HexColor("#F1F5F9")))
                if r % 2 == 0:
                    tbl_style.append(('BACKGROUND', (1, r), (-1, r), colors.HexColor("#F8FAFC")))
            tbl.setStyle(TableStyle(tbl_style))
            story.append(tbl)
            story.append(Spacer(1, 14))

            # Bilgilendirme ve İmza Bloğu
            notes_p = Paragraph(
                "<font size=7 color='#64748B'>Yukarıdaki ders programı ders saatleri çerçevesinde uygulanacaktır. İlgili öğretmen programa uymakla yükümlüdür.</font>",
                ParagraphStyle("TTNote", fontName=font_family, fontSize=7, leading=9)
            )
            story.append(notes_p)
            story.append(Spacer(1, 14))

            sign_data = [
                [Paragraph("Teslim Alan<br/>İlgili Öğretmen", sign_style),
                 Paragraph(f"{today_str}<br/>{school.principal_name}<br/>Okul Müdürü", sign_style)]
            ]
            sign_tbl = Table(sign_data, colWidths=[270, 275])
            sign_tbl.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(sign_tbl)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.build(story)
        logger.info(f"Öğretmen ders programı PDF oluşturuldu: {output_path}")
        return output_path

    # 9. ÖĞRETMEN HAFTALIK DERS PROGRAMI EXCEL (.xlsx)
    def export_teacher_timetable_excel(self, output_path: Path, teacher_id: Optional[str] = None) -> Path:
        school = self.db.get_school_info()
        days = self._get_timetable_days()

        teachers_list: List[Teacher] = []
        if teacher_id:
            t = self.db.get_teacher(teacher_id)
            if t:
                teachers_list.append(t)
        else:
            teachers_list = self.db.get_teachers(active_only=True)

        wb = openpyxl.Workbook()
        ws_summary = wb.active
        ws_summary.title = "Öğretmenler Ders Yükü"

        # Stiller
        hdr_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        hdr_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        sub_fill = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
        sub_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        gray_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
        zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        cell_font = Font(name="Calibri", size=9.5)
        bold_font = Font(name="Calibri", size=9.5, bold=True)
        title_font = Font(name="Calibri", size=12, bold=True, color="1E3A8A")
        thin_border = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1')
        )
        align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)

        # 1. Özet Sayfası
        ws_summary.merge_cells("A1:E1")
        ws_summary["A1"] = f"{school.name} - ÖĞRETMEN HAFTALIK DERS YÜKÜ LİSTESİ ({school.academic_year})"
        ws_summary["A1"].font = title_font
        ws_summary["A1"].alignment = align_center

        sum_headers = ["Sıra", "Öğretmen Adı Soyadı", "Branşı", "Haftalık Ders Saati", "Boş Saat"]
        ws_summary.append([])
        ws_summary.append(sum_headers)
        for col_i in range(1, 6):
            cell = ws_summary.cell(row=3, column=col_i)
            cell.fill = hdr_fill
            cell.font = hdr_font
            cell.alignment = align_center
            cell.border = thin_border

        daily_periods = school.daily_periods if (school and school.daily_periods) else 7
        period_times = self.get_period_times()
        total_weekly_periods = daily_periods * len(days)

        for idx, t in enumerate(teachers_list, start=1):
            lessons = self.db.get_teacher_lessons(t.id)
            active_h = sum(1 for l in lessons if not l.is_free and (l.class_name or l.subject_code))
            free_h = max(0, total_weekly_periods - active_h)
            r_idx = idx + 3
            row_vals = [idx, t.name, t.branch or "-", active_h, free_h]
            ws_summary.append(row_vals)
            for col_i in range(1, 6):
                cell = ws_summary.cell(row=r_idx, column=col_i)
                cell.font = bold_font if col_i in (2, 4) else cell_font
                cell.border = thin_border
                cell.alignment = align_center if col_i in (1, 4, 5) else Alignment(horizontal="left", vertical="center")
                if idx % 2 == 0:
                    cell.fill = zebra_fill

        ws_summary.column_dimensions["A"].width = 8
        ws_summary.column_dimensions["B"].width = 28
        ws_summary.column_dimensions["C"].width = 24
        ws_summary.column_dimensions["D"].width = 18
        ws_summary.column_dimensions["E"].width = 14

        # 2. Her Öğretmen İçin Detay Sayfası / Bloklar
        # Eğer tek bir öğretmen ise doğrudan onun sayfası veya tüm öğretmenlerin sayfaları
        for t in teachers_list[:35]:  # Excel limit
            safe_title = "".join(c for c in t.name if c.isalnum() or c in (" ", "_"))[:28].strip()
            ws_t = wb.create_sheet(title=safe_title or f"Öğretmen_{t.id[:6]}")

            ws_t.merge_cells("A1:F1")
            ws_t["A1"] = f"{school.name} - ÖĞRETMEN HAFTALIK DERS PROGRAMI"
            ws_t["A1"].font = title_font
            ws_t["A1"].alignment = align_center

            ws_t.merge_cells("A2:F2")
            ws_t["A2"] = f"Öğretmen: {t.name}  |  Branş: {t.branch or '-'}  |  Eğitim Yılı: {school.academic_year}"
            ws_t["A2"].font = bold_font
            ws_t["A2"].alignment = align_center

            ws_t.append([])
            hdr_row = ["Ders Saati"] + days
            ws_t.append(hdr_row)
            for c_i in range(1, 7):
                cell = ws_t.cell(row=4, column=c_i)
                cell.fill = sub_fill
                cell.font = sub_font
                cell.alignment = align_center
                cell.border = thin_border

            lessons = self.db.get_teacher_lessons(t.id)
            l_map = {(l.day_name, l.period): l for l in lessons}

            for p in range(1, daily_periods + 1):
                time_str = period_times.get(p, "")
                row = [f"{p}. Ders\n({time_str})"]
                for d in days:
                    item = l_map.get((d, p))
                    if item and not item.is_free and (item.class_name or item.subject_code):
                        row.append(f"{item.class_name}\n{item.subject_code}")
                    else:
                        row.append("—")
                ws_t.append(row)
                r_num = p + 4
                for c_i in range(1, 7):
                    cell = ws_t.cell(row=r_num, column=c_i)
                    cell.border = thin_border
                    cell.alignment = align_center
                    if c_i == 1:
                        cell.fill = gray_fill
                        cell.font = bold_font
                    else:
                        cell.font = bold_font if cell.value != "—" else cell_font
                        if p % 2 == 0:
                            cell.fill = zebra_fill

            ws_t.column_dimensions["A"].width = 16
            for col_letter in ["B", "C", "D", "E", "F"]:
                ws_t.column_dimensions[col_letter].width = 18

        output_path.parent.mkdir(parents=True, exist_ok=True)
        wb.save(output_path)
        logger.info(f"Öğretmen ders programı Excel oluşturuldu: {output_path}")
        return output_path

    export_all_teachers_excel = export_teacher_timetable_excel

    # 10. SINIF / ŞUBE HAFTALIK DERS PROGRAMI PDF (.pdf)
    def export_class_timetable_pdf(self, output_path: Path, class_name: Optional[str] = None) -> Path:
        _register_pdf_fonts()
        school = self.db.get_school_info()
        today_str = datetime.date.today().strftime("%d.%m.%Y")
        days = self._get_timetable_days()

        classes_list: List[str] = []
        if class_name:
            classes_list.append(class_name)
        else:
            classes_list = self.db.get_distinct_classes()

        if not classes_list:
            classes_list = ["5-A", "6-A", "7-A", "8-A"]

        teachers_map = {t.id: t.name for t in self.db.get_teachers()}

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=25,
            leftMargin=25,
            topMargin=25,
            bottomMargin=25
        )

        font_family = "CustomArial" if _FONT_REGISTERED else "Helvetica"
        font_bold = "CustomArial-Bold" if _FONT_REGISTERED else "Helvetica-Bold"

        title_style = ParagraphStyle("ClsPdfTitle", fontName=font_bold, fontSize=11, alignment=1, leading=14)
        subtitle_style = ParagraphStyle("ClsPdfSubTitle", fontName=font_bold, fontSize=11.5, alignment=1, textColor=colors.HexColor("#1E3A8A"), leading=14)
        doc_title_style = ParagraphStyle("ClsDocTitle", fontName=font_bold, fontSize=11.5, alignment=1, textColor=colors.HexColor("#0D9488"), leading=14)
        info_style = ParagraphStyle("ClsInfo", fontName=font_bold, fontSize=10, alignment=0, leading=12)
        info_right_style = ParagraphStyle("ClsInfoRight", fontName=font_bold, fontSize=9.5, alignment=2, leading=12)
        hdr_style = ParagraphStyle("ClsHdr", fontName=font_bold, fontSize=8.5, alignment=1, textColor=colors.white, leading=10)
        day_hdr_style = ParagraphStyle("ClsDayHdr", fontName=font_bold, fontSize=8.5, alignment=1, textColor=colors.HexColor("#0F172A"), leading=10)
        cell_subj_style = ParagraphStyle("ClsCellSubj", fontName=font_bold, fontSize=8, alignment=1, textColor=colors.HexColor("#0F172A"), leading=10)
        cell_t_style = ParagraphStyle("ClsCellT", fontName=font_family, fontSize=7, alignment=1, textColor=colors.HexColor("#475569"), leading=9)
        sign_style = ParagraphStyle("ClsSign", fontName=font_bold, fontSize=9, alignment=1, leading=12)

        story = []

        for idx, c_name in enumerate(classes_list):
            if idx > 0:
                story.append(PageBreak())

            lessons = self.db.get_class_lessons(c_name)
            l_map: Dict[Tuple[str, int], TeacherLesson] = {(l.day_name, l.period): l for l in lessons}

            # Header
            story.append(Paragraph("T.C.", title_style))
            story.append(Paragraph(f"{school.district.upper()} KAYMAKAMLIĞI", title_style))
            story.append(Paragraph(f"{school.name} Müdürlüğü", subtitle_style))
            story.append(Spacer(1, 2))
            story.append(Paragraph(f"SINIF / ŞUBE HAFTALIK DERS PROGRAMI ({school.academic_year})", doc_title_style))
            story.append(Spacer(1, 6))

            info_data = [
                [Paragraph(f"<b>Sınıf / Şube:</b> {c_name}", info_style),
                 Paragraph(f"<b>Düzenleme Tarihi:</b> {today_str}", info_right_style)]
            ]
            t_info = Table(info_data, colWidths=[360, 185])
            t_info.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(t_info)
            story.append(Spacer(1, 4))

            daily_periods = school.daily_periods if (school and school.daily_periods) else 7
            period_times = self.get_period_times()
            col_widths = [75] + [94] * 5
            headers = [Paragraph("Ders Saati", hdr_style)] + [Paragraph(d, hdr_style) for d in days]
            table_data = [headers]

            for p in range(1, daily_periods + 1):
                time_range = period_times.get(p, "")
                row = [Paragraph(f"<b>{p}. Ders</b><br/><font size=6.5 color='#64748B'>{time_range}</font>", day_hdr_style)]
                for d in days:
                    item = l_map.get((d, p))
                    if item and (item.subject_code or item.class_name):
                        t_name = teachers_map.get(item.teacher_id, "")
                        cell_p = [
                            Paragraph(item.subject_code or "-", cell_subj_style),
                            Paragraph(t_name, cell_t_style)
                        ]
                    else:
                        cell_p = [Paragraph("—", ParagraphStyle("Emp", fontName=font_family, fontSize=8, alignment=1, textColor=colors.HexColor("#94A3B8")))]
                    row.append(cell_p)
                table_data.append(row)

            tbl = Table(table_data, colWidths=col_widths)
            row_pad = 4 if daily_periods <= 7 else (3 if daily_periods <= 8 else 2)
            tbl_style = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0D9488")),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ('TOPPADDING', (0, 0), (-1, -1), row_pad),
                ('BOTTOMPADDING', (0, 0), (-1, -1), row_pad),
            ]
            for r in range(1, daily_periods + 1):
                tbl_style.append(('BACKGROUND', (0, r), (0, r), colors.HexColor("#F0FDFA")))
                if r % 2 == 0:
                    tbl_style.append(('BACKGROUND', (1, r), (-1, r), colors.HexColor("#F8FAFC")))
            tbl.setStyle(TableStyle(tbl_style))
            story.append(tbl)
            story.append(Spacer(1, 20))

            sign_data = [
                [Paragraph("Sınıf Rehber Öğretmeni", sign_style),
                 Paragraph(f"{today_str}<br/>{school.principal_name}<br/>Okul Müdürü", sign_style)]
            ]
            sign_tbl = Table(sign_data, colWidths=[270, 275])
            sign_tbl.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(sign_tbl)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.build(story)
        logger.info(f"Sınıf ders programı PDF oluşturuldu: {output_path}")
        return output_path

    # 11. SINIF / ŞUBE HAFTALIK DERS PROGRAMI EXCEL (.xlsx)
    def export_class_timetable_excel(self, output_path: Path, class_name: Optional[str] = None) -> Path:
        school = self.db.get_school_info()
        days = self._get_timetable_days()

        classes_list: List[str] = []
        if class_name:
            classes_list.append(class_name)
        else:
            classes_list = self.db.get_distinct_classes()

        teachers_map = {t.id: t.name for t in self.db.get_teachers()}

        wb = openpyxl.Workbook()
        ws_first = wb.active

        hdr_fill = PatternFill(start_color="0D9488", end_color="0D9488", fill_type="solid")
        hdr_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        gray_fill = PatternFill(start_color="F0FDFA", end_color="F0FDFA", fill_type="solid")
        zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        cell_font = Font(name="Calibri", size=9.5)
        bold_font = Font(name="Calibri", size=9.5, bold=True)
        title_font = Font(name="Calibri", size=12, bold=True, color="0F766E")
        thin_border = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1')
        )
        align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)

        for c_idx, c_name in enumerate(classes_list):
            clean_title = "".join(c for c in c_name if c not in r"/\?*:[ ]")[:30].strip() or f"Sinif_{c_idx+1}"
            ws = ws_first if c_idx == 0 else wb.create_sheet(title=clean_title)
            if c_idx == 0:
                ws.title = clean_title

            ws.merge_cells("A1:F1")
            ws["A1"] = f"{school.name} - {c_name} SINIFI HAFTALIK DERS PROGRAMI ({school.academic_year})"
            ws["A1"].font = title_font
            ws["A1"].alignment = align_center

            ws.append([])
            ws.append(["Ders Saati"] + days)
            for c_i in range(1, 7):
                cell = ws.cell(row=3, column=c_i)
                cell.fill = hdr_fill
                cell.font = hdr_font
                cell.alignment = align_center
                cell.border = thin_border

            lessons = self.db.get_class_lessons(c_name)
            l_map = {(l.day_name, l.period): l for l in lessons}

            daily_periods = school.daily_periods if (school and school.daily_periods) else 7
            period_times = self.get_period_times()

            for p in range(1, daily_periods + 1):
                time_str = period_times.get(p, "")
                row = [f"{p}. Ders\n({time_str})"]
                for d in days:
                    item = l_map.get((d, p))
                    if item and (item.subject_code or item.class_name):
                        t_name = teachers_map.get(item.teacher_id, "")
                        row.append(f"{item.subject_code}\n({t_name})")
                    else:
                        row.append("—")
                ws.append(row)
                r_num = p + 3
                for c_i in range(1, 7):
                    cell = ws.cell(row=r_num, column=c_i)
                    cell.border = thin_border
                    cell.alignment = align_center
                    if c_i == 1:
                        cell.fill = gray_fill
                        cell.font = bold_font
                    else:
                        cell.font = bold_font if cell.value != "—" else cell_font
                        if p % 2 == 0:
                            cell.fill = zebra_fill

            ws.column_dimensions["A"].width = 16
            for col_letter in ["B", "C", "D", "E", "F"]:
                ws.column_dimensions[col_letter].width = 20

        output_path.parent.mkdir(parents=True, exist_ok=True)
        wb.save(output_path)
        logger.info(f"Sınıf ders programı Excel oluşturuldu: {output_path}")
        return output_path

    # 12. GENEL ÇARŞAF DERS PROGRAMI EXCEL (.xlsx)
    def export_master_timetable_excel(self, output_path: Path) -> Path:
        school = self.db.get_school_info()
        days = self._get_timetable_days()
        teachers = self.db.get_teachers(active_only=True)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Genel Çarşaf Ders Programı"

        # Stiller
        hdr_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        hdr_font = Font(name="Calibri", size=9, bold=True, color="FFFFFF")
        day_fill = PatternFill(start_color="334155", end_color="334155", fill_type="solid")
        day_font = Font(name="Calibri", size=9.5, bold=True, color="FFFFFF")
        period_fill = PatternFill(start_color="475569", end_color="475569", fill_type="solid")
        period_font = Font(name="Calibri", size=8, bold=True, color="FFFFFF")
        zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        cell_font = Font(name="Calibri", size=8.5)
        bold_font = Font(name="Calibri", size=8.5, bold=True)
        title_font = Font(name="Calibri", size=13, bold=True, color="1E3A8A")
        thin_border = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1')
        )
        align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)

        # Başlık
        daily_periods = school.daily_periods if (school and school.daily_periods) else 7
        total_cols = 3 + (len(days) * daily_periods) + 1  # No, Ad Soyad, Branş, haftalık dersler, Toplam
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=total_cols)
        ws["A1"] = f"{school.name} - GENEL HAFTALIK ÇARŞAF DERS PROGRAMI ({school.academic_year})"
        ws["A1"].font = title_font
        ws["A1"].alignment = align_center

        # Satır 2: Gün Başlıkları (Merge edilmiş)
        ws.merge_cells("A2:A3")
        ws["A2"] = "No"
        ws["A2"].fill = hdr_fill
        ws["A2"].font = hdr_font
        ws["A2"].alignment = align_center
        ws["A2"].border = thin_border

        ws.merge_cells("B2:B3")
        ws["B2"] = "Öğretmen Adı Soyadı"
        ws["B2"].fill = hdr_fill
        ws["B2"].font = hdr_font
        ws["B2"].alignment = align_center
        ws["B2"].border = thin_border

        ws.merge_cells("C2:C3")
        ws["C2"] = "Branş"
        ws["C2"].fill = hdr_fill
        ws["C2"].font = hdr_font
        ws["C2"].alignment = align_center
        ws["C2"].border = thin_border

        col_pointer = 4
        for d in days:
            start_c = col_pointer
            end_c = col_pointer + daily_periods - 1
            ws.merge_cells(start_row=2, start_column=start_c, end_row=2, end_column=end_c)
            top_cell = ws.cell(row=2, column=start_c, value=d)
            top_cell.fill = day_fill
            top_cell.font = day_font
            top_cell.alignment = align_center
            for c_i in range(start_c, end_c + 1):
                ws.cell(row=2, column=c_i).border = thin_border
                p_num = c_i - start_c + 1
                p_cell = ws.cell(row=3, column=c_i, value=f"{p_num}.D")
                p_cell.fill = period_fill
                p_cell.font = period_font
                p_cell.alignment = align_center
                p_cell.border = thin_border
            col_pointer += daily_periods

        ws.merge_cells(start_row=2, start_column=col_pointer, end_row=3, end_column=col_pointer)
        tot_cell = ws.cell(row=2, column=col_pointer, value="Toplam\nDers")
        tot_cell.fill = hdr_fill
        tot_cell.font = hdr_font
        tot_cell.alignment = align_center
        tot_cell.border = thin_border

        # Öğretmen Satırları
        for t_idx, t in enumerate(teachers, start=1):
            curr_row = t_idx + 3
            lessons = self.db.get_teacher_lessons(t.id)
            l_map = {(l.day_name, l.period): l for l in lessons}
            active_h = sum(1 for l in lessons if not l.is_free and (l.class_name or l.subject_code))

            ws.cell(row=curr_row, column=1, value=t_idx).alignment = align_center
            ws.cell(row=curr_row, column=2, value=t.name).alignment = Alignment(horizontal="left", vertical="center")
            ws.cell(row=curr_row, column=3, value=t.branch or "-").alignment = Alignment(horizontal="left", vertical="center")

            ws.cell(row=curr_row, column=1).font = cell_font
            ws.cell(row=curr_row, column=2).font = bold_font
            ws.cell(row=curr_row, column=3).font = cell_font

            c_pointer = 4
            for d in days:
                for p in range(1, daily_periods + 1):
                    item = l_map.get((d, p))
                    val_str = ""
                    if item and not item.is_free and (item.class_name or item.subject_code):
                        val_str = f"{item.class_name}"
                        if item.subject_code and len(item.subject_code) <= 5:
                            val_str += f" {item.subject_code}"
                    c_cell = ws.cell(row=curr_row, column=c_pointer, value=val_str)
                    c_cell.font = cell_font
                    c_cell.alignment = align_center
                    c_cell.border = thin_border
                    if t_idx % 2 == 0:
                        c_cell.fill = zebra_fill
                    c_pointer += 1

            t_tot_cell = ws.cell(row=curr_row, column=c_pointer, value=active_h)
            t_tot_cell.font = bold_font
            t_tot_cell.alignment = align_center
            t_tot_cell.border = thin_border

            for c_i in range(1, 4):
                ws.cell(row=curr_row, column=c_i).border = thin_border
                if t_idx % 2 == 0:
                    ws.cell(row=curr_row, column=c_i).fill = zebra_fill

        ws.column_dimensions["A"].width = 5
        ws.column_dimensions["B"].width = 24
        ws.column_dimensions["C"].width = 20
        for c_i in range(4, total_cols):
            ws.column_dimensions[get_column_letter(c_i)].width = 7
        ws.column_dimensions[get_column_letter(total_cols)].width = 9

        output_path.parent.mkdir(parents=True, exist_ok=True)
        wb.save(output_path)
        logger.info(f"Genel Çarşaf Ders Programı Excel oluşturuldu: {output_path}")
        return output_path

    # 13. ÖĞRETMEN BOŞ DERS VE NÖBET İKAME UYGUNLUK EXCEL (.xlsx)
    def export_free_periods_excel(self, output_path: Path) -> Path:
        school = self.db.get_school_info()
        days = self._get_timetable_days()
        teachers = self.db.get_teachers(active_only=True)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Boş Dersler ve Nöbet Uygunluk"

        hdr_fill = PatternFill(start_color="166534", end_color="166534", fill_type="solid")
        hdr_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        zebra_fill = PatternFill(start_color="F0FDF4", end_color="F0FDF4", fill_type="solid")
        cell_font = Font(name="Calibri", size=9.5)
        bold_font = Font(name="Calibri", size=9.5, bold=True)
        title_font = Font(name="Calibri", size=12, bold=True, color="166534")
        thin_border = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1')
        )
        align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)

        ws.merge_cells("A1:H1")
        ws["A1"] = f"{school.name} - ÖĞRETMEN GÜNLÜK BOŞ DERS VE İKAME UYGUNLUK ÇİZELGESİ"
        ws["A1"].font = title_font
        ws["A1"].alignment = align_center

        headers = ["No", "Öğretmen Adı Soyadı", "Branşı"] + days
        ws.append([])
        ws.append(headers)
        for c_i in range(1, 9):
            cell = ws.cell(row=3, column=c_i)
            cell.fill = hdr_fill
            cell.font = hdr_font
            cell.alignment = align_center
            cell.border = thin_border

        daily_periods = school.daily_periods if (school and school.daily_periods) else 7

        for idx, t in enumerate(teachers, start=1):
            lessons = self.db.get_teacher_lessons(t.id)
            l_map = {(l.day_name, l.period): l for l in lessons}

            row_vals = [idx, t.name, t.branch or "-"]
            for d in days:
                free_periods = [p for p in range(1, daily_periods + 1) if l_map.get((d, p)) is None or l_map[(d, p)].is_free or not (l_map[(d, p)].class_name or l_map[(d, p)].subject_code)]
                if len(free_periods) == daily_periods:
                    row_vals.append("Tüm Gün Boş 🟢")
                elif free_periods:
                    row_vals.append(f"{', '.join(map(str, free_periods))}. Ders")
                else:
                    row_vals.append("Dolu 🔴")

            ws.append(row_vals)
            r_idx = idx + 3
            for c_i in range(1, 9):
                cell = ws.cell(row=r_idx, column=c_i)
                cell.border = thin_border
                cell.alignment = align_center if c_i not in (2, 3) else Alignment(horizontal="left", vertical="center")
                cell.font = bold_font if c_i == 2 else cell_font
                if idx % 2 == 0:
                    cell.fill = zebra_fill

        ws.column_dimensions["A"].width = 6
        ws.column_dimensions["B"].width = 26
        ws.column_dimensions["C"].width = 22
        for col_l in ["D", "E", "F", "G", "H"]:
            ws.column_dimensions[col_l].width = 18

        output_path.parent.mkdir(parents=True, exist_ok=True)
        wb.save(output_path)
        logger.info(f"Boş ders çizelgesi Excel oluşturuldu: {output_path}")
        return output_path

    # =========================================================================
    # AY SONU İKAME VE EK DERS ÇIKTILARI (MONTHLY EK DERS EXPORTS)
    # =========================================================================

    def export_monthly_ek_ders_excel(self, month_str: str, output_path: Path) -> Path:
        """
        Belirtilen ay (YYYY-MM) için ikame derse giren öğretmenlerin
        ek ders tahakkuk ve nöbet nezareti icmalini Excel (.xlsx) olarak üretir.
        """
        from logic.substitution_service import get_monthly_ek_ders_summary
        summary = get_monthly_ek_ders_summary(self.db, month_str)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"Ek Ders İcmal {month_str}"
        ws.views.sheetView[0].showGridLines = True

        school = self.db.get_school_info()
        today_str = datetime.date.today().strftime("%d.%m.%Y")

        font_title = Font(name="Calibri", size=14, bold=True, color="1E3A8A")
        font_sub = Font(name="Calibri", size=11, bold=True, color="334155")
        font_hdr = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        font_bold = Font(name="Calibri", size=10, bold=True)
        font_norm = Font(name="Calibri", size=10)
        font_meta = Font(name="Calibri", size=9, italic=True, color="64748B")

        fill_hdr = PatternFill("solid", fgColor="1E3A8A")
        fill_zebra = PatternFill("solid", fgColor="F8FAFC")
        fill_ek_ders = PatternFill("solid", fgColor="DCFCE7")  # Hafif yeşil vurgulama
        fill_total = PatternFill("solid", fgColor="E2E8F0")

        thin_border = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1')
        )

        align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
        align_left = Alignment(horizontal="left", vertical="center")
        align_right = Alignment(horizontal="right", vertical="center")

        # Başlık Blokları
        ws.merge_cells("A1:H1")
        ws["A1"] = f"T.C. {school.district.upper() if school.district else ''} {school.name.upper()} MÜDÜRLÜĞÜ"
        ws["A1"].font = font_title
        ws["A1"].alignment = align_center

        ws.merge_cells("A2:H2")
        ws["A2"] = f"AY SONU İKAME DERS VE EK DERS TAHAKKUK İCMALİ ({month_str})"
        ws["A2"].font = font_sub
        ws["A2"].alignment = align_center

        ws.merge_cells("A3:H3")
        ws["A3"] = f"Rapor Tarihi: {today_str} | Toplam İkame: {summary['total_hours']} Saat | Ek Ders Hak Edilen: {summary['total_ek_ders_hours']} Saat | Hak Eden Öğretmen: {summary['eligible_teacher_count']} Kişi"
        ws["A3"].font = font_meta
        ws["A3"].alignment = align_center

        # Tablo Başlıkları
        headers = [
            "Sıra",
            "Öğretmen Adı Soyadı",
            "Branşı",
            "Toplam İkame (Saat)",
            "Ek Ders Hak Ediş (Saat)",
            "Nöbet Nezareti (Saat)",
            "Girdiği Sınıflar",
            "Mevzuat / Açıklama"
        ]
        ws.append([])  # 4. satır boş
        ws.append(headers)  # 5. satır başlıklar
        ws.row_dimensions[5].height = 28

        for col_idx in range(1, 9):
            cell = ws.cell(row=5, column=col_idx)
            cell.font = font_hdr
            cell.fill = fill_hdr
            cell.alignment = align_center
            cell.border = thin_border

        # Veri Satırları
        row_idx = 6
        for idx, st in enumerate(summary["teachers"], start=1):
            is_eligible = st["ek_ders_hours"] > 0
            mevzuat_note = "MEB Yön. Md. 44 (Aynı Branş / Ek Ders)" if is_eligible else "Nöbet Gözetim Görevi (Ücretsiz)"

            row_data = [
                idx,
                st["teacher_name"],
                st["branch"] or "-",
                st["total_substitutions"],
                st["ek_ders_hours"],
                st["supervision_hours"],
                st["classes_str"],
                mevzuat_note
            ]
            ws.append(row_data)
            ws.row_dimensions[row_idx].height = 22

            for c_i in range(1, 9):
                cell = ws.cell(row=row_idx, column=c_i)
                cell.border = thin_border
                cell.font = font_bold if (c_i == 5 and is_eligible) or c_i == 2 else font_norm

                if c_i in (1, 4, 5, 6):
                    cell.alignment = align_center
                else:
                    cell.alignment = align_left

                if is_eligible and c_i == 5:
                    cell.fill = fill_ek_ders
                elif idx % 2 == 0:
                    cell.fill = fill_zebra

            row_idx += 1

        # Genel Toplam Satırı
        total_row = [
            "",
            "GENEL TOPLAM",
            "",
            summary["total_hours"],
            summary["total_ek_ders_hours"],
            summary["total_supervision_hours"],
            "",
            f"Toplam {summary['eligible_teacher_count']} öğretmen ek ders hak etti."
        ]
        ws.append(total_row)
        ws.row_dimensions[row_idx].height = 24
        for c_i in range(1, 9):
            cell = ws.cell(row=row_idx, column=c_i)
            cell.font = font_bold
            cell.fill = fill_total
            cell.border = thin_border
            cell.alignment = align_center if c_i in (4, 5, 6) else align_left

        row_idx += 2
        # İmza Bloğu
        ws.cell(row=row_idx, column=2, value=f"{today_str}\nDüzenleyen\nMüdür Yardımcısı").alignment = align_center
        ws.cell(row=row_idx, column=2).font = font_bold

        ws.cell(row=row_idx, column=6, value=f"{today_str}\n{school.principal_name}\nOkul Müdürü").alignment = align_center
        ws.cell(row=row_idx, column=6).font = font_bold

        # Sütun Genişlikleri
        ws.column_dimensions["A"].width = 6
        ws.column_dimensions["B"].width = 28
        ws.column_dimensions["C"].width = 22
        ws.column_dimensions["D"].width = 16
        ws.column_dimensions["E"].width = 18
        ws.column_dimensions["F"].width = 16
        ws.column_dimensions["G"].width = 24
        ws.column_dimensions["H"].width = 32

        output_path.parent.mkdir(parents=True, exist_ok=True)
        wb.save(output_path)
        logger.info(f"Ay sonu ek ders Excel icmali oluşturuldu: {output_path}")
        return output_path

    def export_monthly_ek_ders_pdf(self, month_str: str, output_path: Path) -> Path:
        """
        Belirtilen ay (YYYY-MM) için ikame derse giren öğretmenlerin
        ek ders tahakkuk ve nöbet nezareti icmalini resmi formatta PDF olarak üretir.
        """
        _register_pdf_fonts()
        from logic.substitution_service import get_monthly_ek_ders_summary
        summary = get_monthly_ek_ders_summary(self.db, month_str)

        school = self.db.get_school_info()
        today_str = datetime.date.today().strftime("%d.%m.%Y")

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=landscape(A4),
            rightMargin=24,
            leftMargin=24,
            topMargin=25,
            bottomMargin=25
        )

        font_family = "CustomArial" if _FONT_REGISTERED else "Helvetica"
        font_bold = "CustomArial-Bold" if _FONT_REGISTERED else "Helvetica-Bold"

        title_style = ParagraphStyle(
            name="EkDersPdfTitle",
            fontName=font_bold,
            fontSize=11,
            alignment=1,
            leading=14
        )
        subtitle_style = ParagraphStyle(
            name="EkDersPdfSubTitle",
            fontName=font_bold,
            fontSize=12,
            alignment=1,
            textColor=colors.HexColor("#1E3A8A"),
            leading=15
        )
        meta_style = ParagraphStyle(
            name="EkDersPdfMeta",
            fontName=font_family,
            fontSize=8,
            alignment=1,
            textColor=colors.HexColor("#64748B"),
            leading=11
        )
        hdr_cell_style = ParagraphStyle(
            name="EkDersHdrCell",
            fontName=font_bold,
            fontSize=8,
            alignment=1,
            textColor=colors.white,
            leading=10
        )
        cell_style = ParagraphStyle(
            name="EkDersCell",
            fontName=font_family,
            fontSize=8,
            alignment=0,
            leading=10
        )
        cell_center = ParagraphStyle(
            name="EkDersCellCenter",
            fontName=font_family,
            fontSize=8,
            alignment=1,
            leading=10
        )
        cell_bold_center = ParagraphStyle(
            name="EkDersCellBoldCenter",
            fontName=font_bold,
            fontSize=8,
            alignment=1,
            leading=10
        )
        sign_style = ParagraphStyle(
            name="EkDersSign",
            fontName=font_bold,
            fontSize=9,
            alignment=1,
            leading=13
        )

        story = []

        # Başlık
        dist_str = f" / {school.district.upper()}" if school.district else ""
        story.append(Paragraph(f"T.C.<br/>{school.city.upper()}{dist_str} KAYMAKAMLIĞI<br/>{school.name.upper()} MÜDÜRLÜĞÜ", title_style))
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"AY SONU İKAME DERS VE EK DERS TAHAKKUK İCMALİ ({month_str})", subtitle_style))
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            f"Rapor Tarihi: {today_str} &nbsp;|&nbsp; Toplam İkame: {summary['total_hours']} Saat &nbsp;|&nbsp; "
            f"Ek Ders Hak Edilen: <b>{summary['total_ek_ders_hours']} Saat</b> &nbsp;|&nbsp; Hak Eden Öğretmen: {summary['eligible_teacher_count']} Kişi",
            meta_style
        ))
        story.append(Spacer(1, 10))

        # Tablo
        table_data = [[
            Paragraph("Sıra", hdr_cell_style),
            Paragraph("Öğretmen Adı Soyadı", hdr_cell_style),
            Paragraph("Branşı", hdr_cell_style),
            Paragraph("Toplam İkame", hdr_cell_style),
            Paragraph("Ek Ders Hak Ediş", hdr_cell_style),
            Paragraph("Nöbet Nezareti", hdr_cell_style),
            Paragraph("Girdiği Sınıflar", hdr_cell_style),
            Paragraph("Mevzuat / Açıklama", hdr_cell_style)
        ]]

        for idx, st in enumerate(summary["teachers"], start=1):
            is_eligible = st["ek_ders_hours"] > 0
            ek_text = f"<b>{st['ek_ders_hours']} Saat ⭐</b>" if is_eligible else "0"
            mevzuat = "MEB Yön. Md. 44 (Aynı Branş / Ek Ders)" if is_eligible else "Nöbet Gözetim Görevi"

            table_data.append([
                Paragraph(str(idx), cell_center),
                Paragraph(f"<b>{st['teacher_name']}</b>", cell_style),
                Paragraph(st["branch"] or "-", cell_style),
                Paragraph(f"{st['total_substitutions']} Saat", cell_center),
                Paragraph(ek_text, cell_bold_center if is_eligible else cell_center),
                Paragraph(f"{st['supervision_hours']} Saat", cell_center),
                Paragraph(st["classes_str"], cell_style),
                Paragraph(mevzuat, cell_style)
            ])

        # Toplam Satırı
        table_data.append([
            Paragraph("", cell_center),
            Paragraph("<b>GENEL TOPLAM</b>", cell_style),
            Paragraph("", cell_style),
            Paragraph(f"<b>{summary['total_hours']} Saat</b>", cell_bold_center),
            Paragraph(f"<b>{summary['total_ek_ders_hours']} Saat</b>", cell_bold_center),
            Paragraph(f"<b>{summary['total_supervision_hours']} Saat</b>", cell_bold_center),
            Paragraph("", cell_style),
            Paragraph(f"<b>{summary['eligible_teacher_count']} Öğretmen Hak Etti</b>", cell_style)
        ])

        col_widths = [26, 130, 95, 75, 85, 75, 110, 160]
        tbl = Table(table_data, colWidths=col_widths, repeatRows=1)

        t_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]

        for i in range(1, len(table_data) - 1):
            if i % 2 == 0:
                t_style.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor("#F8FAFC")))
            # Ek ders alanları hafif yeşille vurgula
            if summary["teachers"][i-1]["ek_ders_hours"] > 0:
                t_style.append(('BACKGROUND', (4, i), (4, i), colors.HexColor("#DCFCE7")))

        # Toplam satırı stili
        total_row_idx = len(table_data) - 1
        t_style.append(('BACKGROUND', (0, total_row_idx), (-1, total_row_idx), colors.HexColor("#E2E8F0")))

        tbl.setStyle(TableStyle(t_style))
        story.append(tbl)
        story.append(Spacer(1, 14))

        # Yasal Not
        note_style = ParagraphStyle(
            name="EkDersNote",
            fontName=font_family,
            fontSize=7,
            textColor=colors.HexColor("#64748B"),
            leading=9
        )
        story.append(Paragraph(
            "<i>* MEB Okul Öncesi ve İlköğretim Kurumları Yönetmeliği Madde 44 uyarınca; nöbetçi öğretmenler boş ders saatlerinde sınıflara nezaret etmekle "
            "yükümlüdür. Gelmeyen öğretmenle aynı branşta olup derse fiilen giren nöbetçi öğretmenlere ilgili mevzuat uyarınca ek ders ücreti tahakkuk ettirilir.</i>",
            note_style
        ))
        story.append(Spacer(1, 16))

        # İmza Bloğu
        sign_table_data = [
            [
                Paragraph(f"{today_str}<br/>Düzenleyen<br/>Müdür Yardımcısı", sign_style),
                Paragraph(f"{today_str}<br/>{school.principal_name}<br/>Okul Müdürü", sign_style)
            ]
        ]
        sign_tbl = Table(sign_table_data, colWidths=[380, 380])
        sign_tbl.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(sign_tbl)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.build(story)
        logger.info(f"Ay sonu ek ders PDF icmali oluşturuldu: {output_path}")
        return output_path

    # =========================================================================
    # 16. RESMİ MEB GÜNLÜK NÖBET DEFTERİ VE KONTROL RAPORU PDF
    # =========================================================================
    def export_daily_duty_log_pdf(
        self,
        date_str: str,
        output_path: Path,
        custom_notes: str = "",
        include_full_week: bool = False
    ) -> Path:
        """
        Resmi MEB Günlük Nöbet Defteri ve Olay Çizelgesi PDF çıktısı üretir.
        include_full_week=True ise haftanın 5 gününü sayfa sayfa (kitapçık) basar.
        """
        _register_pdf_fonts()
        font_family = "CustomArial"
        font_bold = "CustomArial-Bold"

        school = self.db.get_school_info()
        days_all = self.db.get_days()
        day_map = {d.name: d.id for d in days_all}
        locations_all = self.db.get_locations(active_only=True)
        loc_map = {loc.id: loc for loc in locations_all}
        teachers_all = {t.id: t for t in self.db.get_teachers()}
        period_times = self.get_period_times()
        daily_periods = school.daily_periods or 7

        start_offset = 30
        end_offset = 30
        try:
            start_offset = int(self.db.get_setting("duty_start_offset", "30") or 30)
            end_offset = int(self.db.get_setting("duty_end_offset", "30") or 30)
        except Exception:
            pass

        first_t = period_times.get(1, "08:30 - 09:10")
        last_t = period_times.get(daily_periods, "15:00 - 15:40")
        first_s = first_t.split(" - ")[0].strip() if " - " in first_t else "08:30"
        last_e = last_t.split(" - ")[-1].strip() if " - " in last_t else "15:00"

        try:
            f_h, f_m = map(int, first_s.split(":"))
            l_h, l_m = map(int, last_e.split(":"))
            duty_start_min = max(0, f_h * 60 + f_m - start_offset)
            duty_end_min = min(24 * 60 - 1, l_h * 60 + l_m + end_offset)
            duty_hours_str = f"{(duty_start_min // 60):02d}:{(duty_start_min % 60):02d} - {(duty_end_min // 60):02d}:{(duty_end_min % 60):02d}"
        except Exception:
            duty_hours_str = f"{first_s} - {last_e}"

        vp_name = self.db.get_setting("vice_principal_name", "Nöbetten Sorumlu Md. Yrd.")

        try:
            base_dt = datetime.date.fromisoformat(date_str)
        except Exception:
            base_dt = datetime.date.today()

        if include_full_week:
            monday_dt = base_dt - datetime.timedelta(days=base_dt.weekday())
            target_dates = [monday_dt + datetime.timedelta(days=i) for i in range(5)]
        else:
            target_dates = [base_dt]

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=25,
            leftMargin=25,
            topMargin=18,
            bottomMargin=18
        )

        title_style = ParagraphStyle("DLTitle", fontName=font_bold, fontSize=10.5, alignment=1, leading=13, textColor=colors.HexColor("#0F172A"))
        subtitle_style = ParagraphStyle("DLSubtitle", fontName=font_bold, fontSize=9.5, alignment=1, leading=12, textColor=colors.HexColor("#1E293B"))
        doc_heading = ParagraphStyle("DLDocHeading", fontName=font_bold, fontSize=11, alignment=1, leading=14, textColor=colors.HexColor("#1E3A8A"))
        meta_style = ParagraphStyle("DLMeta", fontName=font_family, fontSize=8, alignment=0, leading=10, textColor=colors.HexColor("#334155"))
        meta_right = ParagraphStyle("DLMetaRight", fontName=font_family, fontSize=8, alignment=2, leading=10, textColor=colors.HexColor("#334155"))

        sec_hdr_style = ParagraphStyle("DLSecHdr", fontName=font_bold, fontSize=8.5, alignment=0, leading=10, textColor=colors.HexColor("#0F172A"))
        tbl_hdr_style = ParagraphStyle("DLTblHdr", fontName=font_bold, fontSize=7.5, alignment=1, leading=9, textColor=colors.white)
        tbl_cell_center = ParagraphStyle("DLTblCellC", fontName=font_family, fontSize=7.5, alignment=1, leading=9, textColor=colors.HexColor("#1E293B"))
        tbl_cell_left = ParagraphStyle("DLTblCellL", fontName=font_family, fontSize=7.5, alignment=0, leading=9, textColor=colors.HexColor("#1E293B"))
        tbl_cell_bold_left = ParagraphStyle("DLTblCellBL", fontName=font_bold, fontSize=7.5, alignment=0, leading=9, textColor=colors.HexColor("#0F172A"))

        item_chk_style = ParagraphStyle("DLChkItem", fontName=font_family, fontSize=7.5, alignment=0, leading=9.5, textColor=colors.HexColor("#1E293B"))
        note_text_style = ParagraphStyle("DLNoteText", fontName=font_family, fontSize=7.5, alignment=0, leading=10, textColor=colors.HexColor("#334155"))
        sign_style = ParagraphStyle("DLSign", fontName=font_bold, fontSize=8, alignment=1, leading=10, textColor=colors.HexColor("#0F172A"))

        day_names_tr = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
        story = []

        for p_idx, d_dt in enumerate(target_dates):
            if p_idx > 0:
                story.append(PageBreak())

            iso_date = d_dt.isoformat()
            tr_date_str = d_dt.strftime("%d.%m.%Y")
            day_name = day_names_tr[d_dt.weekday()]
            week_start = (d_dt - datetime.timedelta(days=d_dt.weekday())).isoformat()
            cur_day_id = day_map.get(day_name)

            all_w_assigns = self.db.get_assignments_for_week(week_start)
            cur_assigns = [a for a in all_w_assigns if a.day_id == cur_day_id and a.teacher_id]
            cur_assigns.sort(key=lambda a: (getattr(loc_map.get(a.location_id), 'order_num', 99) if a.location_id in loc_map else 99, a.slot_index))

            att_records = self.db.get_attendance_records(date_str=iso_date)
            subs = self.db.get_substitutions_for_date(date_str=iso_date)

            # 1. Başlık Bloğu
            story.append(Paragraph("T.C.", title_style))
            story.append(Paragraph(f"{school.district.upper()} KAYMAKAMLIĞI", title_style))
            story.append(Paragraph(f"{school.name} Müdürlüğü", subtitle_style))
            story.append(Spacer(1, 2))
            story.append(Paragraph(f"GÜNLÜK NÖBET DEFTERİ VE KONTROL RAPORU ({school.academic_year})", doc_heading))
            story.append(Spacer(1, 3))

            # Bilgi Şeridi
            meta_data = [
                [
                    Paragraph(f"<b>Tarih / Gün:</b> {tr_date_str} {day_name} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Öğretim Şekli:</b> {getattr(school, 'education_type', 'Normal (Tekli)')}", meta_style),
                    Paragraph(f"<b>Nöbet Görev Süresi:</b> {duty_hours_str}", meta_right)
                ]
            ]
            t_meta = Table(meta_data, colWidths=[360, 185])
            t_meta.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ('TOPPADDING', (0, 0), (-1, -1), 2.5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(t_meta)
            story.append(Spacer(1, 5))

            # BÖLÜM 1: NÖBETÇİ PERSONEL
            story.append(Paragraph("<b>I. GÖREVLİ NÖBETÇİ ÖĞRETMENLER VE GÖREV YERLERİ</b>", sec_hdr_style))
            story.append(Spacer(1, 2))

            duty_headers = ["Sıra", "Nöbet / Görev Yeri", "Nöbetçi Öğretmen Adı Soyadı", "Branşı", "Görev Saati", "İmza / Teslim"]
            duty_table_data = [[Paragraph(h, tbl_hdr_style) for h in duty_headers]]

            if cur_assigns:
                for s_i, a in enumerate(cur_assigns, start=1):
                    loc = loc_map.get(a.location_id)
                    loc_name = loc.name if loc else "-"
                    t = teachers_all.get(a.teacher_id)
                    t_name = t.name if t else "-"
                    t_branch = t.branch if (t and t.branch) else "-"
                    duty_table_data.append([
                        Paragraph(str(s_i), tbl_cell_center),
                        Paragraph(f"<b>{loc_name}</b>", tbl_cell_left),
                        Paragraph(f"<b>{t_name}</b>", tbl_cell_bold_left),
                        Paragraph(t_branch, tbl_cell_left),
                        Paragraph(duty_hours_str.split(" (")[0], tbl_cell_center),
                        Paragraph("", tbl_cell_center)
                    ])
            else:
                duty_table_data.append([
                    Paragraph("—", tbl_cell_center),
                    Paragraph("<i>Bu gün için tanımlı nöbet ataması bulunamadı.</i>", tbl_cell_left),
                    Paragraph("—", tbl_cell_center),
                    Paragraph("—", tbl_cell_center),
                    Paragraph("—", tbl_cell_center),
                    Paragraph("", tbl_cell_center)
                ])

            t_duty = Table(duty_table_data, colWidths=[28, 135, 145, 95, 75, 67])
            t_duty_style = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E293B")),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ('TOPPADDING', (0, 0), (-1, -1), 2.5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
            ]
            for r in range(1, len(duty_table_data)):
                if r % 2 == 0:
                    t_duty_style.append(('BACKGROUND', (0, r), (-1, r), colors.HexColor("#F8FAFC")))
            t_duty.setStyle(TableStyle(t_duty_style))
            story.append(t_duty)
            story.append(Spacer(1, 5))

            # BÖLÜM 2: GELMEYEN ÖĞRETMENLER VE BOŞ DERS GÖREVLENDİRMELERİ (İKAME)
            story.append(Paragraph("<b>II. GELMEYEN ÖĞRETMENLER VE BOŞ DERS DOLDURMA (İKAME) DURUMU</b>", sec_hdr_style))
            story.append(Spacer(1, 2))

            if att_records or subs:
                sub_headers = ["Ders", "Gelmeyen Öğretmen", "Sınıf", "Ders Kodu", "İkame Görevlendirilen Nöbetçi", "Ek Ders / Durum"]
                sub_table_data = [[Paragraph(h, tbl_hdr_style) for h in sub_headers]]
                for sub in subs:
                    absent_t = teachers_all.get(sub.absent_teacher_id)
                    duty_t = teachers_all.get(sub.duty_teacher_id) if sub.duty_teacher_id else None
                    abs_name = absent_t.name if absent_t else "-"
                    duty_name = duty_t.name if duty_t else "— Boş / Atanmadı —"
                    ek_text = "⭐ Ek Ders" if sub.is_ek_ders else "Nöbet Görevi"
                    sub_table_data.append([
                        Paragraph(f"{sub.period}. Ders", tbl_cell_center),
                        Paragraph(f"<b>{abs_name}</b>", tbl_cell_left),
                        Paragraph(sub.class_name or "-", tbl_cell_center),
                        Paragraph(sub.subject_code or "-", tbl_cell_center),
                        Paragraph(f"<b>{duty_name}</b>", tbl_cell_left),
                        Paragraph(ek_text, tbl_cell_center)
                    ])
                t_sub = Table(sub_table_data, colWidths=[45, 130, 50, 65, 155, 100])
                t_sub_style = [
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2563EB")),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ('TOPPADDING', (0, 0), (-1, -1), 2),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ]
                for r in range(1, len(sub_table_data)):
                    if r % 2 == 0:
                        t_sub_style.append(('BACKGROUND', (0, r), (-1, r), colors.HexColor("#EFF6FF")))
                t_sub.setStyle(TableStyle(t_sub_style))
                story.append(t_sub)
            else:
                no_abs_box = [
                    [Paragraph("✓ <b>Gelmeyen Öğretmen Yok:</b> Bugün kurumumuzda izinli/raporlu öğretmen bulunmamaktadır. Tüm dersler zamanında ve eksiksiz işlenmiştir.", ParagraphStyle("NoAbs", fontName=font_family, fontSize=7.5, textColor=colors.HexColor("#166534")))]
                ]
                t_no_abs = Table(no_abs_box, colWidths=[545])
                t_no_abs.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F0FDF4")),
                    ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#86EFAC")),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ]))
                story.append(t_no_abs)

            story.append(Spacer(1, 5))

            # BÖLÜM 3: GÜNLÜK DENETİM MADDELERİ
            story.append(Paragraph("<b>III. GÜNLÜK NÖBET KONTROL MADDELERİ VE TESPİTLER</b>", sec_hdr_style))
            story.append(Spacer(1, 2))

            chk_items = [
                "[ ✓ ] 1. Okul binası, bahçe, kazan dairesi, elektrik ve su tesisatlarının emniyet kontrolleri yapıldı.",
                "[ ✓ ] 2. Nöbetçi öğretmenler görev yerlerine zamanında intikal ederek öğrenci gözetim ve güvenliğini sağladı.",
                "[ ✓ ] 3. Teneffüslerde koridor, bahçe ve lavabo temizlikleri ile genel okul düzeni denetlendi.",
                "[ ✓ ] 4. Günlük ders başlama ve bitiş vakit çizelgesine titizlikle riayet edildi."
            ]
            chk_data = [[Paragraph(item, item_chk_style)] for item in chk_items]
            t_chk = Table(chk_data, colWidths=[545])
            t_chk.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 0.5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0.5),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(t_chk)
            story.append(Spacer(1, 4))

            # BÖLÜM 4: OLAYLAR VE ALINAN TEDBİRLER (Not Kutusu)
            story.append(Paragraph("<b>IV. GÜNLÜK MEYDANA GELEN OLAYLAR VE ALINAN TEDBİRLER</b>", sec_hdr_style))
            story.append(Spacer(1, 2))

            note_content = custom_notes.strip() if custom_notes else (
                ".......................................................................................................................................................................................................\n\n"
                ".......................................................................................................................................................................................................\n\n"
                "......................................................................................................................................................................................................."
            )
            note_box = [[Paragraph(note_content.replace("\n", "<br/>"), note_text_style)]]
            t_notes = Table(note_box, colWidths=[545])
            t_notes.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#FAFAFA")),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(t_notes)
            story.append(Spacer(1, 7))

            # BÖLÜM 5: İMZA VE ONAY BLOĞU
            sign_data = [
                [
                    Paragraph("Nöbetçi Öğretmenler Adına<br/><br/><br/>İmza", sign_style),
                    Paragraph(f"Nöbetten Sorumlu Md. Yrd.<br/><b>{vp_name}</b><br/><br/>İmza", sign_style),
                    Paragraph(f"UYGUNDUR<br/><b>{school.principal_name}</b><br/>Okul Müdürü<br/>İmza", sign_style),
                ]
            ]
            t_sign = Table(sign_data, colWidths=[180, 185, 180])
            t_sign.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(t_sign)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.build(story)
        logger.info(f"Resmi Nöbet Defteri PDF çıktısı oluşturuldu: {output_path}")
        return output_path

    def export_monthly_kbs_duty_sheet(self, year: int, month: int, output_path: Path) -> Path:
        """
        Ay sonu öğretmenlerin fiili nöbet günlerini ve KBS sistemine girilecek
        3 saatlik nöbet ek ders tahakkukunu hesaplayıp resmi Excel (.xlsx) puantajı üretir.
        """
        import calendar
        wb = openpyxl.Workbook()
        ws = wb.active
        month_names = [
            "", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
            "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"
        ]
        month_name = month_names[month] if 1 <= month <= 12 else str(month)
        ws.title = f"Nöbet Puantaj {month_name}"
        ws.views.sheetView[0].showGridLines = True

        school = self.db.get_school_info()
        teachers = sorted(self.db.get_teachers(active_only=True), key=lambda x: x.name)
        num_days = calendar.monthrange(year, month)[1]

        # Gün Haritası
        day_id_map = {0: "monday", 1: "tuesday", 2: "wednesday", 3: "thursday", 4: "friday"}
        day_abbr_tr = {0: "Pzt", 1: "Sal", 2: "Çar", 3: "Per", 4: "Cum", 5: "Cmt", 6: "Paz"}

        # Haftalık atama önbelleği (week_start -> assignments)
        week_assignments_cache = {}

        for d in range(1, num_days + 1):
            c_date = datetime.date(year, month, d)
            w_day = c_date.weekday()
            w_monday = c_date - datetime.timedelta(days=w_day)
            w_start_str = w_monday.strftime("%Y-%m-%d")
            if w_start_str not in week_assignments_cache:
                week_assignments_cache[w_start_str] = self.db.get_assignments_for_week(w_start_str)

        # Stiller
        font_title = Font(name="Calibri", size=13, bold=True, color="1E3A8A")
        font_sub = Font(name="Calibri", size=11, bold=True, color="334155")
        font_desc = Font(name="Calibri", size=9, italic=True, color="64748B")
        font_hdr = Font(name="Calibri", size=9, bold=True, color="FFFFFF")
        font_subhdr = Font(name="Calibri", size=8, bold=True, color="475569")
        font_cell = Font(name="Calibri", size=9)
        font_duty = Font(name="Calibri", size=10, bold=True, color="15803D")
        font_total = Font(name="Calibri", size=9, bold=True, color="1E293B")

        fill_hdr = PatternFill("solid", fgColor="1E3A8A")
        fill_weekend = PatternFill("solid", fgColor="E2E8F0")
        fill_duty = PatternFill("solid", fgColor="DCFCE7")  # Hafif yeşil nöbet hücresi
        fill_zebra = PatternFill("solid", fgColor="F8FAFC")
        fill_total = PatternFill("solid", fgColor="FEF08A")  # Hafif sarı ek ders vurgusu

        thin_side = Side(style='thin', color='CBD5E1')
        thin_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
        double_bottom = Border(left=thin_side, right=thin_side, top=thin_side, bottom=Side(style='double', color='1E3A8A'))

        align_center = Alignment(horizontal="center", vertical="center")
        align_left = Alignment(horizontal="left", vertical="center")
        align_right = Alignment(horizontal="right", vertical="center")

        total_cols = 3 + num_days + 4  # Sıra, İsim, Branş + Günler + Nöbet Günü, Ek Ders Saati, KBS Kodu, İmza
        last_col_letter = get_column_letter(total_cols)

        # 1. Başlıklar
        ws.merge_cells(f"A1:{last_col_letter}1")
        ws["A1"] = f"T.C. {school.district.upper() if school.district else ''} {school.name.upper()} MÜDÜRLÜĞÜ"
        ws["A1"].font = font_title
        ws["A1"].alignment = align_center

        ws.merge_cells(f"A2:{last_col_letter}2")
        ws["A2"] = f"{month_name.upper()} {year} NÖBET GÖREVİ VE EK DERS PUANTAJ ÇİZELGESİ (KBS UYUMLU)"
        ws["A2"].font = font_sub
        ws["A2"].alignment = align_center

        ws.merge_cells(f"A3:{last_col_letter}3")
        ws["A3"] = "MEB Yönetici ve Öğretmenlerinin Ders ve Ek Ders Saatlerine İlişkin Karar (Md. 44/2) gereğince fiilen tutulan nöbet karşılığı haftalık 3 saat ek ders tahakkuku."
        ws["A3"].font = font_desc
        ws["A3"].alignment = align_center

        # 2. Tablo Başlık Satırı (Satır 5 ve 6)
        ws.row_dimensions[5].height = 20
        ws.row_dimensions[6].height = 18

        ws.merge_cells("A5:A6")
        ws["A5"] = "Sıra"
        ws.merge_cells("B5:B6")
        ws["B5"] = "Öğretmen Adı Soyadı"
        ws.merge_cells("C5:C6")
        ws["C5"] = "Branşı"

        for c_idx in [1, 2, 3]:
            cell = ws.cell(row=5, column=c_idx)
            cell.font = font_hdr
            cell.fill = fill_hdr
            cell.alignment = align_center
            cell.border = thin_border

        # Gün Sütunları
        for d in range(1, num_days + 1):
            col_idx = 3 + d
            c_date = datetime.date(year, month, d)
            w_day = c_date.weekday()
            is_wknd = w_day >= 5

            # Gün Sayısı
            cell_num = ws.cell(row=5, column=col_idx, value=d)
            cell_num.font = font_hdr
            cell_num.fill = PatternFill("solid", fgColor="475569") if is_wknd else fill_hdr
            cell_num.alignment = align_center
            cell_num.border = thin_border

            # Gün Adı
            cell_name = ws.cell(row=6, column=col_idx, value=day_abbr_tr[w_day])
            cell_name.font = font_subhdr
            cell_name.fill = fill_weekend if is_wknd else PatternFill("solid", fgColor="F1F5F9")
            cell_name.alignment = align_center
            cell_name.border = thin_border
            ws.column_dimensions[get_column_letter(col_idx)].width = 3.6

        # Sağ Toplam Sütunları
        c_tot_duty = 3 + num_days + 1
        c_tot_hrs = 3 + num_days + 2
        c_kbs = 3 + num_days + 3
        c_sign = 3 + num_days + 4

        ws.merge_cells(start_row=5, start_column=c_tot_duty, end_row=6, end_column=c_tot_duty)
        ws.cell(row=5, column=c_tot_duty, value="Fiili Nöbet\n(Gün)").alignment = align_center

        ws.merge_cells(start_row=5, start_column=c_tot_hrs, end_row=6, end_column=c_tot_hrs)
        ws.cell(row=5, column=c_tot_hrs, value="Ek Ders\n(x3 Saat)").alignment = align_center

        ws.merge_cells(start_row=5, start_column=c_kbs, end_row=6, end_column=c_kbs)
        ws.cell(row=5, column=c_kbs, value="KBS Nöbet\nKodu (110)").alignment = align_center

        ws.merge_cells(start_row=5, start_column=c_sign, end_row=6, end_column=c_sign)
        ws.cell(row=5, column=c_sign, value="Öğretmen\nİmzası").alignment = align_center

        for col_idx in [c_tot_duty, c_tot_hrs, c_kbs, c_sign]:
            cell = ws.cell(row=5, column=col_idx)
            cell.font = font_hdr
            cell.fill = fill_hdr
            cell.border = thin_border

        ws.column_dimensions["A"].width = 5
        ws.column_dimensions["B"].width = 24
        ws.column_dimensions["C"].width = 15
        ws.column_dimensions[get_column_letter(c_tot_duty)].width = 11
        ws.column_dimensions[get_column_letter(c_tot_hrs)].width = 12
        ws.column_dimensions[get_column_letter(c_kbs)].width = 12
        ws.column_dimensions[get_column_letter(c_sign)].width = 14

        # 3. Öğretmen Veri Satırları
        cur_row = 7
        for idx, t in enumerate(teachers, start=1):
            ws.row_dimensions[cur_row].height = 20
            row_fill = fill_zebra if idx % 2 == 0 else PatternFill(fill_type=None)

            c_idx_cell = ws.cell(row=cur_row, column=1, value=idx)
            c_idx_cell.font = font_cell
            c_idx_cell.alignment = align_center
            c_idx_cell.border = thin_border
            if row_fill.fill_type:
                c_idx_cell.fill = row_fill

            c_name_cell = ws.cell(row=cur_row, column=2, value=t.name)
            c_name_cell.font = font_cell
            c_name_cell.alignment = align_left
            c_name_cell.border = thin_border
            if row_fill.fill_type:
                c_name_cell.fill = row_fill

            c_br_cell = ws.cell(row=cur_row, column=3, value=t.branch or "-")
            c_br_cell.font = font_cell
            c_br_cell.alignment = align_left
            c_br_cell.border = thin_border
            if row_fill.fill_type:
                c_br_cell.fill = row_fill

            # Günlük Nöbet Kontrolleri
            first_day_col = 4
            last_day_col = 3 + num_days

            for d in range(1, num_days + 1):
                col_idx = 3 + d
                c_date = datetime.date(year, month, d)
                w_day = c_date.weekday()
                cell = ws.cell(row=cur_row, column=col_idx)
                cell.border = thin_border
                cell.alignment = align_center

                if w_day >= 5:  # Hafta sonu
                    cell.fill = fill_weekend
                    cell.value = ""
                else:
                    # Hafta içi: Nöbet kontrolü
                    w_monday = c_date - datetime.timedelta(days=w_day)
                    w_start_str = w_monday.strftime("%Y-%m-%d")
                    day_id = day_id_map.get(w_day, "monday")
                    assignments = week_assignments_cache.get(w_start_str, [])

                    has_duty = any(a.teacher_id == t.id and a.day_id == day_id for a in assignments)
                    if has_duty:
                        cell.value = "N"
                        cell.font = font_duty
                        cell.fill = fill_duty
                    else:
                        cell.value = ""
                        if row_fill.fill_type:
                            cell.fill = row_fill

            # Formüller
            first_let = get_column_letter(first_day_col)
            last_let = get_column_letter(last_day_col)

            # Fiili Nöbet Gün Sayısı: =COUNTIF(D7:AH7, "N")
            cell_tot = ws.cell(row=cur_row, column=c_tot_duty)
            cell_tot.value = f'=COUNTIF({first_let}{cur_row}:{last_let}{cur_row}, "N")'
            cell_tot.font = font_total
            cell_tot.alignment = align_center
            cell_tot.border = thin_border
            cell_tot.fill = fill_zebra

            # Ek Ders Saati (Haftalık Nöbet x 3 Saat):
            # Fiilen tutulan her nöbet günü haftalık 3 saat ek ders olarak değerlendirilir
            tot_let = get_column_letter(c_tot_duty)
            cell_hrs = ws.cell(row=cur_row, column=c_tot_hrs)
            cell_hrs.value = f'={tot_let}{cur_row}*3'
            cell_hrs.font = font_total
            cell_hrs.alignment = align_center
            cell_hrs.border = thin_border
            cell_hrs.fill = fill_total

            # KBS Kodu (Sabit 110 Nöbet Ücreti)
            cell_kbs = ws.cell(row=cur_row, column=c_kbs, value="110")
            cell_kbs.font = font_cell
            cell_kbs.alignment = align_center
            cell_kbs.border = thin_border

            # İmza hücresi boş
            cell_sign = ws.cell(row=cur_row, column=c_sign, value="")
            cell_sign.border = thin_border

            cur_row += 1

        # 4. Genel Toplam Satırı
        ws.row_dimensions[cur_row].height = 22
        ws.merge_cells(f"A{cur_row}:C{cur_row}")
        c_lbl = ws.cell(row=cur_row, column=1, value="GENEL TOPLAM")
        c_lbl.font = font_total
        c_lbl.alignment = align_right
        c_lbl.fill = PatternFill("solid", fgColor="E2E8F0")
        c_lbl.border = double_bottom

        for c in range(1, total_cols + 1):
            ws.cell(row=cur_row, column=c).border = double_bottom
            ws.cell(row=cur_row, column=c).fill = PatternFill("solid", fgColor="E2E8F0")

        # Toplam Nöbet ve Saat Formülleri
        start_r = 7
        end_r = cur_row - 1
        tot_duty_let = get_column_letter(c_tot_duty)
        tot_hrs_let = get_column_letter(c_tot_hrs)

        cell_sum_duty = ws.cell(row=cur_row, column=c_tot_duty, value=f"=SUM({tot_duty_let}{start_r}:{tot_duty_let}{end_r})")
        cell_sum_duty.font = font_total
        cell_sum_duty.alignment = align_center

        cell_sum_hrs = ws.cell(row=cur_row, column=c_tot_hrs, value=f"=SUM({tot_hrs_let}{start_r}:{tot_hrs_let}{end_r})")
        cell_sum_hrs.font = font_total
        cell_sum_hrs.alignment = align_center

        # 5. İmza ve Onay Blokları
        cur_row += 3
        ws.merge_cells(f"B{cur_row}:E{cur_row}")
        ws.merge_cells(f"{get_column_letter(c_tot_duty - 2)}{cur_row}:{last_col_letter}{cur_row}")

        ws[f"B{cur_row}"] = "DÜZENLEYEN\nNöbetten Sorumlu Müdür Yardımcısı\n\n\nİmza"
        ws[f"B{cur_row}"].font = font_cell
        ws[f"B{cur_row}"].alignment = align_center

        principal_name = school.principal_name or "Okul Müdürü"
        ws[f"{get_column_letter(c_tot_duty - 2)}{cur_row}"] = f"UYGUNDUR\n{principal_name}\nOkul Müdürü\n\n\nİmza - Mühür"
        ws[f"{get_column_letter(c_tot_duty - 2)}{cur_row}"].font = font_cell
        ws[f"{get_column_letter(c_tot_duty - 2)}{cur_row}"].alignment = align_center

        output_path.parent.mkdir(parents=True, exist_ok=True)
        wb.save(output_path)
        logger.info(f"Aylık KBS Nöbet Puantaj Excel çıktısı oluşturuldu: {output_path}")
        return output_path


