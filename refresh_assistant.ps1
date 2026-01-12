# PowerShell script to help refresh and encode YouTube tokens

function Get-TokenBase64 {
    param([string]$File)
    if (Test-Path $File) {
        return [Convert]::ToBase64String([IO.File]::ReadAllBytes($File))
    }
    return $null
}

Write-Host "--- YouTube Token Refresh Assistant ---" -ForegroundColor Cyan

$tokens = @(
    @{ Name = "Epic Stories (Default)"; File = "token.pickle"; Secret = "TOKEN_PICKLE_BASE64"; Script = "scripts/epicstories/daily_quote_video.py" },
    @{ Name = "Hindi Shayari"; File = "token_shayari.pickle"; Secret = "SHAYARI_TOKEN_PICKLE_BASE64"; Script = "scripts/shayari/daily_shayari_video.py" },
    @{ Name = "God Is Greatest"; File = "token_godisgreatest.pickle"; Secret = "GODISGREATEST_TOKEN_PICKLE_BASE64"; Script = "scripts/godisgreatest/daily_god_message_video.py" },
    @{ Name = "Viral Courses"; File = "token_viral_courses.pickle"; Secret = "VIRAL_COURSES_TOKEN_PICKLE_BASE64"; Script = "scripts/viralcourses/viral_courses_fast.py" }
)

foreach ($t in $tokens) {
    Write-Host "`nChecking $($t.Name)..." -ForegroundColor Yellow
    
    # Try to load and check if valid (simplified)
    # We'll just run the reset script for the one the user wants
    Write-Host "Path: $($t.File)"
    if (Test-Path $t.File) {
        Write-Host "Status: Token exists." -ForegroundColor Green
    } else {
        Write-Host "Status: Token MISSING." -ForegroundColor Red
    }
}

Write-Host "`nTo refresh a token, run: python reset_youtube_auth.py [name]" -ForegroundColor Cyan
Write-Host "Example: python reset_youtube_auth.py shayari" -ForegroundColor Gray

Write-Host "`nTo generate Base64 for a token, run: python update_github_token.py [file]" -ForegroundColor Cyan
Write-Host "Example: python update_github_token.py token_shayari.pickle" -ForegroundColor Gray
