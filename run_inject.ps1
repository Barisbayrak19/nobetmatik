
$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false

try {
    $srcPath = "C:\Users\SKACO-02\Desktop\Ogrenci_Veritabani.xlsx"
    $dstPath = "C:\Users\SKACO-02\Desktop\Ogrenci_Veritabani.xlsm"
    
    Write-Host "Opening $srcPath..."
    $wb = $excel.Workbooks.Open($srcPath)
    $vbProj = $wb.VBProject
    
    # 1. Add Standard Module via AddFromFile
    $mod = $vbProj.VBComponents.Import("C:\\Users\\SKACO-02\\Desktop\\nobet\\Modul_OgrenciListesi.bas")
    Write-Host "Imported standard module."
    
    # 2. Add Worksheet Events to Sayfa3
    $wsClass = $null
    foreach ($ws in $wb.Worksheets) {
        if ($ws.Name -like "*SINIF*") {
            $wsClass = $ws
            break
        }
    }
    if ($wsClass -eq $null) {
        $wsClass = $wb.Worksheets.Item(3)
    }
    
    $sheetComp = $vbProj.VBComponents.Item($wsClass.CodeName)
    $clsLines = [System.IO.File]::ReadAllText("C:\\Users\\SKACO-02\\Desktop\\nobet\\Sheet_Events.cls", [System.Text.Encoding]::GetEncoding(1254))
    $sheetComp.CodeModule.AddFromString($clsLines)
    Write-Host "Added Worksheet_BeforeDoubleClick & Worksheet_Change to $($wsClass.Name)."
    
    # 3. Add visual buttons
    $wsClass.Columns.Item(8).ColumnWidth = 20
    $wsClass.Columns.Item(9).ColumnWidth = 20
    
    # Shape 1: Yeni Liste Sayfasi Olustur
    $btn1 = $wsClass.Shapes.AddShape(1, 680, 48, 260, 34)
    $btn1.TextFrame.Characters().Text = "📁 Seçilenlerle YENİ LİSTE Sayfası Oluştur"
    $btn1.TextFrame.Characters().Font.Name = "Segoe UI"
    $btn1.TextFrame.Characters().Font.Size = 10
    $btn1.TextFrame.Characters().Font.Bold = $true
    $btn1.TextFrame.Characters().Font.Color = 0xFFFFFF
    $btn1.Fill.ForeColor.RGB = (93 * 65536 + 54 * 256 + 27)
    $btn1.OnAction = "SecilenlerleYeniListeSayfasiOlustur"
    
    # Shape 2: Secilenleri Ozel Listeye Ekle
    $btn2 = $wsClass.Shapes.AddShape(1, 680, 88, 260, 32)
    $btn2.TextFrame.Characters().Text = "➕ Seçilenleri Özel Listeye Ekle"
    $btn2.TextFrame.Characters().Font.Name = "Segoe UI"
    $btn2.TextFrame.Characters().Font.Size = 10
    $btn2.TextFrame.Characters().Font.Bold = $true
    $btn2.TextFrame.Characters().Font.Color = 0xFFFFFF
    $btn2.Fill.ForeColor.RGB = (65 * 65536 + 124 * 256 + 16)
    $btn2.OnAction = "SecilenleriOzelListeyeAktar"
    
    # Shape 3: Bu Satiri Sec / Kaldir (Alternative to double-click)
    $btn3a = $wsClass.Shapes.AddShape(1, 680, 126, 260, 26)
    $btn3a.TextFrame.Characters().Text = "🎯 Tıkladığın Satırı Seç / Kaldır"
    $btn3a.TextFrame.Characters().Font.Name = "Segoe UI"
    $btn3a.TextFrame.Characters().Font.Size = 9.5
    $btn3a.TextFrame.Characters().Font.Bold = $true
    $btn3a.TextFrame.Characters().Font.Color = 0xFFFFFF
    $btn3a.Fill.ForeColor.RGB = (147 * 65536 + 84 * 256 + 32)
    $btn3a.OnAction = "SatiriSecKaldir"
    
    # Shape 4: Tumunu Sec
    $btn3 = $wsClass.Shapes.AddShape(1, 680, 158, 125, 26)
    $btn3.TextFrame.Characters().Text = "✓ Tümünü Seç"
    $btn3.TextFrame.Characters().Font.Name = "Segoe UI"
    $btn3.TextFrame.Characters().Font.Size = 9.5
    $btn3.TextFrame.Characters().Font.Bold = $true
    $btn3.TextFrame.Characters().Font.Color = 0xFFFFFF
    $btn3.Fill.ForeColor.RGB = (147 * 65536 + 84 * 256 + 32)
    $btn3.OnAction = "TumSinifiSec"
    
    # Shape 5: Secimleri Temizle
    $btn4 = $wsClass.Shapes.AddShape(1, 815, 158, 125, 26)
    $btn4.TextFrame.Characters().Text = "✕ Seçimi Kaldır"
    $btn4.TextFrame.Characters().Font.Name = "Segoe UI"
    $btn4.TextFrame.Characters().Font.Size = 9.5
    $btn4.TextFrame.Characters().Font.Bold = $true
    $btn4.TextFrame.Characters().Font.Color = 0x334155
    $btn4.Fill.ForeColor.RGB = (240 * 65536 + 232 * 256 + 226)
    $btn4.OnAction = "SecimleriTemizle"
    
    # Shape 6: Ozel Listeye Git
    $btn5 = $wsClass.Shapes.AddShape(1, 680, 190, 260, 26)
    $btn5.TextFrame.Characters().Text = "👁️ Özel Listeyi Görüntüle"
    $btn5.TextFrame.Characters().Font.Name = "Segoe UI"
    $btn5.TextFrame.Characters().Font.Size = 9.5
    $btn5.TextFrame.Characters().Font.Bold = $true
    $btn5.TextFrame.Characters().Font.Color = 0xFFFFFF
    $btn5.Fill.ForeColor.RGB = (105 * 65536 + 85 * 256 + 71)
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
    if (Test-Path "$dstPath") {
        Remove-Item "$dstPath" -Force
        Write-Host "Existing destination file removed."
    }
    $wb.SaveAs($dstPath, 52)
    $wb.Close($false)
    Write-Host "Success! Created $dstPath"
} catch {
    Write-Host "Error: $($_.Exception.Message)"
    exit 1
} finally {
    $excel.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null
}
