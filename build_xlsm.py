import os
import subprocess
import sys

# Step 1: Run build_database.py
print("Step 1: Running build_database.py to create base XLSX...")
res = subprocess.run([sys.executable, "build_database.py"], capture_output=True, text=True)
if res.returncode != 0:
    print("Error running build_database.py:")
    print(res.stderr)
    sys.exit(1)
print(res.stdout.strip())

# Step 2: Prepare VBA Code for Standard Module
standard_vba = '''Attribute VB_Name = "Modul_OgrenciListesi"
' ==============================================================
' OKUL ÖĞRENCİ YÖNETİMİ & LİSTE OLUŞTURUCU MAKROLARI
' ==============================================================

Function GetClassSheet() As Worksheet
    Dim ws As Worksheet
    For Each ws In ThisWorkbook.Worksheets
        If InStr(1, ws.Name, "SINIF", vbTextCompare) > 0 Then
            Set GetClassSheet = ws
            Exit Function
        End If
    Next ws
    On Error Resume Next
    Set GetClassSheet = Sayfa3
End Function

Function GetCustomSheet() As Worksheet
    Dim ws As Worksheet
    For Each ws In ThisWorkbook.Worksheets
        If InStr(1, ws.Name, "ZEL", vbTextCompare) > 0 Or InStr(1, ws.Name, "OZEL", vbTextCompare) > 0 Then
            Set GetCustomSheet = ws
            Exit Function
        End If
    Next ws
    On Error Resume Next
    Set GetCustomSheet = Sayfa2
End Function

Sub SatiriSecKaldir()
    Dim wsClass As Worksheet
    Dim r As Long
    Set wsClass = GetClassSheet()
    r = ActiveCell.Row
    If r >= 8 And r <= 45 Then
        If Trim(CStr(wsClass.Cells(r, 2).Value)) <> "" Then
            If Trim(CStr(wsClass.Cells(r, 7).Value)) = "" Then
                wsClass.Cells(r, 7).Value = "[X] SECILDI"
            Else
                wsClass.Cells(r, 7).Value = ""
            End If
        Else
            MsgBox "Bu satırda öğrenci kaydı bulunmuyor.", vbExclamation, "Öğrenci Yok"
        End If
    Else
        MsgBox "Lütfen sınıf listesinden (8-45 satırları arası) bir öğrenciye tıklayınız.", vbInformation, "Satır Seçiniz"
    End If
End Sub

Sub OgrenciyiOzelListeyeEkle(Optional rowIdx As Long = 0)
    Dim wsClass As Worksheet
    Dim wsCustom As Worksheet
    Dim targetRow As Long
    Dim sNo As Variant
    Dim sName As String, sSurname As String, sClass As String
    
    Set wsClass = GetClassSheet()
    Set wsCustom = GetCustomSheet()
    
    If rowIdx = 0 Then rowIdx = ActiveCell.Row
    
    If rowIdx < 8 Or rowIdx > 45 Then
        MsgBox "Lütfen sınıf listesinden geçerli bir öğrenci satırına tıklayınız.", vbExclamation, "Geçersiz Satır"
        Exit Sub
    End If
    
    sNo = wsClass.Cells(rowIdx, 2).Value
    sName = wsClass.Cells(rowIdx, 3).Value
    sSurname = wsClass.Cells(rowIdx, 4).Value
    sClass = wsClass.Range("D3").Value
    
    If Trim(CStr(sNo)) = "" Or Trim(sName) = "" Then
        MsgBox "Bu satırda öğrenci kaydı bulunmuyor.", vbExclamation, "Kayıt Yok"
        Exit Sub
    End If
    
    targetRow = 4
    Do While wsCustom.Cells(targetRow, 2).Value <> "" And targetRow <= 300
        If CStr(wsCustom.Cells(targetRow, 2).Value) = CStr(sNo) Or _
           UCase(Trim(wsCustom.Cells(targetRow, 2).Value)) = UCase(Trim(sName & " " & sSurname)) Then
            MsgBox sName & " " & sSurname & " (" & sNo & ") zaten Özel Liste'de mevcut!", vbInformation, "Zaten Ekli"
            Exit Sub
        End If
        targetRow = targetRow + 1
    Loop
    
    If targetRow > 300 Then
        MsgBox "Özel Liste maksimum kapasiteye (300 öğrenci) ulaştı!", vbCritical, "Liste Dolu"
        Exit Sub
    End If
    
    wsCustom.Cells(targetRow, 2).Value = sNo
    wsClass.Cells(rowIdx, 7).Value = "[X] SECILDI"
    
    MsgBox sName & " " & sSurname & " (" & sNo & ")" & vbCrLf & _
           "Sınıf: " & sClass & vbCrLf & _
           "Özel Liste'ye başarıyla eklendi!", vbInformation, "Öğrenci Eklendi"
End Sub

Sub SecilenlerleYeniListeSayfasiOlustur()
    Dim wsClass As Worksheet
    Dim wsNew As Worksheet
    Dim r As Long
    Dim selectedCount As Long
    Dim listName As String
    Dim cleanName As String
    Dim newRow As Long
    Dim sNo As Variant, sName As String, sSurname As String, sGender As String, sRole As String, sClass As String, sTeacher As String
    Dim checkIndices() As Long
    Dim i As Long, colIdx As Long
    
    Set wsClass = GetClassSheet()
    sClass = wsClass.Range("D3").Value
    sTeacher = wsClass.Range("B5").Value
    
    selectedCount = 0
    ReDim checkIndices(1 To 50)
    
    For r = 8 To 45
        If wsClass.Cells(r, 2).Value <> "" Then
            If Trim(CStr(wsClass.Cells(r, 7).Value)) <> "" Then
                selectedCount = selectedCount + 1
                checkIndices(selectedCount) = r
            End If
        End If
    Next r
    
    If selectedCount = 0 Then
        If ActiveCell.Row >= 8 And ActiveCell.Row <= 45 And wsClass.Cells(ActiveCell.Row, 2).Value <> "" Then
            selectedCount = 1
            checkIndices(1) = ActiveCell.Row
        End If
    End If
    
    If selectedCount = 0 Then
        MsgBox "Lütfen önce sınıf listesinden öğrenci seçiniz!" & vbCrLf & vbCrLf & _
               "İpucu: Öğrenci satırına ÇİFT TIKLAYARAK seçim yapabilirsiniz.", _
               vbExclamation, "Öğrenci Seçilmedi"
        Exit Sub
    End If
    
    listName = InputBox("Oluşturmak istediğiniz yeni listenin adını yazınız:" & vbCrLf & _
                        "(Örnek: Satranç Kulübü, Tiyatro Ekibi, Gezi Listesi, Deneme Sınavı vb.)", _
                        "Yeni Liste Sayfası Oluştur", "Özel Öğrenci Listesi")
    
    listName = Trim(listName)
    If listName = "" Then Exit Sub
    
    cleanName = Replace(Replace(Replace(Replace(Replace(Replace(Replace(listName, "/", "-"), "\", "-"), "?", ""), "*", ""), ":", "-"), "[", "("), "]", ")")
    If Len(cleanName) > 28 Then cleanName = Left(cleanName, 28)
    
    Dim sheetExists As Boolean
    Dim suffix As Long
    Dim finalName As String
    finalName = cleanName
    suffix = 2
    Do
        sheetExists = False
        Dim wsTest As Worksheet
        For Each wsTest In ThisWorkbook.Worksheets
            If UCase(wsTest.Name) = UCase(finalName) Then
                sheetExists = True
                finalName = Left(cleanName, 24) & " (" & suffix & ")"
                suffix = suffix + 1
                Exit For
            End If
        Next wsTest
    Loop While sheetExists
    
    Set wsNew = ThisWorkbook.Sheets.Add(After:=ThisWorkbook.Sheets(ThisWorkbook.Sheets.Count))
    wsNew.Name = finalName
    wsNew.Tab.Color = RGB(0, 120, 212)
    
    wsNew.Columns("A").ColumnWidth = 7
    wsNew.Columns("B").ColumnWidth = 14
    wsNew.Columns("C").ColumnWidth = 20
    wsNew.Columns("D").ColumnWidth = 18
    wsNew.Columns("E").ColumnWidth = 24
    wsNew.Columns("F").ColumnWidth = 22
    wsNew.Columns("G").ColumnWidth = 12
    wsNew.Columns("H").ColumnWidth = 24
    
    wsNew.Rows(1).RowHeight = 24
    wsNew.Range("A1:H1").Merge
    wsNew.Range("A1").Value = "T.C. İZMİR VALİLİĞİ - TORBALI İLÇE MİLLÎ EĞİTİM MÜDÜRLÜĞÜ"
    wsNew.Range("A1").Font.Name = "Segoe UI"
    wsNew.Range("A1").Font.Size = 10
    wsNew.Range("A1").Font.Bold = True
    wsNew.Range("A1").Font.Color = RGB(27, 54, 93)
    wsNew.Range("A1").HorizontalAlignment = -4108
    
    wsNew.Rows(2).RowHeight = 26
    wsNew.Range("A2:H2").Merge
    wsNew.Range("A2").Value = "Örnek Ortaokulu Müdürlüğü"
    wsNew.Range("A2").Font.Name = "Segoe UI"
    wsNew.Range("A2").Font.Size = 12
    wsNew.Range("A2").Font.Bold = True
    wsNew.Range("A2").Font.Color = RGB(32, 84, 147)
    wsNew.Range("A2").HorizontalAlignment = -4108
    
    wsNew.Rows(3).RowHeight = 28
    wsNew.Range("A3:H3").Merge
    wsNew.Range("A3").Value = UCase(listName) & " LİSTESİ"
    wsNew.Range("A3").Font.Name = "Segoe UI"
    wsNew.Range("A3").Font.Size = 13
    wsNew.Range("A3").Font.Bold = True
    wsNew.Range("A3").Font.Color = RGB(255, 255, 255)
    wsNew.Range("A3:H3").Interior.Color = RGB(27, 54, 93)
    wsNew.Range("A3").HorizontalAlignment = -4108
    
    wsNew.Rows(4).RowHeight = 22
    wsNew.Range("A4:D4").Merge
    wsNew.Range("A4").Value = "Oluşturulma Tarihi: " & Format(Date, "dd.mm.yyyy")
    wsNew.Range("A4").Font.Name = "Segoe UI"
    wsNew.Range("A4").Font.Size = 9.5
    wsNew.Range("A4").Font.Italic = True
    wsNew.Range("A4:D4").Interior.Color = RGB(248, 250, 252)
    
    wsNew.Range("E4:H4").Merge
    wsNew.Range("E4").Value = "Toplam: " & selectedCount & " Öğrenci"
    wsNew.Range("E4").Font.Name = "Segoe UI"
    wsNew.Range("E4").Font.Size = 9.5
    wsNew.Range("E4").Font.Bold = True
    wsNew.Range("E4").HorizontalAlignment = -4152
    wsNew.Range("E4:H4").Interior.Color = RGB(248, 250, 252)
    
    Dim th(1 To 8) As String
    th(1) = "S.No"
    th(2) = "Öğrenci No"
    th(3) = "Adı"
    th(4) = "Soyadı"
    th(5) = "Adı Soyadı"
    th(6) = "Sınıfı / Şubesi"
    th(7) = "Cinsiyeti"
    th(8) = "Sınıf Rehber Öğretmeni"
    
    wsNew.Rows(5).RowHeight = 24
    For i = 1 To 8
        wsNew.Cells(5, i).Value = th(i)
        wsNew.Cells(5, i).Font.Name = "Segoe UI"
        wsNew.Cells(5, i).Font.Size = 10
        wsNew.Cells(5, i).Font.Bold = True
        wsNew.Cells(5, i).Font.Color = RGB(255, 255, 255)
        wsNew.Cells(5, i).Interior.Color = RGB(32, 84, 147)
        wsNew.Cells(5, i).HorizontalAlignment = -4108
        wsNew.Cells(5, i).Borders.Weight = 2
    Next i
    
    newRow = 6
    For i = 1 To selectedCount
        r = checkIndices(i)
        sNo = wsClass.Cells(r, 2).Value
        sName = wsClass.Cells(r, 3).Value
        sSurname = wsClass.Cells(r, 4).Value
        sGender = wsClass.Cells(r, 5).Value
        sRole = wsClass.Cells(r, 6).Value
        
        wsNew.Rows(newRow).RowHeight = 20
        wsNew.Cells(newRow, 1).Value = i
        wsNew.Cells(newRow, 2).Value = sNo
        wsNew.Cells(newRow, 3).Value = sName
        wsNew.Cells(newRow, 4).Value = sSurname
        wsNew.Cells(newRow, 5).Value = sName & " " & sSurname
        wsNew.Cells(newRow, 6).Value = sClass
        wsNew.Cells(newRow, 7).Value = sGender
        wsNew.Cells(newRow, 8).Value = sTeacher
        
        wsNew.Cells(newRow, 1).HorizontalAlignment = -4108
        wsNew.Cells(newRow, 2).HorizontalAlignment = -4108
        wsNew.Cells(newRow, 2).Font.Bold = True
        wsNew.Cells(newRow, 7).HorizontalAlignment = -4108
        wsNew.Cells(newRow, 5).Font.Bold = True
        
        For colIdx = 1 To 8
            wsNew.Cells(newRow, colIdx).Font.Name = "Segoe UI"
            wsNew.Cells(newRow, colIdx).Font.Size = 9.5
            wsNew.Cells(newRow, colIdx).Borders.Weight = 2
            If newRow Mod 2 = 1 Then
                wsNew.Cells(newRow, colIdx).Interior.Color = RGB(248, 250, 252)
            End If
        Next colIdx
        
        newRow = newRow + 1
    Next i
    
    wsNew.Rows(newRow).RowHeight = 24
    wsNew.Range(wsNew.Cells(newRow, 1), wsNew.Cells(newRow, 5)).Merge
    wsNew.Cells(newRow, 1).Value = "LİSTE TOPLAMI"
    wsNew.Cells(newRow, 1).Font.Name = "Segoe UI"
    wsNew.Cells(newRow, 1).Font.Bold = True
    wsNew.Cells(newRow, 1).Font.Color = RGB(255, 255, 255)
    wsNew.Range(wsNew.Cells(newRow, 1), wsNew.Cells(newRow, 5)).Interior.Color = RGB(27, 54, 93)
    wsNew.Cells(newRow, 1).HorizontalAlignment = -4108
    
    wsNew.Cells(newRow, 6).Value = "Toplam: " & selectedCount & " Öğrenci"
    wsNew.Cells(newRow, 6).Font.Bold = True
    wsNew.Cells(newRow, 6).HorizontalAlignment = -4108
    wsNew.Cells(newRow, 6).Interior.Color = RGB(226, 232, 240)
    
    wsNew.Range(wsNew.Cells(newRow, 7), wsNew.Cells(newRow, 8)).Merge
    wsNew.Cells(newRow, 7).Formula = "=COUNTIF(G6:G" & (newRow - 1) & ", ""Kız"") & "" Kız  |  "" & COUNTIF(G6:G" & (newRow - 1) & ", ""Erkek"") & "" Erkek"""
    wsNew.Cells(newRow, 7).Font.Bold = True
    wsNew.Cells(newRow, 7).HorizontalAlignment = -4108
    wsNew.Range(wsNew.Cells(newRow, 7), wsNew.Cells(newRow, 8)).Interior.Color = RGB(226, 232, 240)
    
    For colIdx = 1 To 8
        wsNew.Cells(newRow, colIdx).Borders.Weight = 2
    Next colIdx
    
    newRow = newRow + 2
    wsNew.Cells(newRow, 2).Value = "Listeyi Düzenleyen"
    wsNew.Cells(newRow, 2).Font.Bold = True
    wsNew.Cells(newRow, 2).HorizontalAlignment = -4108
    
    wsNew.Cells(newRow, 7).Value = "Okul Müdürü"
    wsNew.Cells(newRow, 7).Font.Bold = True
    wsNew.Cells(newRow, 7).HorizontalAlignment = -4108
    
    wsNew.Cells(newRow + 1, 2).Value = "İmza"
    wsNew.Cells(newRow + 1, 2).Font.Italic = True
    wsNew.Cells(newRow + 1, 2).HorizontalAlignment = -4108
    
    wsNew.Cells(newRow + 1, 7).Value = "İmza / Mühür"
    wsNew.Cells(newRow + 1, 7).Font.Italic = True
    wsNew.Cells(newRow + 1, 7).HorizontalAlignment = -4108
    
    On Error Resume Next
    With wsNew.PageSetup
        .Orientation = 1
        .PaperSize = 9
        .Zoom = False
        .FitToPagesWide = 1
        .FitToPagesTall = 1
    End With
    On Error GoTo 0
    
    Call SecimleriTemizle
    wsNew.Activate
    MsgBox "'" & finalName & "' sayfası başarıyla oluşturuldu ve " & selectedCount & " öğrenci eklendi!", vbInformation, "Yeni Liste Hazır"
End Sub

Sub SecilenleriOzelListeyeAktar()
    Dim wsClass As Worksheet
    Dim wsCustom As Worksheet
    Dim r As Long
    Dim targetRow As Long
    Dim addedCount As Long
    Dim sNo As Variant, sName As String, sSurname As String
    
    Set wsClass = GetClassSheet()
    Set wsCustom = GetCustomSheet()
    
    addedCount = 0
    targetRow = 4
    
    For r = 8 To 45
        If wsClass.Cells(r, 2).Value <> "" Then
            If Trim(CStr(wsClass.Cells(r, 7).Value)) <> "" Then
                sNo = wsClass.Cells(r, 2).Value
                sName = wsClass.Cells(r, 3).Value
                sSurname = wsClass.Cells(r, 4).Value
                
                Do While wsCustom.Cells(targetRow, 2).Value <> "" And targetRow <= 300
                    targetRow = targetRow + 1
                Loop
                
                If targetRow <= 300 Then
                    wsCustom.Cells(targetRow, 2).Value = sNo
                    addedCount = addedCount + 1
                End If
            End If
        End If
    Next r
    
    If addedCount = 0 Then
        If ActiveCell.Row >= 8 And ActiveCell.Row <= 45 And wsClass.Cells(ActiveCell.Row, 2).Value <> "" Then
            Call OgrenciyiOzelListeyeEkle(ActiveCell.Row)
            Exit Sub
        End If
    End If
    
    If addedCount = 0 Then
        MsgBox "Lütfen aktarmak için önce sınıf listesinden öğrenci seçiniz!", vbExclamation, "Seçim Yapılmadı"
        Exit Sub
    End If
    
    Call SecimleriTemizle
    wsCustom.Activate
    MsgBox addedCount & " öğrenci başarıyla 'ÖZEL LİSTE OLUŞTUR' sayfasına eklendi!", vbInformation, "Özel Liste Güncellendi"
End Sub

Sub SecimleriTemizle()
    Dim wsClass As Worksheet
    Dim r As Long, c As Long
    Set wsClass = GetClassSheet()
    
    Application.ScreenUpdating = False
    Application.EnableEvents = False
    For r = 8 To 45
        wsClass.Cells(r, 7).Value = ""
        For c = 1 To 7
            If r Mod 2 = 1 Then
                wsClass.Cells(r, c).Interior.Color = RGB(248, 250, 252)
            Else
                wsClass.Cells(r, c).Interior.Color = RGB(255, 255, 255)
            End If
        Next c
    Next r
    Application.EnableEvents = True
    Application.ScreenUpdating = True
End Sub

Sub TumSinifiSec()
    Dim wsClass As Worksheet
    Dim r As Long, c As Long
    Set wsClass = GetClassSheet()
    
    Application.ScreenUpdating = False
    Application.EnableEvents = False
    For r = 8 To 45
        If Trim(CStr(wsClass.Cells(r, 2).Value)) <> "" Then
            wsClass.Cells(r, 7).Value = "[X] SECILDI"
            For c = 1 To 7
                wsClass.Cells(r, c).Interior.Color = RGB(220, 252, 231)
            Next c
        End If
    Next r
    Application.EnableEvents = True
    Application.ScreenUpdating = True
End Sub

Sub OzelListeyeGit()
    Dim wsCustom As Worksheet
    Set wsCustom = GetCustomSheet()
    wsCustom.Activate
End Sub
'''

