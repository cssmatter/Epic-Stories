Write-Host "Step 1: Removing old Quote token..." -ForegroundColor Cyan
Remove-Item token.pickle -Force -ErrorAction SilentlyContinue

Write-Host "Step 2: Starting Authentication... (Please login in the browser)" -ForegroundColor Cyan
# Run the script to trigger auth
try {
    python scripts/epicstories/daily_quote_video.py
} catch {
    Write-Host "Script had an error, but checking for token..." -ForegroundColor Yellow
}

if (Test-Path token.pickle) {
    Write-Host "Step 3: Encoding Token..." -ForegroundColor Cyan
    $b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes("token.pickle"))
    
    Write-Host "`n------------------------------------------------------------" -ForegroundColor Green
    Write-Host "SUCCESS! Here is your TOKEN_PICKLE_BASE64:" -ForegroundColor Green
    Write-Host "------------------------------------------------------------`n"
    Write-Host $b64
    Write-Host "`n------------------------------------------------------------" -ForegroundColor Green
    
    Set-Clipboard $b64
    Write-Host "(I've also copied this long string to your clipboard!)" -ForegroundColor Yellow
    Write-Host "Now go to GitHub -> Settings -> Secrets -> TOKEN_PICKLE_BASE64 and paste it." -ForegroundColor Yellow
} else {
    Write-Host "Error: Token file was not created. Did you login?" -ForegroundColor Red
}
