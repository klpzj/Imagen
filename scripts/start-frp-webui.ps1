param(
  [int]$BackendPort = 18000,
  [int]$FrontendPort = 5173,
  [string]$PublicUrl = "http://39.106.96.49:15173"
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$RunDir = Join-Path $Root ".run"
$PidFile = Join-Path $RunDir "processes.json"
$BackendOutLog = Join-Path $RunDir "backend.out.log"
$BackendErrLog = Join-Path $RunDir "backend.err.log"
$FrontendOutLog = Join-Path $RunDir "frontend.out.log"
$FrontendErrLog = Join-Path $RunDir "frontend.err.log"
$FrpcOutLog = Join-Path $RunDir "frpc.out.log"
$FrpcErrLog = Join-Path $RunDir "frpc.err.log"
$Processes = @()

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

public static class ImagenJobObject {
  [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
  public static extern IntPtr CreateJobObject(IntPtr lpJobAttributes, string lpName);

  [DllImport("kernel32.dll")]
  public static extern bool SetInformationJobObject(IntPtr hJob, int JobObjectInfoClass, IntPtr lpJobObjectInfo, uint cbJobObjectInfoLength);

  [DllImport("kernel32.dll")]
  public static extern bool AssignProcessToJobObject(IntPtr hJob, IntPtr hProcess);

  [DllImport("kernel32.dll")]
  public static extern bool CloseHandle(IntPtr hObject);

  [StructLayout(LayoutKind.Sequential)]
  public struct JOBOBJECT_BASIC_LIMIT_INFORMATION {
    public long PerProcessUserTimeLimit;
    public long PerJobUserTimeLimit;
    public uint LimitFlags;
    public UIntPtr MinimumWorkingSetSize;
    public UIntPtr MaximumWorkingSetSize;
    public uint ActiveProcessLimit;
    public long Affinity;
    public uint PriorityClass;
    public uint SchedulingClass;
  }

  [StructLayout(LayoutKind.Sequential)]
  public struct IO_COUNTERS {
    public ulong ReadOperationCount;
    public ulong WriteOperationCount;
    public ulong OtherOperationCount;
    public ulong ReadTransferCount;
    public ulong WriteTransferCount;
    public ulong OtherTransferCount;
  }

  [StructLayout(LayoutKind.Sequential)]
  public struct JOBOBJECT_EXTENDED_LIMIT_INFORMATION {
    public JOBOBJECT_BASIC_LIMIT_INFORMATION BasicLimitInformation;
    public IO_COUNTERS IoInfo;
    public UIntPtr ProcessMemoryLimit;
    public UIntPtr JobMemoryLimit;
    public UIntPtr PeakProcessMemoryUsed;
    public UIntPtr PeakJobMemoryUsed;
  }
}
"@

function New-KillOnCloseJob {
  $handle = [ImagenJobObject]::CreateJobObject([IntPtr]::Zero, "ImagenWebUI-$PID")
  if ($handle -eq [IntPtr]::Zero) {
    throw "Failed to create Windows job object."
  }

  $info = New-Object ImagenJobObject+JOBOBJECT_EXTENDED_LIMIT_INFORMATION
  $info.BasicLimitInformation.LimitFlags = 0x00002000
  $size = [Runtime.InteropServices.Marshal]::SizeOf($info)
  $ptr = [Runtime.InteropServices.Marshal]::AllocHGlobal($size)
  try {
    [Runtime.InteropServices.Marshal]::StructureToPtr($info, $ptr, $false)
    $ok = [ImagenJobObject]::SetInformationJobObject($handle, 9, $ptr, [uint32]$size)
    if (-not $ok) {
      throw "Failed to configure Windows job object."
    }
  }
  finally {
    [Runtime.InteropServices.Marshal]::FreeHGlobal($ptr)
  }

  return $handle
}

$JobHandle = New-KillOnCloseJob

function Assert-File {
  param(
    [string]$Path,
    [string]$Message
  )

  if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
    throw $Message
  }
}

function Stop-ProcessTree {
  param([int]$ProcessId)

  if ($ProcessId -le 0) {
    return
  }

  $children = Get-CimInstance Win32_Process -Filter "ParentProcessId=$ProcessId" -ErrorAction SilentlyContinue
  foreach ($child in $children) {
    Stop-ProcessTree -ProcessId ([int]$child.ProcessId)
  }

  $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
  if ($process) {
    Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
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

function Assert-PortFree {
  param(
    [int]$Port,
    [string]$Name
  )

  $owners = Get-PortOwnerIds -Port $Port
  if ($owners.Count -gt 0) {
    throw "$Name port $Port is already in use by PID(s): $($owners -join ', '). Run stop-frp-webui.bat or stop the occupying process."
  }
}

function Add-ProcessToJob {
  param([System.Diagnostics.Process]$Process)

  $ok = [ImagenJobObject]::AssignProcessToJobObject($JobHandle, $Process.Handle)
  if (-not $ok) {
    Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
    throw "Failed to attach $($Process.ProcessName) PID $($Process.Id) to lifecycle job."
  }
}

function Write-PidFile {
  $payload = $script:Processes | ForEach-Object {
    [ordered]@{
      name = $_.Name
      pid = $_.Process.Id
      started_at = $_.StartedAt
    }
  }

  $payload | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $PidFile -Encoding UTF8
}

function Start-ManagedProcess {
  param(
    [string]$Name,
    [string]$FilePath,
    [string]$ArgumentList,
    [string]$WorkingDirectory,
    [string]$OutLogPath,
    [string]$ErrLogPath
  )

  $process = Start-Process `
    -FilePath $FilePath `
    -ArgumentList $ArgumentList `
    -WorkingDirectory $WorkingDirectory `
    -RedirectStandardOutput $OutLogPath `
    -RedirectStandardError $ErrLogPath `
    -NoNewWindow `
    -PassThru

  Add-ProcessToJob -Process $process

  $script:Processes += [pscustomobject]@{
    Name = $Name
    Process = $process
    StartedAt = (Get-Date).ToString("s")
  }
  Write-PidFile
  Write-Host "[Imagen] $Name PID: $($process.Id)"
}

function Cleanup {
  Write-Host ""
  Write-Host "[Imagen] Stopping managed processes..."

  foreach ($entry in @($script:Processes | Sort-Object { $_.Process.Id } -Descending)) {
    Stop-ProcessTree -ProcessId $entry.Process.Id
  }

  if (Test-Path -LiteralPath $PidFile) {
    Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
  }

  if ($JobHandle -and $JobHandle -ne [IntPtr]::Zero) {
    [ImagenJobObject]::CloseHandle($JobHandle) | Out-Null
    $script:JobHandle = [IntPtr]::Zero
  }

  Write-Host "[Imagen] Stopped."
}

try {
  Set-Location -LiteralPath $Root
  New-Item -ItemType Directory -Force -Path $RunDir | Out-Null

  Assert-File -Path (Join-Path $Root "auth.json") -Message "Missing auth.json. Create it before starting the service."
  Assert-File -Path (Join-Path $Root "frpc.toml") -Message "Missing frpc.toml. Copy frpc.example.toml to frpc.toml and fill it in."
  Assert-File -Path (Join-Path $Root "frpc.exe") -Message "Missing frpc.exe. Put frpc.exe in the project root."

  if (-not (Test-Path -LiteralPath (Join-Path $Root "webui\node_modules") -PathType Container)) {
    Write-Host "[Imagen] Installing frontend dependencies..."
    Push-Location -LiteralPath (Join-Path $Root "webui")
    try {
      npm install
    }
    finally {
      Pop-Location
    }
  }

  if (Test-Path -LiteralPath $PidFile) {
    Write-Host "[Imagen] Existing PID file found. Cleaning stale managed processes..."
    & (Join-Path $PSScriptRoot "stop-frp-webui.ps1") -Quiet
  }

  Assert-PortFree -Port $BackendPort -Name "Backend"
  Assert-PortFree -Port $FrontendPort -Name "Frontend"

  Write-Host "[Imagen] Backend:  http://127.0.0.1:$BackendPort"
  Write-Host "[Imagen] Frontend: http://127.0.0.1:$FrontendPort"
  Write-Host "[Imagen] Public:   $PublicUrl"
  Write-Host "[Imagen] Logs:     $RunDir"
  Write-Host ""

  Start-ManagedProcess `
    -Name "backend" `
    -FilePath "python" `
    -ArgumentList "-m uvicorn backend.app:app --reload --host 127.0.0.1 --port $BackendPort" `
    -WorkingDirectory $Root `
    -OutLogPath $BackendOutLog `
    -ErrLogPath $BackendErrLog

  Start-Sleep -Seconds 2

  Start-ManagedProcess `
    -Name "frontend" `
    -FilePath "cmd.exe" `
    -ArgumentList "/c npm run dev -- --host 127.0.0.1 --port $FrontendPort --strictPort" `
    -WorkingDirectory (Join-Path $Root "webui") `
    -OutLogPath $FrontendOutLog `
    -ErrLogPath $FrontendErrLog

  Start-Sleep -Seconds 2

  Start-ManagedProcess `
    -Name "frpc" `
    -FilePath (Join-Path $Root "frpc.exe") `
    -ArgumentList "-c frpc.toml" `
    -WorkingDirectory $Root `
    -OutLogPath $FrpcOutLog `
    -ErrLogPath $FrpcErrLog

  Write-Host ""
  Write-Host "[Imagen] Started. Close this window or press Ctrl+C to stop all managed processes."
  Write-Host "[Imagen] Local:  http://127.0.0.1:$FrontendPort"
  Write-Host "[Imagen] Public: $PublicUrl"
  Write-Host ""

  while ($true) {
    foreach ($entry in @($script:Processes)) {
      if ($entry.Process.HasExited) {
        throw "$($entry.Name) exited with code $($entry.Process.ExitCode). See logs in $RunDir."
      }
    }
    Start-Sleep -Seconds 2
  }
}
finally {
  Cleanup
}