# Step 3: Prepare Sheet Event Code
sheet_vba = '''
Private Sub Worksheet_BeforeDoubleClick(ByVal Target As Range, Cancel As Boolean)
    Dim r As Long
    r = Target.Row
    If r >= 8 And r <= 45 Then
        If Trim(CStr(Me.Cells(r, 2).Value)) <> "" Then
            Cancel = True
            If Trim(CStr(Me.Cells(r, 7).Value)) = "" Then
                Me.Cells(r, 7).Value = "[X] SECILDI"
            Else
                Me.Cells(r, 7).Value = ""
            End If
        End If
    End If
End Sub

Private Sub Worksheet_Change(ByVal Target As Range)
    On Error Resume Next
    If Not Intersect(Target, Me.Range("D3")) Is Nothing Then
        Call SecimleriTemizle
        Exit Sub
    End If
    
    Dim cell As Range, r As Long, c As Long
    If Not Intersect(Target, Me.Range("G8:G45")) Is Nothing Then
        Application.EnableEvents = False
        For Each cell In Intersect(Target, Me.Range("G8:G45"))
            r = cell.Row
            If Trim(CStr(cell.Value)) <> "" Then
                For c = 1 To 7
                    Me.Cells(r, c).Interior.Color = RGB(220, 252, 231)
                Next c
            Else
                For c = 1 To 7
                    If r Mod 2 = 1 Then
                        Me.Cells(r, c).Interior.Color = RGB(248, 250, 252)
                    Else
                        Me.Cells(r, c).Interior.Color = RGB(255, 255, 255)
                    End If
                Next c
            End If
        Next cell
        Application.EnableEvents = True
    End If
End Sub
'''

