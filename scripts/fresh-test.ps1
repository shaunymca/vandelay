# fresh-test.ps1 — Reset Vandelay to a clean first-run state for testing.
#
# What this does:
#   1. Kills any running Vandelay server (by PID file or port 8000)
#   2. Deletes ~/.vandelay  (config, DB, workspace, logs, cron jobs, etc.)
#   3. Clears Python __pycache__ from the repo
#   4. Does NOT touch git state — your code changes are preserved.
#
# Usage (from the repo root):
#   .\scripts\fresh-test.ps1
#
# Then test with:
#   uv run vandelay

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$VandelayHome = Join-Path $env:USERPROFILE ".vandelay"
$PidFile      = Join-Path $VandelayHome "vandelay.pid"

Write-Host ""
Write-Host "=== Vandelay Fresh Test Reset ===" -ForegroundColor Cyan
Write-Host ""

# ── 1. Kill running server ─────────────────────────────────────────────────

Write-Host "Stopping any running Vandelay server..." -ForegroundColor Yellow

$killed = $false

# Try PID file first
if (Test-Path $PidFile) {
    $pid = Get-Content $PidFile -ErrorAction SilentlyContinue
    if ($pid -match '^\d+$') {
        $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if ($proc) {
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            Write-Host "  Killed PID $pid ($($proc.ProcessName))" -ForegroundColor Green
            $killed = $true
        }
    }
}

# Fall back to port 8000 scan
if (-not $killed) {
    $netstat = netstat -ano 2>$null | Select-String ":8000\s.*LISTENING"
    if ($netstat) {
        $pid = ($netstat -split '\s+')[-1]
        if ($pid -match '^\d+$') {
            $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
            taskkill /PID $pid /F 2>$null | Out-Null
            Write-Host "  Killed PID $pid on port 8000" -ForegroundColor Green
            $killed = $true
        }
    }
}

if (-not $killed) {
    Write-Host "  No running server found." -ForegroundColor DarkGray
}

# Brief pause to let the port release
Start-Sleep -Milliseconds 500

# ── 2. Delete ~/.vandelay ──────────────────────────────────────────────────

Write-Host ""
Write-Host "Removing ~/.vandelay..." -ForegroundColor Yellow

if (Test-Path $VandelayHome) {
    Remove-Item -Recurse -Force $VandelayHome
    Write-Host "  Deleted $VandelayHome" -ForegroundColor Green
} else {
    Write-Host "  Already clean (not found)." -ForegroundColor DarkGray
}

# ── 3. Clear Python cache ──────────────────────────────────────────────────

Write-Host ""
Write-Host "Clearing Python __pycache__..." -ForegroundColor Yellow

$cacheCount = 0
Get-ChildItem -Path $PSScriptRoot\.. -Recurse -Filter "__pycache__" -Directory `
    -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch "\\\.venv\\" } |
    ForEach-Object {
        Remove-Item -Recurse -Force $_.FullName -ErrorAction SilentlyContinue
        $cacheCount++
    }

Write-Host "  Cleared $cacheCount cache directories." -ForegroundColor Green

# ── Done ───────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "Ready for a fresh test!" -ForegroundColor Cyan
Write-Host "  Run:  uv run vandelay" -ForegroundColor White
Write-Host ""
