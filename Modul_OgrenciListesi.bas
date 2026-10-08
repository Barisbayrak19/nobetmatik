Attribute VB_Name = "Modul_OgrenciListesi"
' ==============================================================
' OKUL ÖÐRENCÝ YÖNETÝMÝ & LÝSTE OLUÞTURUCU MAKROLARI
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
            MsgBox "Bu satýrda öðrenci kaydý bulunmuyor.", vbExclamation, "Öðrenci Yok"
        End If
    Else
        MsgBox "Lütfen sýnýf listesinden (8-45 satýrlarý arasý) bir öðrenciye týklayýnýz.", vbInformation, "Satýr Seçiniz"
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
        MsgBox "Lütfen sýnýf listesinden geçerli bir öðrenci satýrýna týklayýnýz.", vbExclamation, "Geçersiz Satýr"
        Exit Sub
    End If
    
    sNo = wsClass.Cells(rowIdx, 2).Value
    sName = wsClass.Cells(rowIdx, 3).Value
    sSurname = wsClass.Cells(rowIdx, 4).Value
    sClass = wsClass.Range("D3").Value
    
    If Trim(CStr(sNo)) = "" Or Trim(sName) = "" Then
        MsgBox "Bu satýrda öðrenci kaydý bulunmuyor.", vbExclamation, "Kayýt Yok"
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
        MsgBox "Özel Liste maksimum kapasiteye (300 öðrenci) ulaþtý!", vbCritical, "Liste Dolu"
        Exit Sub
    End If
    
    wsCustom.Cells(targetRow, 2).Value = sNo
    wsClass.Cells(rowIdx, 7).Value = "[X] SECILDI"
    
    MsgBox sName & " " & sSurname & " (" & sNo & ")" & vbCrLf & _
           "Sýnýf: " & sClass & vbCrLf & _
           "Özel Liste'ye baþarýyla eklendi!", vbInformation, "Öðrenci Eklendi"
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
        MsgBox "Lütfen önce sýnýf listesinden öðrenci seçiniz!" & vbCrLf & vbCrLf & _
               "Ýpucu: Öðrenci satýrýna ÇÝFT TIKLAYARAK seçim yapabilirsiniz.", _
               vbExclamation, "Öðrenci Seçilmedi"
        Exit Sub
    End If
    
    listName = InputBox("Oluþturmak istediðiniz yeni listenin adýný yazýnýz:" & vbCrLf & _
                        "(Örnek: Satranç Kulübü, Tiyatro Ekibi, Gezi Listesi, Deneme Sýnavý vb.)", _
                        "Yeni Liste Sayfasý Oluþtur", "Özel Öðrenci Listesi")
    
    listName = Trim(listName)
    If listName = "" Then Exit Sub
    
    cleanName = Replace(Replace(Replace(Replace(Replace(Replace(Replace(listName, "/", "-"), "", "-"), "?", ""), "*", ""), ":", "-"), "[", "("), "]", ")")
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
    wsNew.Range("A1").Value = "T.C. ÝZMÝR VALÝLÝÐÝ - TORBALI ÝLÇE MÝLLÎ EÐÝTÝM MÜDÜRLÜÐÜ"
    wsNew.Range("A1").Font.Name = "Segoe UI"
    wsNew.Range("A1").Font.Size = 10
    wsNew.Range("A1").Font.Bold = True
    wsNew.Range("A1").Font.Color = RGB(27, 54, 93)
    wsNew.Range("A1").HorizontalAlignment = -4108
    
    wsNew.Rows(2).RowHeight = 26
    wsNew.Range("A2:H2").Merge
    wsNew.Range("A2").Value = "Þehit Kadir Altuntaþ Cumhuriyet Ortaokulu Müdürlüðü"
    wsNew.Range("A2").Font.Name = "Segoe UI"
    wsNew.Range("A2").Font.Size = 12
    wsNew.Range("A2").Font.Bold = True
    wsNew.Range("A2").Font.Color = RGB(32, 84, 147)
    wsNew.Range("A2").HorizontalAlignment = -4108
    
    wsNew.Rows(3).RowHeight = 28
    wsNew.Range("A3:H3").Merge
    wsNew.Range("A3").Value = UCase(listName) & " LÝSTESÝ"
    wsNew.Range("A3").Font.Name = "Segoe UI"
    wsNew.Range("A3").Font.Size = 13
    wsNew.Range("A3").Font.Bold = True
    wsNew.Range("A3").Font.Color = RGB(255, 255, 255)
    wsNew.Range("A3:H3").Interior.Color = RGB(27, 54, 93)
    wsNew.Range("A3").HorizontalAlignment = -4108
    
    wsNew.Rows(4).RowHeight = 22
    wsNew.Range("A4:D4").Merge
    wsNew.Range("A4").Value = "Oluþturulma Tarihi: " & Format(Date, "dd.mm.yyyy")
    wsNew.Range("A4").Font.Name = "Segoe UI"
    wsNew.Range("A4").Font.Size = 9.5
    wsNew.Range("A4").Font.Italic = True
    wsNew.Range("A4:D4").Interior.Color = RGB(248, 250, 252)
    
    wsNew.Range("E4:H4").Merge
    wsNew.Range("E4").Value = "Toplam: " & selectedCount & " Öðrenci"
    wsNew.Range("E4").Font.Name = "Segoe UI"
    wsNew.Range("E4").Font.Size = 9.5
    wsNew.Range("E4").Font.Bold = True
    wsNew.Range("E4").HorizontalAlignment = -4152
    wsNew.Range("E4:H4").Interior.Color = RGB(248, 250, 252)
    
    Dim th(1 To 8) As String
    th(1) = "S.No"
    th(2) = "Öðrenci No"
    th(3) = "Adý"
    th(4) = "Soyadý"
    th(5) = "Adý Soyadý"
    th(6) = "Sýnýfý / Þubesi"
    th(7) = "Cinsiyeti"
    th(8) = "Sýnýf Rehber Öðretmeni"
    
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
    wsNew.Cells(newRow, 1).Value = "LÝSTE TOPLAMI"
    wsNew.Cells(newRow, 1).Font.Name = "Segoe UI"
    wsNew.Cells(newRow, 1).Font.Bold = True
    wsNew.Cells(newRow, 1).Font.Color = RGB(255, 255, 255)
    wsNew.Range(wsNew.Cells(newRow, 1), wsNew.Cells(newRow, 5)).Interior.Color = RGB(27, 54, 93)
    wsNew.Cells(newRow, 1).HorizontalAlignment = -4108
    
    wsNew.Cells(newRow, 6).Value = "Toplam: " & selectedCount & " Öðrenci"
    wsNew.Cells(newRow, 6).Font.Bold = True
    wsNew.Cells(newRow, 6).HorizontalAlignment = -4108
    wsNew.Cells(newRow, 6).Interior.Color = RGB(226, 232, 240)
    
    wsNew.Range(wsNew.Cells(newRow, 7), wsNew.Cells(newRow, 8)).Merge
    wsNew.Cells(newRow, 7).Formula = "=COUNTIF(G6:G" & (newRow - 1) & ", ""Kýz"") & "" Kýz  |  "" & COUNTIF(G6:G" & (newRow - 1) & ", ""Erkek"") & "" Erkek"""
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
    
    wsNew.Cells(newRow + 1, 2).Value = "Ýmza"
    wsNew.Cells(newRow + 1, 2).Font.Italic = True
    wsNew.Cells(newRow + 1, 2).HorizontalAlignment = -4108
    
    wsNew.Cells(newRow + 1, 7).Value = "Ýmza / Mühür"
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
    MsgBox "'" & finalName & "' sayfasý baþarýyla oluþturuldu ve " & selectedCount & " öðrenci eklendi!", vbInformation, "Yeni Liste Hazýr"
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
        MsgBox "Lütfen aktarmak için önce sýnýf listesinden öðrenci seçiniz!", vbExclamation, "Seçim Yapýlmadý"
        Exit Sub
    End If
    
    Call SecimleriTemizle
    wsCustom.Activate
    MsgBox addedCount & " öðrenci baþarýyla 'ÖZEL LÝSTE OLUÞTUR' sayfasýna eklendi!", vbInformation, "Özel Liste Güncellendi"
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
