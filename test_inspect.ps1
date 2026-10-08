$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false

try {
    $wb = $excel.Workbooks.Open("C:\Users\SKACO-02\Desktop\Ogrenci_Veritabani.xlsm")
    $comp = $wb.VBProject.VBComponents.Item("Sayfa3")
    Write-Host "Total lines in Sayfa3: $($comp.CodeModule.CountOfLines)"
    for ($i = 1; $i -le $comp.CodeModule.CountOfLines; $i++) {
        Write-Host "L$i : $($comp.CodeModule.Lines($i, 1))"
    }
    
    $mod = $wb.VBProject.VBComponents.Item("Modul_OgrenciListesi")
    Write-Host "Total lines in Modul_OgrenciListesi: $($mod.CodeModule.CountOfLines)"
    
    $wb.Close($false)
} finally {
    $excel.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null
}
