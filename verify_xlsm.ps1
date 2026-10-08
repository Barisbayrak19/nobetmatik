$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false

try {
    $wb = $excel.Workbooks.Open("C:\Users\SKACO-02\Desktop\Ogrenci_Veritabani.xlsm")
    Write-Host "Workbook opened successfully."
    
    foreach ($comp in $wb.VBProject.VBComponents) {
        Write-Host "Component: $($comp.Name), Type: $($comp.Type), Lines: $($comp.CodeModule.CountOfLines)"
        if ($comp.CodeModule.CountOfLines -gt 0) {
            $preview = $comp.CodeModule.Lines(1, [Math]::Min(4, $comp.CodeModule.CountOfLines))
            Write-Host "Preview:`n$preview"
        }
    }
    
    $ws = $wb.Sheets.Item(3)
    Write-Host "Sheet 3: $($ws.Name), CodeName: $($ws.CodeName), Shapes: $($ws.Shapes.Count)"
    foreach ($shp in $ws.Shapes) {
        Write-Host "Shape: $($shp.Name) | Action: $($shp.OnAction) | Text: $($shp.TextFrame.Characters().Text)"
    }
    
    # Test SatiriSecKaldir
    $ws.Activate()
    $ws.Range("B8").Select()
    $excel.Run("SatiriSecKaldir")
    Write-Host "After SatiriSecKaldir on B8, G8 value: '$($ws.Range('G8').Value2)'"
    
    $excel.Run("SatiriSecKaldir")
    Write-Host "After toggle SatiriSecKaldir on B8, G8 value: '$($ws.Range('G8').Value2)'"
    
    # Test TumSinifiSec and SecimleriTemizle
    $excel.Run("TumSinifiSec")
    Write-Host "After TumSinifiSec, G8 value: '$($ws.Range('G8').Value2)'"
    
    $excel.Run("SecimleriTemizle")
    Write-Host "After SecimleriTemizle, G8 value: '$($ws.Range('G8').Value2)'"
    
    $wb.Close($false)
    Write-Host "Verification completed successfully."
} catch {
    Write-Host "Error: $($_.Exception.Message)"
} finally {
    $excel.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null
}
