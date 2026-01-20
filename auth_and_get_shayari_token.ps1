Write-Host "Step 1: Removing old Shayari token..." -ForegroundColor Cyan
Remove-Item token_shayari.pickle -Force -ErrorAction SilentlyContinue

Write-Host "Step 2: Starting Authentication... (Please login in the browser)" -ForegroundColor Cyan
# Run the reset script for shayari
python reset_youtube_auth.py shayari

if (Test-Path token_shayari.pickle) {
    Write-Host "Step 3: Encoding Token..." -ForegroundColor Cyan
    $b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes("token_shayari.pickle"))
    
    Write-Host "`n------------------------------------------------------------" -ForegroundColor Green
    Write-Host "SUCCESS! Here is your SHAYARI_TOKEN_PICKLE_BASE64:" -ForegroundColor Green
    Write-Host "------------------------------------------------------------`n"
    Write-Host $b64
    Write-Host "`n------------------------------------------------------------" -ForegroundColor Green
    
    try {
        Set-Clipboard $b64
        Write-Host "(I've also copied this long string to your clipboard!)" -ForegroundColor Yellow
    } catch {
        Write-Host "(Failed to copy to clipboard, but you can copy it manually from above)" -ForegroundColor Gray
    }
    
    Write-Host "Now go to GitHub -> Settings -> Secrets -> Actions -> SHAYARI_TOKEN_PICKLE_BASE64 and update it." -ForegroundColor Yellow
} else {
    Write-Host "Error: Token file was not created. Did you login?" -ForegroundColor Red
}