# Write VBA files in cp1254 (Turkish ANSI)
cur_dir = os.path.dirname(os.path.abspath(__file__))
mod_path = os.path.join(cur_dir, "Modul_OgrenciListesi.bas")
cls_path = os.path.join(cur_dir, "Sheet_Events.cls")

with open(mod_path, "w", encoding="cp1254", errors="replace") as f:
    f.write(standard_vba)

with open(cls_path, "w", encoding="cp1254", errors="replace") as f:
    f.write(sheet_vba)

print("VBA code files written with cp1254 encoding.")

# Step 4: Write PowerShell injection runner
ps_runner = f'''
$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false

try {{
    $srcPath = "C:\\Users\\SKACO-02\\Desktop\\Ogrenci_Veritabani.xlsx"
    $dstPath = "C:\\Users\\SKACO-02\\Desktop\\Ogrenci_Veritabani.xlsm"
    
    Write-Host "Opening $srcPath..."
    $wb = $excel.Workbooks.Open($srcPath)
    $vbProj = $wb.VBProject
    
    # 1. Add Standard Module via AddFromFile
    $mod = $vbProj.VBComponents.Import("{mod_path.replace(chr(92), chr(92)+chr(92))}")
    Write-Host "Imported standard module."
    
    # 2. Add Worksheet Events to Sayfa3
    $wsClass = $null
    foreach ($ws in $wb.Worksheets) {{
        if ($ws.Name -like "*SINIF*") {{
            $wsClass = $ws
            break
        }}
    }}
    if ($wsClass -eq $null) {{
        $wsClass = $wb.Worksheets.Item(3)
    }}
    
    $sheetComp = $vbProj.VBComponents.Item($wsClass.CodeName)
    $clsLines = [System.IO.File]::ReadAllText("{cls_path.replace(chr(92), chr(92)+chr(92))}", [System.Text.Encoding]::GetEncoding(1254))
    $sheetComp.CodeModule.AddFromString($clsLines)
    Write-Host "Added Worksheet_BeforeDoubleClick & Worksheet_Change to $($wsClass.Name)."
    
    # 3. Add visual buttons (Modern Rounded Pill Shapes - msoShapeRoundedRectangle = 5)
    $wsClass.Columns.Item(8).ColumnWidth = 20
    $wsClass.Columns.Item(9).ColumnWidth = 20
    
    # Shape 1: Yeni Liste Sayfasi Olustur (Soft Indigo / Blue Pill)
    $btn1 = $wsClass.Shapes.AddShape(5, 680, 48, 260, 34)
    $btn1.Adjustments.Item(1) = 0.25
    $btn1.Line.Visible = 0
    $btn1.TextFrame.Characters().Text = "📁 Seçilenlerle YENİ LİSTE Oluştur"
    $btn1.TextFrame.Characters().Font.Name = "Segoe UI"
    $btn1.TextFrame.Characters().Font.Size = 10
    $btn1.TextFrame.Characters().Font.Bold = $true
    $btn1.TextFrame.Characters().Font.Color = (216 * 65536 + 78 * 256 + 29)
    $btn1.Fill.ForeColor.RGB = (254 * 65536 + 234 * 256 + 219)
    $btn1.OnAction = "SecilenlerleYeniListeSayfasiOlustur"
    
    # Shape 2: Secilenleri Ozel Listeye Ekle (Soft Emerald Pill)
    $btn2 = $wsClass.Shapes.AddShape(5, 680, 88, 260, 32)
    $btn2.Adjustments.Item(1) = 0.25
    $btn2.Line.Visible = 0
    $btn2.TextFrame.Characters().Text = "➕ Seçilenleri Özel Listeye Ekle"
    $btn2.TextFrame.Characters().Font.Name = "Segoe UI"
    $btn2.TextFrame.Characters().Font.Size = 10
    $btn2.TextFrame.Characters().Font.Bold = $true
    $btn2.TextFrame.Characters().Font.Color = (87 * 65536 + 120 * 256 + 4)
    $btn2.Fill.ForeColor.RGB = (229 * 65536 + 250 * 256 + 209)
    $btn2.OnAction = "SecilenleriOzelListeyeAktar"
    
    # Shape 3: Bu Satiri Sec / Kaldir (Soft Sky Pill)
    $btn3a = $wsClass.Shapes.AddShape(5, 680, 126, 260, 26)
    $btn3a.Adjustments.Item(1) = 0.25
    $btn3a.Line.Visible = 0
    $btn3a.TextFrame.Characters().Text = "🎯 Tıkladığın Satırı Seç / Kaldır"
    $btn3a.TextFrame.Characters().Font.Name = "Segoe UI"
    $btn3a.TextFrame.Characters().Font.Size = 9.5
    $btn3a.TextFrame.Characters().Font.Bold = $true
    $btn3a.TextFrame.Characters().Font.Color = (42 * 65536 + 23 * 256 + 15)
    $btn3a.Fill.ForeColor.RGB = (240 * 65536 + 226 * 256 + 226)
    $btn3a.OnAction = "SatiriSecKaldir"
    
    # Shape 4: Tumunu Sec (Soft Slate Pill)
    $btn3 = $wsClass.Shapes.AddShape(5, 680, 158, 125, 26)
    $btn3.Adjustments.Item(1) = 0.25
    $btn3.Line.Visible = 0
    $btn3.TextFrame.Characters().Text = "✓ Tümünü Seç"
    $btn3.TextFrame.Characters().Font.Name = "Segoe UI"
    $btn3.TextFrame.Characters().Font.Size = 9.5
    $btn3.TextFrame.Characters().Font.Bold = $true
    $btn3.TextFrame.Characters().Font.Color = (216 * 65536 + 78 * 256 + 29)
    $btn3.Fill.ForeColor.RGB = (254 * 65536 + 234 * 256 + 219)
    $btn3.OnAction = "TumSinifiSec"
    
    # Shape 5: Secimleri Temizle (Soft Rose Pill)
    $btn4 = $wsClass.Shapes.AddShape(5, 815, 158, 125, 26)
    $btn4.Adjustments.Item(1) = 0.25
    $btn4.Line.Visible = 0
    $btn4.TextFrame.Characters().Text = "✕ Seçimi Kaldır"
    $btn4.TextFrame.Characters().Font.Name = "Segoe UI"
    $btn4.TextFrame.Characters().Font.Size = 9.5
    $btn4.TextFrame.Characters().Font.Bold = $true
    $btn4.TextFrame.Characters().Font.Color = (38 * 65536 + 38 * 256 + 220)
    $btn4.Fill.ForeColor.RGB = (226 * 65536 + 226 * 256 + 254)
    $btn4.OnAction = "SecimleriTemizle"
    
    # Shape 6: Ozel Listeye Git (Soft Neutral Pill)
    $btn5 = $wsClass.Shapes.AddShape(5, 680, 190, 260, 26)
    $btn5.Adjustments.Item(1) = 0.25
    $btn5.Line.Visible = 0
    $btn5.TextFrame.Characters().Text = "👁️ Özel Listeyi Görüntüle"
    $btn5.TextFrame.Characters().Font.Name = "Segoe UI"
    $btn5.TextFrame.Characters().Font.Size = 9.5
    $btn5.TextFrame.Characters().Font.Bold = $true
    $btn5.TextFrame.Characters().Font.Color = (42 * 65536 + 23 * 256 + 15)
    $btn5.Fill.ForeColor.RGB = (240 * 65536 + 226 * 256 + 226)
    $btn5.OnAction = "OzelListeyeGit"
    
    # Instructions Box
    $wsClass.Range("H12:I17").Merge()
    $instBox = $wsClass.Range("H12")
    $instBox.Value2 = "💡 NASIL KULLANILIR?`n`n1. Sınıf listesinde öğrenci satırına ÇİFT TIKLAYIN (satır otomatik yeşil olur).`n`n2. Veya 'Seçim' sütunundaki oka tıklayıp [X] SECILDI seçin.`n`n3. Ya da satıra bir kez tıklayıp üstteki '🎯 Tıkladığın Satırı Seç' butonuna basın!`n`n4. '📁 YENİ LİSTE Sayfası Oluştur' butonuna basarak liste adını yazın; yeni sayfa anında açılır!"
    $instBox.Font.Name = "Segoe UI"
    $instBox.Font.Size = 9
    $instBox.Font.Color = 0x334155
    $instBox.Interior.Color = (138 * 65536 + 240 * 256 + 254)
    $instBox.VerticalAlignment = -4160
    $instBox.WrapText = $true
    $instBox.Borders.Weight = 2
    
    Write-Host "Saving as $dstPath..."
    if (Test-Path "$dstPath") {{
        Remove-Item "$dstPath" -Force
        Write-Host "Existing destination file removed."
    }}
    $wb.SaveAs($dstPath, 52)
    $wb.Close($false)
    Write-Host "Success! Created $dstPath"
}} catch {{
    Write-Host "Error: $($_.Exception.Message)"
    exit 1
}} finally {{
    $excel.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null
}}
'''

ps_runner_path = os.path.join(cur_dir, "run_inject.ps1")
with open(ps_runner_path, "w", encoding="utf-8-sig") as f:
    f.write(ps_runner)

print("Running PowerShell injection...")
res2 = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", ps_runner_path], capture_output=True, text=True)
print("POWERSHELL OUTPUT:")
print(res2.stdout)
if res2.stderr:
    print("POWERSHELL ERROR:")
    print(res2.stderr)

if res2.returncode == 0:
    print("ALL DONE SUCCESSFULLY!")
else:
    print("FAILED with code:", res2.returncode)
