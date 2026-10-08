$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false

try {
    $srcPath = "C:\Users\SKACO-02\Desktop\Ogrenci_Veritabani.xlsx"
    $dstPath = "C:\Users\SKACO-02\Desktop\Ogrenci_Veritabani.xlsm"
    
    Write-Host "Opening $srcPath..."
    $wb = $excel.Workbooks.Open($srcPath)
    
    # 1. Add Standard Module with Macros
    $vbProj = $wb.VBProject
    $stdModule = $vbProj.VBComponents.Add(1)
    $stdModule.Name = "Modul_OgrenciListesi"
    
    $vbaCode = @'
' ==============================================================
' OKUL ÖĞRENCİ YÖNETİMİ & LİSTE OLUŞTURUCU MAKROLARI
' ==============================================================

Sub SatiriSecKaldir()
    Dim wsClass As Worksheet
    Dim r As Long
    Set wsClass = ThisWorkbook.Sheets("📄 SINIF LİSTESİ AL")
    r = ActiveCell.Row
    If r >= 8 And r <= 45 Then
        If Trim(CStr(wsClass.Cells(r, 2).Value)) <> "" Then
            If Trim(CStr(wsClass.Cells(r, 7).Value)) = "" Then
                wsClass.Cells(r, 7).Value = "[X] SEÇİLDİ"
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
    
    Set wsClass = ThisWorkbook.Sheets("📄 SINIF LİSTESİ AL")
    Set wsCustom = ThisWorkbook.Sheets("📝 ÖZEL LİSTE OLUŞTUR")
    
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
    wsClass.Cells(rowIdx, 7).Value = "[X] SEÇİLDİ"
    
    MsgBox "✅ " & sName & " " & sSurname & " (" & sNo & ")" & vbCrLf & _
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
    
    Set wsClass = ThisWorkbook.Sheets("📄 SINIF LİSTESİ AL")
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
               "💡 İpucu: Öğrenci satırına ÇİFT TIKLAYARAK seçim yapabilirsiniz.", _
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
    wsNew.Range("A2").Value = "Şehit Kadir Altuntaş Cumhuriyet Ortaokulu Müdürlüğü"
    wsNew.Range("A2").Font.Name = "Segoe UI"
    wsNew.Range("A2").Font.Size = 12
    wsNew.Range("A2").Font.Bold = True
    wsNew.Range("A2").Font.Color = RGB(32, 84, 147)
    wsNew.Range("A2").HorizontalAlignment = -4108
    
    wsNew.Rows(3).RowHeight = 28
    wsNew.Range("A3:H3").Merge
    wsNew.Range("A3").Value = "📋 " & UCase(listName) & " LİSTESİ"
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
    
    With wsNew.PageSetup
        .Orientation = 1
        .PaperSize = 9
        .Zoom = $false
        .FitToPagesWide = 1
        .FitToPagesTall = 1
    End With
    
    Call SecimleriTemizle
    wsNew.Activate
    MsgBox "🎉 '" & finalName & "' sayfası başarıyla oluşturuldu ve " & selectedCount & " öğrenci eklendi!", vbInformation, "Yeni Liste Hazır"
End Sub

Sub SecilenleriOzelListeyeAktar()
    Dim wsClass As Worksheet
    Dim wsCustom As Worksheet
    Dim r As Long
    Dim targetRow As Long
    Dim addedCount As Long
    Dim sNo As Variant, sName As String, sSurname As String
    
    Set wsClass = ThisWorkbook.Sheets("📄 SINIF LİSTESİ AL")
    Set wsCustom = ThisWorkbook.Sheets("📝 ÖZEL LİSTE OLUŞTUR")
    
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
    MsgBox "✅ " & addedCount & " öğrenci başarıyla '📝 ÖZEL LİSTE OLUŞTUR' sayfasına eklendi!", vbInformation, "Özel Liste Güncellendi"
End Sub

Sub SecimleriTemizle()
    Dim wsClass As Worksheet
    Dim r As Long
    Set wsClass = ThisWorkbook.Sheets("📄 SINIF LİSTESİ AL")
    
    For r = 8 To 45
        wsClass.Cells(r, 7).Value = ""
    Next r
End Sub

Sub TumSinifiSec()
    Dim wsClass As Worksheet
    Dim r As Long
    Set wsClass = ThisWorkbook.Sheets("📄 SINIF LİSTESİ AL")
    
    For r = 8 To 45
        If wsClass.Cells(r, 2).Value <> "" Then
            wsClass.Cells(r, 7).Value = "[X] SEÇİLDİ"
        End If
    Next r
End Sub

Sub OzelListeyeGit()
    ThisWorkbook.Sheets("📝 ÖZEL LİSTE OLUŞTUR").Activate
End Sub
'@
    $stdModule.CodeModule.AddFromString($vbaCode)
    Write-Host "Standard module Modul_OgrenciListesi added."
    
    # 2. Add Clean Worksheet_BeforeDoubleClick Event to "📄 SINIF LİSTESİ AL" (Sayfa3)
    $wsClass = $wb.Sheets.Item("📄 SINIF LİSTESİ AL")
    $wsCodeName = $wsClass.CodeName
    $sheetComp = $vbProj.VBComponents.Item($wsCodeName)
    
    $sheetEventCode = @'
Private Sub Worksheet_BeforeDoubleClick(ByVal Target As Range, Cancel As Boolean)
    Dim r As Long
    r = Target.Row
    If r >= 8 And r <= 45 Then
        If Trim(CStr(Me.Cells(r, 2).Value)) <> "" Then
            Cancel = True
            If Trim(CStr(Me.Cells(r, 7).Value)) = "" Then
                Me.Cells(r, 7).Value = "[X] SEÇİLDİ"
            Else
                Me.Cells(r, 7).Value = ""
            End If
        End If
    End If
End Sub
'@
    $sheetComp.CodeModule.AddFromString($sheetEventCode)
    Write-Host "Clean Worksheet_BeforeDoubleClick handler added to $($wsClass.Name)."
    
    # 3. Add Interactive Visual Macro Buttons to wsClass
    $wsClass.Columns.Item(8).ColumnWidth = 20
    $wsClass.Columns.Item(9).ColumnWidth = 20
    
    # Shape 1: Yeni Liste Sayfasi Olustur
    $btn1 = $wsClass.Shapes.AddShape(1, 680, 48, 260, 34)
    $btn1.TextFrame.Characters().Text = "📁 Seçilenlerle YENİ LİSTE Sayfası Oluştur"
    $btn1.TextFrame.Characters().Font.Name = "Segoe UI"
    $btn1.TextFrame.Characters().Font.Size = 10
    $btn1.TextFrame.Characters().Font.Bold = $true
    $btn1.TextFrame.Characters().Font.Color = 0xFFFFFF
    $btn1.Fill.ForeColor.RGB = (93 * 65536 + 54 * 256 + 27) # Navy
    $btn1.OnAction = "SecilenlerleYeniListeSayfasiOlustur"
    
    # Shape 2: Secilenleri Ozel Listeye Ekle
    $btn2 = $wsClass.Shapes.AddShape(1, 680, 88, 260, 32)
    $btn2.TextFrame.Characters().Text = "➕ Seçilenleri Özel Listeye Ekle"
    $btn2.TextFrame.Characters().Font.Name = "Segoe UI"
    $btn2.TextFrame.Characters().Font.Size = 10
    $btn2.TextFrame.Characters().Font.Bold = $true
    $btn2.TextFrame.Characters().Font.Color = 0xFFFFFF
    $btn2.Fill.ForeColor.RGB = (65 * 65536 + 124 * 256 + 16) # Green
    $btn2.OnAction = "SecilenleriOzelListeyeAktar"
    
    # Shape 3: Bu Satiri Sec / Kaldir (Alternative to double-click)
    $btn3a = $wsClass.Shapes.AddShape(1, 680, 126, 260, 26)
    $btn3a.TextFrame.Characters().Text = "🎯 Tıkladığın Satırı Seç / Kaldır"
    $btn3a.TextFrame.Characters().Font.Name = "Segoe UI"
    $btn3a.TextFrame.Characters().Font.Size = 9.5
    $btn3a.TextFrame.Characters().Font.Bold = $true
    $btn3a.TextFrame.Characters().Font.Color = 0xFFFFFF
    $btn3a.Fill.ForeColor.RGB = (147 * 65536 + 84 * 256 + 32) # Blue
    $btn3a.OnAction = "SatiriSecKaldir"
    
    # Shape 4: Tumunu Sec
    $btn3 = $wsClass.Shapes.AddShape(1, 680, 158, 125, 26)
    $btn3.TextFrame.Characters().Text = "✓ Tümünü Seç"
    $btn3.TextFrame.Characters().Font.Name = "Segoe UI"
    $btn3.TextFrame.Characters().Font.Size = 9.5
    $btn3.TextFrame.Characters().Font.Bold = $true
    $btn3.TextFrame.Characters().Font.Color = 0xFFFFFF
    $btn3.Fill.ForeColor.RGB = (147 * 65536 + 84 * 256 + 32) # Blue
    $btn3.OnAction = "TumSinifiSec"
    
    # Shape 5: Secimleri Temizle
    $btn4 = $wsClass.Shapes.AddShape(1, 815, 158, 125, 26)
    $btn4.TextFrame.Characters().Text = "✕ Seçimi Kaldır"
    $btn4.TextFrame.Characters().Font.Name = "Segoe UI"
    $btn4.TextFrame.Characters().Font.Size = 9.5
    $btn4.TextFrame.Characters().Font.Bold = $true
    $btn4.TextFrame.Characters().Font.Color = 0x334155
    $btn4.Fill.ForeColor.RGB = (240 * 65536 + 232 * 256 + 226) # Slate
    $btn4.OnAction = "SecimleriTemizle"
    
    # Shape 6: Ozel Listeye Git
    $btn5 = $wsClass.Shapes.AddShape(1, 680, 190, 260, 26)
    $btn5.TextFrame.Characters().Text = "👁️ Özel Listeyi Görüntüle"
    $btn5.TextFrame.Characters().Font.Name = "Segoe UI"
    $btn5.TextFrame.Characters().Font.Size = 9.5
    $btn5.TextFrame.Characters().Font.Bold = $true
    $btn5.TextFrame.Characters().Font.Color = 0xFFFFFF
    $btn5.Fill.ForeColor.RGB = (105 * 65536 + 85 * 256 + 71) # Gray
    $btn5.OnAction = "OzelListeyeGit"
    
    # Instructions Box right on the side
    $wsClass.Range("H12:I17").Merge()
    $instBox = $wsClass.Range("H12")
    $instBox.Value2 = "💡 NASIL KULLANILIR?`n`n1. Sınıf listesinde öğrenci satırına ÇİFT TIKLAYIN (satır otomatik yeşil olur).`n`n2. Veya 'Seçim' sütunundaki oka tıklayıp [X] SEÇİLDİ seçin.`n`n3. Ya da satıra bir kez tıklayıp üstteki '🎯 Tıkladığın Satırı Seç' butonuna basın!`n`n4. '📁 YENİ LİSTE Sayfası Oluştur' butonuna basarak liste adını yazın; yeni sayfa anında açılır!"
    $instBox.Font.Name = "Segoe UI"
    $instBox.Font.Size = 9
    $instBox.Font.Color = 0x334155
    $instBox.Interior.Color = (138 * 65536 + 240 * 256 + 254)
    $instBox.VerticalAlignment = -4160
    $instBox.WrapText = $true
    $instBox.Borders.Weight = 2
    
    Write-Host "Buttons and instruction boxes created successfully."
    
    # Save as .xlsm
    $wb.SaveAs($dstPath, 52)
    Write-Host "Saved successfully as $dstPath"
    
    $wb.Close($false)
    Write-Host "Workbook closed cleanly."
} catch {
    Write-Host "Error in script:" $_.Exception.Message
} finally {
    $excel.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null
}
