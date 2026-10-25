# Smoke-test the hand-authored Windows GUI executable without elevating privileges.
# The C# helper is used only to inspect the Windows dialog; it is NOT part of CHA.exe.
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$archive = Join-Path $repo 'after-hours\assets\CHA_EXE_Im_Still_Here.zip'
$archiveExpected = 'd92f5ab08ab2a4c162279d1b054a215c8b8c9818c2c2398f1544d36c9c2e8dc4'
$binaryExpected = '0391cac84bd25c18505db7a4586e931f3ba8fd4967f8b28b6d17128d80f0c3b2'
if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $archiveExpected) {
  throw 'CHA.EXE ZIP checksum mismatch'
}
$destination = Join-Path $env:RUNNER_TEMP 'cha-exe-windows-smoke'
New-Item -Path $destination -ItemType Directory -Force | Out-Null
Expand-Archive -LiteralPath $archive -DestinationPath $destination -Force
$binary = Join-Path $destination 'CHA_EXE_machine_code\CHA.exe'
if ((Get-FileHash -LiteralPath $binary -Algorithm SHA256).Hash.ToLowerInvariant() -ne $binaryExpected) {
  throw 'CHA.exe checksum mismatch'
}
Write-Host 'PASS: ZIP and EXE checksums match the reviewed source.'

# Leave Windows Defender and SmartScreen enabled; scanning is best-effort only
# because GitHub-hosted runners may not have an active Defender engine.
$status = Get-MpComputerStatus -ErrorAction SilentlyContinue
if ($null -ne $status -and $status.AMServiceEnabled -and $status.AntivirusEnabled) {
  Start-MpScan -ScanType CustomScan -ScanPath $binary -ErrorAction Stop
  Write-Host 'PASS: Microsoft Defender custom scan completed.'
} else {
  Write-Warning 'Defender scan unavailable on this hosted runner. Local Windows scan is still recommended.'
}

Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class ChaWindow {
    [DllImport("user32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern IntPtr FindWindow(string className, string caption);
    [DllImport("user32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern IntPtr FindWindowEx(IntPtr parent, IntPtr childAfter, string className, string caption);
    [DllImport("user32.dll", SetLastError=true)]
    public static extern uint GetWindowThreadProcessId(IntPtr window, out uint processId);
    [DllImport("user32.dll", SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool PostMessage(IntPtr window, uint message, IntPtr wParam, IntPtr lParam);
}
'@

$process = Start-Process -FilePath $binary -PassThru
$dialog = [IntPtr]::Zero
try {
  for ($i=0; $i -lt 200; $i++) {
    $process.Refresh()
    if ($process.HasExited) {
      throw "CHA.exe terminated before showing its dialog (exit code $($process.ExitCode))"
    }
    $candidate = [ChaWindow]::FindWindow('#32770', 'CHA.EXE')
    if ($candidate -ne [IntPtr]::Zero) {
      [uint32] $ownerPid = 0
      [void][ChaWindow]::GetWindowThreadProcessId($candidate, [ref] $ownerPid)
      if ($ownerPid -eq [uint32] $process.Id) {
        $dialog = $candidate
        break
      }
    }
    Start-Sleep -Milliseconds 100
  }
  if ($dialog -eq [IntPtr]::Zero) {
    throw 'CHA.EXE dialog was not detected (headless runner or executable failure).'
  }
  $message = [ChaWindow]::FindWindowEx($dialog, [IntPtr]::Zero, 'Static', "I'M STILL HERE.")
  if ($message -eq [IntPtr]::Zero) {
    throw "Expected message text not found in CHA.EXE's Windows dialog."
  }
  Write-Host "PASS: An actual CHA.EXE dialog with only I'M STILL HERE. is visible."
  if (-not [ChaWindow]::PostMessage($dialog, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero)) {
    throw 'Unable to close the CHA.EXE dialog.'
  }
  if (-not $process.WaitForExit(10000)) {
    throw 'CHA.EXE did not exit within ten seconds after dialog closure.'
  }
  if ($process.ExitCode -ne 0) {
    throw "CHA.EXE returned non-zero exit code $($process.ExitCode)."
  }
  Write-Host 'PASS: CHA.EXE exits cleanly with code 0; no elevated privileges.'
} finally {
  $process.Refresh()
  if (-not $process.HasExited) {
    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
  }
  $process.Dispose()
}
