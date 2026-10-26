#requires -Version 5.1
<#
.SYNOPSIS
Verify the pinned CHA.EXE package. Execution is opt-in, including in CI.
.DESCRIPTION
No security settings are changed. Reports and extracted files are retained in a
unique directory. Dot-sourcing defines functions only, for offline regression tests.
#>
[CmdletBinding()]
param(
    [switch]$RunExecutable,
    [switch]$AllowUnavailableDefenderOnCI,
    [string]$ArchivePath = (Join-Path $PSScriptRoot '../after-hours/assets/CHA_EXE_Im_Still_Here.zip'),
    [string]$OutputDirectory,
    [ValidateRange(5, 300)][int]$ScanTimeoutSeconds = 120,
    [ValidateRange(1, 60)][int]$DialogTimeoutSeconds = 20
)

function Test-ChaHostedCI {
    return ($env:GITHUB_ACTIONS -eq 'true' -and
        $env:RUNNER_ENVIRONMENT -eq 'github-hosted' -and $env:RUNNER_OS -eq 'Windows')
}

function Get-ChaDefenderResult {
    param([string]$Binary, [int]$TimeoutSeconds)
    $result = [ordered]@{
        status = 'Unavailable'; scanCompleted = $false; detail = ''
        serviceEnabled = $null; antivirusEnabled = $null; realTimeProtectionEnabled = $null
        engineVersion = $null; signatureVersion = $null; signatureUpdatedUtc = $null
        detectionCount = 0; threatIds = @()
    }
    $job = $null
    try {
        foreach ($command in @('Get-MpComputerStatus', 'Start-MpScan', 'Get-MpThreatDetection')) {
            if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
                $result.detail = "Defender command unavailable: $command"
                return [pscustomobject]$result
            }
        }
        $status = Get-MpComputerStatus -ErrorAction Stop
        if ($null -eq $status) { throw 'Defender returned no status.' }
        $result.serviceEnabled = $status.AMServiceEnabled
        $result.antivirusEnabled = $status.AntivirusEnabled
        $result.realTimeProtectionEnabled = $status.RealTimeProtectionEnabled
        $result.engineVersion = [string]$status.AMEngineVersion
        $result.signatureVersion = [string]$status.AntivirusSignatureVersion
        if ($status.AntivirusSignatureLastUpdated) {
            $result.signatureUpdatedUtc = $status.AntivirusSignatureLastUpdated.ToUniversalTime().ToString('o')
        }
        if (-not $status.AMServiceEnabled -or -not $status.AntivirusEnabled) {
            $result.detail = 'Defender antivirus service/engine is not active.'
            return [pscustomobject]$result
        }
        $result.status = 'Error'
        $job = Start-MpScan -ScanType CustomScan -ScanPath $Binary -AsJob -ErrorAction Stop
        if ($null -eq $job) { throw 'Defender did not return a scan job.' }
        $completed = Wait-Job -Job $job -Timeout $TimeoutSeconds -ErrorAction Stop
        if ($null -eq $completed) { throw "Defender scan timed out after $TimeoutSeconds seconds." }
        Receive-Job -Job $job -ErrorAction Stop | Out-Null
        if ($job.State -ne 'Completed') { throw "Defender scan job ended in state $($job.State)." }
        $result.scanCompleted = $true
        # Scope the history to this unique extraction path. Do not log other threats.
        $detections = @(Get-MpThreatDetection -ErrorAction Stop | Where-Object {
            @($_.Resources | Where-Object {
                ([string]$_).IndexOf($Binary, [StringComparison]::OrdinalIgnoreCase) -ge 0
            }).Count -gt 0
        })
        $result.detectionCount = $detections.Count
        $result.threatIds = @($detections | ForEach-Object { [string]$_.ThreatID } | Select-Object -Unique)
        if ($detections.Count -gt 0) {
            $result.status = 'Detected'
            $result.detail = 'Defender reported a detection for this test binary; execution is blocked.'
        } else {
            $result.status = 'NoDetections'
            $result.detail = 'Custom scan completed; no matching detection was reported. This is not a safety guarantee.'
        }
    } catch {
        $result.status = 'Error'
        $result.detail = $_.Exception.Message
    } finally {
        if ($null -ne $job) {
            # Cancel only our PowerShell job on timeout; never stop the Defender service.
            if ($job.State -eq 'Running' -or $job.State -eq 'NotStarted') {
                Stop-Job -Job $job -ErrorAction SilentlyContinue
            }
            Remove-Job -Job $job -Force -ErrorAction SilentlyContinue
        }
    }
    return [pscustomobject]$result
}

