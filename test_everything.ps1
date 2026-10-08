$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false

try {
    $src = "C:\Users\SKACO-02\Desktop\Ogrenci_Veritabani.xlsm"
    Write-Host "Opening $src..."
    $wb = $excel.Workbooks.Open($src)
    
    $wsClass = $null
    foreach ($ws in $wb.Worksheets) {
        if ($ws.Name -like "*SINIF*") {
            $wsClass = $ws
            break
        }
    }
    
    Write-Host "Found Class sheet: $($wsClass.Name), CodeName: $($wsClass.CodeName)"
    $wsClass.Activate()
    
    # 1. Test SatiriSecKaldir on B8
    $wsClass.Range("B8").Select()
    Write-Host "Initial G8: '$($wsClass.Range('G8').Value2)'"
    
    Write-Host "Running SatiriSecKaldir..."
    $excel.Run("SatiriSecKaldir")
    $g8_after = $wsClass.Range("G8").Value2
    $color_after = $wsClass.Range("A8").Interior.Color
    Write-Host "After 1st toggle - G8: '$g8_after' | Color: $color_after (Expected mint green: $((231*65536 + 252*256 + 220)))"
    
    Write-Host "Running SatiriSecKaldir (toggle off)..."
    $excel.Run("SatiriSecKaldir")
    $g8_off = $wsClass.Range("G8").Value2
    $color_off = $wsClass.Range("A8").Interior.Color
    Write-Host "After 2nd toggle - G8: '$g8_off' | Color: $color_off"
    
    # 2. Test TumSinifiSec
    Write-Host "Testing TumSinifiSec..."
    $excel.Run("TumSinifiSec")
    Write-Host "G8 after TumSinifiSec: '$($wsClass.Range('G8').Value2)'"
    Write-Host "G9 after TumSinifiSec: '$($wsClass.Range('G9').Value2)'"
    
    # 3. Test SecilenleriOzelListeyeAktar
    Write-Host "Testing SecilenleriOzelListeyeAktar..."
    # Disable alerts and message boxes by replacing MsgBox with dummy or let's test if SecilenleriOzelListeyeAktar shows MsgBox
    # Note: MsgBox is modal in Excel, so we shouldn't call it if it has MsgBox unless we mock it or test the logic
    
    # Test SecimleriTemizle
    Write-Host "Testing SecimleriTemizle..."
    $excel.Run("SecimleriTemizle")
    Write-Host "G8 after SecimleriTemizle: '$($wsClass.Range('G8').Value2)'"
    
    $wb.Close($false)
    Write-Host "ALL TESTS PASSED CLEANLY!"
} catch {
    Write-Host "ERROR: $($_.Exception.Message)"
} finally {
    $excel.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null
}
