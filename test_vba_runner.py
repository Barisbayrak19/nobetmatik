import subprocess
import os

ps_script = '''
$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false

try {
    $wb = $excel.Workbooks.Open("C:\\Users\\SKACO-02\\Desktop\\Ogrenci_Veritabani.xlsm")
    $ws = $wb.Sheets.Item(3)
    Write-Host "CodeName: $($ws.CodeName), Name: $($ws.Name)"
    
    # Select cell B8
    $ws.Activate()
    $ws.Range("B8").Select()
    
    Write-Host "Running SatiriSecKaldir..."
    $excel.Run("SatiriSecKaldir")
    Write-Host "Success! Cell G8: '$($ws.Range('G8').Value2)'"
    
    $excel.Run("SatiriSecKaldir")
    Write-Host "Toggle off! Cell G8: '$($ws.Range('G8').Value2)'"
    
    $wb.Close($false)
    Write-Host "Done!"
} catch {
    Write-Host "Error: $($_.Exception.Message)"
} finally {
    $excel.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null
}
'''

with open("test_runner.ps1", "w", encoding="utf-8-sig") as f:
    f.write(ps_script)

res = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", "test_runner.ps1"], capture_output=True, text=True, timeout=10)
print("STDOUT:", res.stdout)
print("STDERR:", res.stderr)