function Invoke-ChaRuntimeCheck {
    param([string]$Binary, [int]$TimeoutSeconds, [System.Collections.IDictionary]$Result)
    if (-not ('ChaSmokeWindow' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class ChaSmokeWindow {
    private delegate bool EnumProc(IntPtr window, IntPtr param);
    [DllImport("user32.dll")] private static extern bool EnumWindows(EnumProc proc, IntPtr param);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] private static extern int GetClassName(IntPtr w, StringBuilder text, int count);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] private static extern int GetWindowText(IntPtr w, StringBuilder text, int count);
    [DllImport("user32.dll")] private static extern bool IsWindowVisible(IntPtr w);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr w, out uint pid);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern IntPtr FindWindowEx(IntPtr parent, IntPtr after, string cls, string text);
    [DllImport("user32.dll", SetLastError=true)] public static extern bool PostMessage(IntPtr w, uint msg, IntPtr wp, IntPtr lp);
    public static IntPtr FindDialog(uint processId) {
        IntPtr found = IntPtr.Zero;
        EnumWindows(delegate(IntPtr w, IntPtr p) {
            uint owner;
            GetWindowThreadProcessId(w, out owner);
            if (owner != processId || !IsWindowVisible(w)) return true;
            var cls = new StringBuilder(256);
            var title = new StringBuilder(256);
            GetClassName(w, cls, cls.Capacity);
            GetWindowText(w, title, title.Capacity);
            if (cls.ToString() == "#32770" && title.ToString() == "CHA.EXE") {
                found = w;
                return false;
            }
            return true;
        }, IntPtr.Zero);
        return found;
    }
}
'@
    }
    $process = $null
    try {
        # Use the normal Windows shell launch path. Do not suppress or accept warnings.
        $Result.status = 'Running'
        $process = Start-Process -FilePath $Binary -PassThru -ErrorAction Stop
        $Result.processId = $process.Id
        $timer = [Diagnostics.Stopwatch]::StartNew()
        $dialog = [IntPtr]::Zero
        while ($timer.Elapsed.TotalSeconds -lt $TimeoutSeconds) {
            $process.Refresh()
            if ($process.HasExited) {
                throw "CHA.EXE exited before its dialog was verified (exit $($process.ExitCode))."
            }
            $dialog = [ChaSmokeWindow]::FindDialog([uint32]$process.Id)
            if ($dialog -ne [IntPtr]::Zero) { break }
            Start-Sleep -Milliseconds 100
        }
        if ($dialog -eq [IntPtr]::Zero) {
            throw 'CHA.EXE dialog not detected. Leave any security warning in place; do not bypass it.'
        }
        $message = [ChaSmokeWindow]::FindWindowEx($dialog, [IntPtr]::Zero, 'Static', "I'M STILL HERE.")
        if ($message -eq [IntPtr]::Zero) { throw 'Expected CHA.EXE message text was not found.' }
        $Result.dialogVerified = $true
        $Result.message = "I'M STILL HERE."
        [uint32]$owner = 0
        [void][ChaSmokeWindow]::GetWindowThreadProcessId($dialog, [ref]$owner)
        if ($owner -ne [uint32]$process.Id) { throw 'Dialog process ownership changed.' }
        if (-not [ChaSmokeWindow]::PostMessage($dialog, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero)) {
            throw 'Unable to close the verified CHA.EXE dialog.'
        }
        if (-not $process.WaitForExit(10000)) { throw 'CHA.EXE did not exit within ten seconds.' }
        $Result.exitCode = $process.ExitCode
        if ($process.ExitCode -ne 0) { throw "CHA.EXE exit code was $($process.ExitCode)." }
        $Result.status = 'Passed'
    } catch {
        $Result.status = 'Failed'
        $Result.error = $_.Exception.Message
        throw
    } finally {
        if ($null -ne $process) {
            try {
                $process.Refresh()
                if (-not $process.HasExited) {
                    # Only this process instance, never a process-name-wide termination.
                    $process.Kill()
                    [void]$process.WaitForExit(5000)
                }
            } finally { $process.Dispose() }
        }
    }
}

