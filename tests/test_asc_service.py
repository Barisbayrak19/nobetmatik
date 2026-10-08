import unittest
import tempfile
from pathlib import Path
import openpyxl

from logic.asc_service import AscBilsaService

class TestAscBilsaService(unittest.TestCase):
    def setUp(self):
        self.service = AscBilsaService()
        self.temp_dir = Path(tempfile.mkdtemp())

    def test_parse_asc_xml(self):
        sample_xml = """<?xml version="1.0" encoding="utf-8"?>
<timetable ascttversion="2024.1.1" importtype="database">
   <periods>
      <period name="1" short="1" period="1" starttime="08:30" endtime="09:10"/>
      <period name="2" short="2" period="2" starttime="09:20" endtime="10:00"/>
   </periods>
   <daysdefs>
      <daysdef id="1" name="Pazartesi" short="Pzt" days="10000"/>
      <daysdef id="2" name="Salı" short="Sal" days="01000"/>
   </daysdefs>
   <teachers>
      <teacher id="T1" name="Ahmet YILMAZ" short="AY" gender="M"/>
      <teacher id="T2" name="Zeynep KAYA" short="ZK" gender="F"/>
   </teachers>
   <classes>
      <class id="C1" name="9-A" short="9A"/>
      <class id="C2" name="10-B" short="10B"/>
   </classes>
   <subjects>
      <subject id="S1" name="Matematik" short="MAT"/>
      <subject id="S2" name="Fizik" short="FİZ"/>
   </subjects>
   <lessons>
      <lesson id="L1" teacherids="T1" subjectid="S1" classids="C1"/>
      <lesson id="L2" teacherids="T2" subjectid="S2" classids="C2"/>
   </lessons>
   <cards>
      <card lessonid="L1" period="1" day="10000"/>
      <card lessonid="L1" period="2" day="10000"/>
      <card lessonid="L2" period="1" day="01000"/>
   </cards>
</timetable>"""
        xml_file = self.temp_dir / "sample_asc.xml"
        xml_file.write_text(sample_xml, encoding="utf-8")

        result = self.service.parse_asc_xml(str(xml_file))
        self.assertEqual(len(result["teachers"]), 2)
        self.assertEqual(len(result["lessons"]), 3)

        # Kontrol: Ahmet YILMAZ branşı Matematik
        ahmet = next(t for t in result["teachers"] if "Ahmet" in t["name"])
        self.assertEqual(ahmet["branch"], "Matematik")

        # Kontrol: Pazartesi 1. saat Ahmet YILMAZ 9-A
        les1 = result["lessons"][0]
        self.assertEqual(les1.day_name, "Pazartesi")
        self.assertEqual(les1.period, 1)
        self.assertEqual(les1.class_name, "9-A")
        self.assertEqual(les1.temp_teacher_name, "Ahmet YILMAZ")

    def test_parse_matrix_excel(self):
        wb = openpyxl.Workbook()
        ws = wb.active
        # Row 1: Günler
        ws.append(["Öğretmen", "Pazartesi", "Pazartesi", "Salı", "Salı"])
        # Row 2: Saatler
        ws.append(["Saat", "1", "2", "1", "2"])
        # Row 3: Öğretmen dersleri
        ws.append(["Mehmet Can", "9A MAT", "9A MAT", "10B FIZ", ""])

        excel_file = self.temp_dir / "sample_matrix.xlsx"
        wb.save(excel_file)

        result = self.service.parse_asc_bilsa_excel(str(excel_file))
        self.assertEqual(len(result["teachers"]), 1)
        self.assertEqual(len(result["lessons"]), 3)
        self.assertEqual(result["lessons"][0].day_name, "Pazartesi")
        self.assertEqual(result["lessons"][0].period, 1)

if __name__ == "__main__":
    unittest.main()
