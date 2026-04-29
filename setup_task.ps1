# setup_task.ps1
# Registers ftp_sync as a daily Windows Task Scheduler job.
# Run once from an elevated (Administrator) PowerShell session.
#
# Usage:
#   .\setup_task.ps1 -ProjectDir "C:\ftp_sync" -RunAt "06:00" -Env "prod"
#
# Parameters:
#   -ProjectDir  Full path to the ftp_sync project directory.
#   -RunAt       Daily start time in HH:MM (24-hour). Default: 06:00.
#   -Env         Environment passed to main.py (dev | prod). Default: prod.

param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectDir,

    [string]$RunAt = "06:00",

    [ValidateSet("dev", "prod")]
    [string]$Env = "prod"
)

$TaskName    = "ftp_sync_daily"
$PythonExe   = Join-Path $ProjectDir ".venv\Scripts\python.exe"
$MainScript  = Join-Path $ProjectDir "main.py"
$Arguments   = "main.py --env $Env"

# ── Validate project directory ────────────────────────────────────────────────
if (-not (Test-Path $ProjectDir)) {
    Write-Error "ProjectDir not found: $ProjectDir"
    exit 1
}

if (-not (Test-Path $PythonExe)) {
    Write-Error "Virtual environment not found at $PythonExe. Run setup first (see README)."
    exit 1
}

# ── Build the scheduled task ──────────────────────────────────────────────────
$Action  = New-ScheduledTaskAction -Execute $PythonExe -Argument $Arguments -WorkingDirectory $ProjectDir
$Trigger = New-ScheduledTaskTrigger -Daily -At $RunAt
$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -RestartCount 2 `
    -RestartInterval (New-TimeSpan -Minutes 5) `
    -StartWhenAvailable

# ── Remove existing task if present, then register ───────────────────────────
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed existing task: $TaskName"
}

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -RunLevel Highest `
    -Description "Daily FTP sync — downloads new files from configured remote paths."

Write-Host ""
Write-Host "Task registered: $TaskName"
Write-Host "  Runs daily at : $RunAt"
Write-Host "  Environment   : $Env"
Write-Host "  Python        : $PythonExe"
Write-Host "  Working dir   : $ProjectDir"
Write-Host ""
Write-Host "To run immediately: Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "To remove:          Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
