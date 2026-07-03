param(
  [switch]$Quiet,
  [int[]]$Ports = @(18000, 5173)
)

$ErrorActionPreference = "SilentlyContinue"

$Root = Split-Path -Parent $PSScriptRoot
$RunDir = Join-Path $Root ".run"
$PidFile = Join-Path $RunDir "processes.json"

function Stop-ProcessTree {
  param([int]$ProcessId)

  if ($ProcessId -le 0) {
    return
  }

  try {
    $children = Get-CimInstance Win32_Process -Filter "ParentProcessId=$ProcessId"
    foreach ($child in $children) {
      Stop-ProcessTree -ProcessId ([int]$child.ProcessId)
    }
  }
  catch {
    # Fall back to stopping the root when process tree inspection is denied.
  }

  $process = Get-Process -Id $ProcessId
  if ($process) {
    Stop-Process -Id $ProcessId -Force
  }
}

function Get-PortOwnerIds {
  param([int]$Port)

  $owners = @()
  $lines = netstat -ano | Select-String -Pattern "^\s*TCP\s+\S+:$Port\s+\S+\s+LISTENING\s+(\d+)\s*$"
  foreach ($line in $lines) {
    $match = [regex]::Match($line.Line, "LISTENING\s+(\d+)\s*$")
    if ($match.Success) {
      $owners += [int]$match.Groups[1].Value
    }
  }
  return @($owners | Sort-Object -Unique)
}

$stopped = $false

if (Test-Path -LiteralPath $PidFile) {
  $entries = Get-Content -LiteralPath $PidFile -Raw | ConvertFrom-Json
  foreach ($entry in @($entries)) {
    if (-not $Quiet) {
      Write-Host "[Imagen] Stopping $($entry.name) PID $($entry.pid)..."
    }
    Stop-ProcessTree -ProcessId ([int]$entry.pid)
    $stopped = $true
  }

  Remove-Item -LiteralPath $PidFile -Force
}

foreach ($port in $Ports) {
  foreach ($ownerPid in Get-PortOwnerIds -Port $port) {
    if (-not $Quiet) {
      Write-Host "[Imagen] Stopping process on port $port PID $ownerPid..."
    }
    Stop-ProcessTree -ProcessId $ownerPid
    $stopped = $true
  }
}

if (-not $Quiet) {
  if ($stopped) {
    Write-Host "[Imagen] Stopped managed processes and port listeners."
  }
  else {
    Write-Host "[Imagen] No managed PID file or project port listeners found."
  }
}
