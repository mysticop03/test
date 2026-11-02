param(
    [string]$HtmlPath = "c:\Users\gamin\OneDrive\Desktop\projects\tills\md\System_Checker_1Pager.html",
    [string]$PdfPath = "c:\Users\gamin\OneDrive\Desktop\projects\tills\System_Checker_1Pager.pdf"
)

$tempDir = Join-Path $env:TEMP ("edge_p_" + [System.Guid]::NewGuid().ToString("N"))
$edge = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'

$args = @(
    '--headless=new',
    '--disable-gpu',
    '--no-sandbox',
    '--no-pdf-header-footer',
    "--user-data-dir=$tempDir",
    "--print-to-pdf=$PdfPath",
    "file:///$($HtmlPath.Replace('\', '/'))"
)

$proc = Start-Process -FilePath $edge -ArgumentList $args -Wait -PassThru
Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue

if (Test-Path $PdfPath) {
    Copy-Item -Force $PdfPath "c:\Users\gamin\OneDrive\Desktop\projects\tills\md\System_Checker_1Pager.pdf"
    Copy-Item -Force $PdfPath "c:\Users\gamin\OneDrive\Desktop\projects\tills\System_Checker_Overview.pdf"
    Copy-Item -Force $PdfPath "c:\Users\gamin\OneDrive\Desktop\projects\tills\Enterprise_POS_Auditor_Executive_Brief.pdf"
    Get-Item $PdfPath | Select-Object Name, Length, LastWriteTime
} else {
    Write-Error "PDF generation failed. ExitCode: $($proc.ExitCode)"
}

