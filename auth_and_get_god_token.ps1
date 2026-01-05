Write-Host "Step 1: Removing old God Is Greatest token..." -ForegroundColor Cyan
Remove-Item token_godisgreatest.pickle -Force -ErrorAction SilentlyContinue

Write-Host "Step 2: Starting Authentication... (Please login in the browser)" -ForegroundColor Cyan
# Run the script to trigger auth
try {
    python scripts/godisgreatest/daily_god_message_video.py
} catch {
    Write-Host "Script had an error, but checking for token..." -ForegroundColor Yellow
}

if (Test-Path token_godisgreatest.pickle) {
    Write-Host "Step 3: Encoding Token..." -ForegroundColor Cyan
    $b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes("token_godisgreatest.pickle"))
    
    Write-Host "`n------------------------------------------------------------" -ForegroundColor Green
    Write-Host "SUCCESS! Here is your GODISGREATEST_TOKEN_PICKLE_BASE64:" -ForegroundColor Green
    Write-Host "------------------------------------------------------------`n"
    Write-Host $b64
    Write-Host "`n------------------------------------------------------------" -ForegroundColor Green
    
    Set-Clipboard $b64
    Write-Host "(I've also copied this long string to your clipboard!)" -ForegroundColor Yellow
    Write-Host "Now go to GitHub -> Settings -> Secrets -> GODISGREATEST_TOKEN_PICKLE_BASE64 and paste it." -ForegroundColor Yellow
} else {
    Write-Host "Error: Token file was not created. Did you login?" -ForegroundColor Red
}
