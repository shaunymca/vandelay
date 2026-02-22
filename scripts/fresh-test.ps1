# fresh-test.ps1 — Reset Vandelay to a clean first-run state for testing.
#
# What this does:
#   1. Kills any running Vandelay server (by PID file or port 8000)
#   2. Kills any Python processes holding ~/.vandelay open
#   3. Deletes ~/.vandelay  (config, DB, workspace, logs, cron jobs, etc.)
#   4. Clears Python __pycache__ from the repo
#   5. Does NOT touch git state — your code changes are preserved.
#
# Usage (from the repo root):
#   .\scripts\fresh-test.ps1

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

$VandelayHome = Join-Path $env:USERPROFILE ".vandelay"
$PidFile      = Join-Path $VandelayHome "vandelay.pid"

Write-Host ""
Write-Host "=== Vandelay Fresh Test Reset ===" -ForegroundColor Cyan
Write-Host ""

# ── 1. Kill by PID file ────────────────────────────────────────────────────

Write-Host "Stopping any running Vandelay server..." -ForegroundColor Yellow

if (Test-Path $PidFile) {
    $pidVal = Get-Content $PidFile -ErrorAction SilentlyContinue
    if ($pidVal -match '^\d+$') {
        $proc = Get-Process -Id $pidVal -ErrorAction SilentlyContinue
        if ($proc) {
            Stop-Process -Id $pidVal -Force -ErrorAction SilentlyContinue
            Write-Host "  Killed PID $pidVal ($($proc.ProcessName))" -ForegroundColor Green
        }
    }
}

# ── 2. Kill by port 8000 ───────────────────────────────────────────────────

$netstat = netstat -ano 2>$null | Select-String ":8000\s.*LISTENING"
if ($netstat) {
    $portPid = ($netstat -split '\s+')[-1]
    if ($portPid -match '^\d+$') {
        taskkill /PID $portPid /F 2>$null | Out-Null
        Write-Host "  Killed PID $portPid on port 8000" -ForegroundColor Green
    }
}

# ── 3. Kill any Python processes with .vandelay in their path ─────────────

$pythonProcs = Get-WmiObject Win32_Process -Filter "Name LIKE '%python%'" -ErrorAction SilentlyContinue
$vandelayKills = 0
foreach ($p in $pythonProcs) {
    $cmd = $p.CommandLine
    if ($cmd -and ($cmd -match "vandelay" -or $cmd -match "\.vandelay")) {
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        $vandelayKills++
    }
}
if ($vandelayKills -gt 0) {
    Write-Host "  Killed $vandelayKills vandelay Python process(es)" -ForegroundColor Green
} else {
    Write-Host "  No extra Python processes found." -ForegroundColor DarkGray
}

# Give OS time to release file handles
Start-Sleep -Seconds 1

# ── 4. Delete ~/.vandelay ──────────────────────────────────────────────────

Write-Host ""
Write-Host "Removing ~/.vandelay..." -ForegroundColor Yellow

if (Test-Path $VandelayHome) {
    # Try PowerShell first, fall back to cmd rmdir which is more aggressive
    try {
        Remove-Item -Recurse -Force $VandelayHome -ErrorAction Stop
        Write-Host "  Deleted $VandelayHome" -ForegroundColor Green
    } catch {
        Write-Host "  Remove-Item failed, trying cmd rmdir..." -ForegroundColor Yellow
        cmd /c "rmdir /s /q `"$VandelayHome`"" 2>$null
        if (-not (Test-Path $VandelayHome)) {
            Write-Host "  Deleted $VandelayHome" -ForegroundColor Green
        } else {
            Write-Host "  WARNING: Could not fully remove $VandelayHome" -ForegroundColor Red
            Write-Host "  Close any terminals/editors that may have it open and retry." -ForegroundColor Red
        }
    }
} else {
    Write-Host "  Already clean (not found)." -ForegroundColor DarkGray
}

# ── 5. Clear Python cache ──────────────────────────────────────────────────

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
