$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false

try {
    $wb = $excel.Workbooks.Open("C:\Users\SKACO-02\Desktop\Ogrenci_Veritabani.xlsm")
    $ws = $wb.Sheets.Item(3)
    Write-Host "ws item 3 name: $($ws.Name)"
    
    # Try calling SatiriSecKaldir via Excel.Run
    $ws.Activate()
    $ws.Range("B8").Select()
    Write-Host "Calling SatiriSecKaldir..."
    $excel.Run("SatiriSecKaldir")
    Write-Host "Success! Cell G8: '$($ws.Range('G8').Value2)'"
    
    $wb.Close($false)
} catch {
    Write-Host "ERROR: $($_.Exception.Message)"
} finally {
    $excel.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null
}