function Invoke-ChaSmoke {
    [CmdletBinding()]
    param(
        [string]$ArchivePath, [string]$OutputDirectory,
        [switch]$RunExecutable, [switch]$AllowUnavailableDefenderOnCI,
        [int]$ScanTimeoutSeconds = 120, [int]$DialogTimeoutSeconds = 20
    )
    $ErrorActionPreference = 'Stop'
    $archiveExpected = 'd92f5ab08ab2a4c162279d1b054a215c8b8c9818c2c2398f1544d36c9c2e8dc4'
    $binaryExpected = '0391cac84bd25c18505db7a4586e931f3ba8fd4967f8b28b6d17128d80f0c3b2'
    $hostedCI = Test-ChaHostedCI
    if (-not $OutputDirectory) {
        $OutputDirectory = [IO.Path]::GetTempPath()
        if ($hostedCI -and $env:RUNNER_TEMP -and (Test-Path -LiteralPath $env:RUNNER_TEMP -PathType Container)) {
            $OutputDirectory = $env:RUNNER_TEMP
        }
    }
    $baseDirectory = [IO.Path]::GetFullPath($OutputDirectory)
    $runDirectory = Join-Path $baseDirectory ('cha-smoke-' + [guid]::NewGuid().ToString('N'))
    # Never reuse a directory, overwrite an earlier report, or recursively delete files.
    New-Item -ItemType Directory -Path $runDirectory -ErrorAction Stop | Out-Null
    $resultPath = Join-Path $runDirectory 'result.json'
    $report = [ordered]@{
        schemaVersion = 1; startedUtc = [DateTime]::UtcNow.ToString('o'); finishedUtc = $null
        status = 'Failed'; runDirectory = $runDirectory; error = $null
        environment = [ordered]@{
            osVersion = [Environment]::OSVersion.VersionString
            powershellVersion = $PSVersionTable.PSVersion.ToString()
            is64BitProcess = [Environment]::Is64BitProcess
            hostedCI = $hostedCI
            isElevated = $null
        }
        requestedExecution = [bool]$RunExecutable
        integrity = [ordered]@{ archiveSha256 = $null; binarySha256 = $null; preLaunchSha256 = $null; sourceZoneIdentifier = $false }
        defender = $null; ciDefenderExceptionUsed = $false
        execution = [ordered]@{ status = 'NotRequested'; processId = $null; dialogVerified = $false; message = $null; exitCode = $null; error = $null }
    }
    $binaryLock = $null
    try {
        if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { throw 'Windows is required.' }
        $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
        try {
            $principal = New-Object Security.Principal.WindowsPrincipal($identity)
            $report.environment.isElevated = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
        } finally { $identity.Dispose() }
        if ($AllowUnavailableDefenderOnCI -and -not $hostedCI) {
            throw 'The unavailable-Defender exception is restricted to GitHub-hosted Windows CI.'
        }
        if ($RunExecutable) { $report.execution.status = 'Blocked' }
        $archive = (Resolve-Path -LiteralPath $ArchivePath).Path
        # A verified private snapshot prevents extraction from a different archive.
        $snapshot = Join-Path $runDirectory 'package.zip'
        Copy-Item -LiteralPath $archive -Destination $snapshot
        $zone = @(Get-Item -LiteralPath $archive -Stream * | Where-Object Stream -eq 'Zone.Identifier')
        if ($zone.Count -gt 0) {
            $zoneText = Get-Content -LiteralPath $archive -Stream Zone.Identifier -Raw
            $report.integrity.sourceZoneIdentifier = $true
            Set-Content -LiteralPath $snapshot -Stream Zone.Identifier -Value $zoneText -NoNewline
        }
        $report.integrity.archiveSha256 = (Get-FileHash -LiteralPath $snapshot -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($report.integrity.archiveSha256 -ne $archiveExpected) { throw 'CHA.EXE ZIP checksum mismatch.' }
        $destination = Join-Path $runDirectory 'extracted'
        Expand-Archive -LiteralPath $snapshot -DestinationPath $destination
        # Expand-Archive does not guarantee MOTW propagation. Preserve it explicitly.
        if ($report.integrity.sourceZoneIdentifier) {
            Get-ChildItem -LiteralPath $destination -File -Recurse | ForEach-Object {
                Set-Content -LiteralPath $_.FullName -Stream Zone.Identifier -Value $zoneText -NoNewline
            }
        }
        $binary = Join-Path $destination 'CHA_EXE_machine_code/CHA.exe'
        $report.integrity.binarySha256 = (Get-FileHash -LiteralPath $binary -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($report.integrity.binarySha256 -ne $binaryExpected) { throw 'CHA.exe checksum mismatch.' }
        $report.defender = Get-ChaDefenderResult -Binary $binary -TimeoutSeconds $ScanTimeoutSeconds
        if ($report.defender.status -eq 'Detected' -or $report.defender.status -eq 'Error') {
            throw "Defender verification failed: $($report.defender.detail)"
        }
        if ($RunExecutable) {
            if ($report.defender.status -ne 'NoDetections') {
                if ($report.defender.status -eq 'Unavailable' -and $hostedCI -and $AllowUnavailableDefenderOnCI) {
                    $report.ciDefenderExceptionUsed = $true
                    Write-Warning 'CI runtime check only: Defender unavailable. This is not a Defender scan pass.'
                } else { throw 'Execution blocked: a completed Defender scan with no matching detections is required locally.' }
            }
            if (-not [Environment]::Is64BitProcess -or $env:PROCESSOR_ARCHITECTURE -ne 'AMD64') {
                throw 'Runtime check requires native x64 Windows and a 64-bit PowerShell process.'
            }
            # Recheck after scanning and hold a read-only/no-delete share through exit.
            $binaryLock = [IO.File]::Open($binary, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
            $report.integrity.preLaunchSha256 = (Get-FileHash -InputStream $binaryLock -Algorithm SHA256).Hash.ToLowerInvariant()
            if ($report.integrity.preLaunchSha256 -ne $binaryExpected) { throw 'CHA.exe changed before launch.' }
            # Persist intent/evidence even if the host is interrupted during launch.
            $report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $resultPath -Encoding UTF8
            Invoke-ChaRuntimeCheck -Binary $binary -TimeoutSeconds $DialogTimeoutSeconds -Result $report.execution
            $report.status = 'Passed'
            if ($report.ciDefenderExceptionUsed) { $report.status = 'PassedWithDefenderUnavailable' }
        } else {
            $report.status = 'PreflightPassed'
            if ($report.defender.status -ne 'NoDetections') { $report.status = 'PreflightIncomplete' }
        }
    } catch {
        $report.error = $_.Exception.Message
        $report.status = 'Failed'
        throw
    } finally {
        if ($null -ne $binaryLock) { $binaryLock.Dispose() }
        $report.finishedUtc = [DateTime]::UtcNow.ToString('o')
        $report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $resultPath -Encoding UTF8
        Write-Host "CHA smoke: $($report.status); execution: $($report.execution.status)"
        Write-Host "Report: $resultPath"
    }
    return [pscustomobject]$report
}

if ($MyInvocation.InvocationName -ne '.') {
    Invoke-ChaSmoke -ArchivePath $ArchivePath -OutputDirectory $OutputDirectory `
        -RunExecutable:$RunExecutable -AllowUnavailableDefenderOnCI:$AllowUnavailableDefenderOnCI `
        -ScanTimeoutSeconds $ScanTimeoutSeconds -DialogTimeoutSeconds $DialogTimeoutSeconds | Out-Null
}
