#requires -Version 5.1
# Dependency-free regression tests. No CHA.EXE process or real Defender scan is started.
$ErrorActionPreference = 'Stop'
$smokeScript = Join-Path $PSScriptRoot 'cha_windows_smoke.ps1'
$package = Join-Path $PSScriptRoot '../after-hours/assets/CHA_EXE_Im_Still_Here.zip'
$testRoot = Join-Path ([IO.Path]::GetTempPath()) ('cha-regression-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $testRoot | Out-Null
$failures = 0
$count = 0

function Assert-True($Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}
function Assert-Throws([scriptblock]$Body, [string]$Pattern) {
    $caught = $null
    try { & $Body | Out-Null } catch { $caught = $_.Exception.Message }
    Assert-True ($null -ne $caught -and $caught -match $Pattern) "Expected error /$Pattern/, got: $caught"
}
function Read-LastReport([string]$Root) {
    $file = Get-ChildItem -LiteralPath $Root -Filter result.json -Recurse |
        Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
    Assert-True ($null -ne $file) 'Failure did not write result.json.'
    return (Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json)
}
function Invoke-Case([string]$Name, [scriptblock]$Body) {
    $script:count++
    $saved = @{}
    foreach ($key in @('GITHUB_ACTIONS', 'RUNNER_ENVIRONMENT', 'RUNNER_OS', 'RUNNER_TEMP')) {
        $saved[$key] = [Environment]::GetEnvironmentVariable($key)
        [Environment]::SetEnvironmentVariable($key, $null)
    }
    try {
        & {
            . $smokeScript
            $caseRoot = Join-Path $testRoot ($script:count.ToString())
            New-Item -ItemType Directory -Path $caseRoot | Out-Null
            $script:runtimeCalls = 0
            function Start-Process { throw 'Regression harness must never launch a process.' }
            function Get-ChaDefenderResult {
                [pscustomobject]@{ status = 'NoDetections'; scanCompleted = $true; detail = 'MOCK' }
            }
            function Invoke-ChaRuntimeCheck {
                param($Binary, $TimeoutSeconds, $Result)
                $script:runtimeCalls++
                $Result.status = 'Passed'
                $Result.dialogVerified = $true
                $Result.exitCode = 0
            }
            & $Body
        }
        Write-Host "PASS: $Name"
    } catch {
        $script:failures++
        Write-Host "FAIL: $Name -- $($_.Exception.Message)"
    } finally {
        foreach ($key in $saved.Keys) { [Environment]::SetEnvironmentVariable($key, $saved[$key]) }
    }
}

Invoke-Case 'Default preflight never launches and records both hashes' {
    $r = Invoke-ChaSmoke -ArchivePath $package -OutputDirectory $caseRoot
    Assert-True ($r.status -eq 'PreflightPassed') 'Preflight status'
    Assert-True ($r.execution.status -eq 'NotRequested' -and $script:runtimeCalls -eq 0) 'Unexpected execution'
    Assert-True ($r.integrity.archiveSha256 -eq 'd92f5ab08ab2a4c162279d1b054a215c8b8c9818c2c2398f1544d36c9c2e8dc4') 'ZIP hash'
    Assert-True ($r.integrity.binarySha256 -eq '0391cac84bd25c18505db7a4586e931f3ba8fd4967f8b28b6d17128d80f0c3b2') 'EXE hash'
    Assert-True ((Read-LastReport $caseRoot).execution.status -eq 'NotRequested') 'Persisted status'
}
Invoke-Case 'RUNNER_TEMP is optional and local fallback is unique' {
    $a = Invoke-ChaSmoke -ArchivePath $package
    $b = Invoke-ChaSmoke -ArchivePath $package
    Assert-True ($a.runDirectory -ne $b.runDirectory) 'Temporary directory reused'
    Assert-True ($a.runDirectory.StartsWith([IO.Path]::GetTempPath(), [StringComparison]::OrdinalIgnoreCase)) 'Wrong fallback'
}
Invoke-Case 'Hosted CI uses RUNNER_TEMP without implicitly opting in' {
    $env:GITHUB_ACTIONS = 'true'; $env:RUNNER_ENVIRONMENT = 'github-hosted'; $env:RUNNER_OS = 'Windows'
    $env:RUNNER_TEMP = $caseRoot
    $r = Invoke-ChaSmoke -ArchivePath $package
    Assert-True ($r.runDirectory.StartsWith($caseRoot, [StringComparison]::OrdinalIgnoreCase)) 'Wrong CI temp'
    Assert-True ($script:runtimeCalls -eq 0) 'CI implicitly launched'
}
Invoke-Case 'Invalid hosted RUNNER_TEMP falls back to OS temp' {
    $env:GITHUB_ACTIONS = 'true'; $env:RUNNER_ENVIRONMENT = 'github-hosted'; $env:RUNNER_OS = 'Windows'
    $env:RUNNER_TEMP = Join-Path $caseRoot 'missing'
    $r = Invoke-ChaSmoke -ArchivePath $package
    Assert-True ($r.runDirectory.StartsWith([IO.Path]::GetTempPath(), [StringComparison]::OrdinalIgnoreCase)) 'No fallback'
}
Invoke-Case 'Bad ZIP is rejected before scanning, extraction or launch' {
    $bad = Join-Path $caseRoot 'bad.zip'
    Set-Content -LiteralPath $bad -Value 'not the pinned archive'
    function Get-ChaDefenderResult { throw 'Scan must not be reached' }
    Assert-Throws { Invoke-ChaSmoke -ArchivePath $bad -OutputDirectory $caseRoot -RunExecutable } 'ZIP checksum mismatch'
    $r = Read-LastReport $caseRoot
    Assert-True ($r.status -eq 'Failed' -and $null -eq $r.defender -and $script:runtimeCalls -eq 0) 'Incorrect failure record'
    Assert-True (-not (Test-Path -LiteralPath (Join-Path $r.runDirectory 'extracted'))) 'Bad ZIP extracted'
}
Invoke-Case 'Bad EXE hash blocks scanning and execution' {
    function Get-FileHash {
        param($LiteralPath, $Algorithm, $InputStream)
        if ($LiteralPath -like '*.exe') { return [pscustomobject]@{ Hash = 'bad' } }
        Microsoft.PowerShell.Utility\Get-FileHash -LiteralPath $LiteralPath -Algorithm $Algorithm
    }
    function Get-ChaDefenderResult { throw 'Scan must not be reached' }
    Assert-Throws { Invoke-ChaSmoke -ArchivePath $package -OutputDirectory $caseRoot -RunExecutable } 'exe checksum mismatch'
    Assert-True ($script:runtimeCalls -eq 0) 'Launched invalid EXE'
}
Invoke-Case 'Defender unavailable gives incomplete preflight, never scan pass' {
    function Get-ChaDefenderResult { [pscustomobject]@{ status = 'Unavailable'; detail = 'MOCK missing' } }
    $r = Invoke-ChaSmoke -ArchivePath $package -OutputDirectory $caseRoot
    Assert-True ($r.status -eq 'PreflightIncomplete' -and $script:runtimeCalls -eq 0) 'Missing engine passed'
}
Invoke-Case 'Local execution fails closed without Defender' {
    function Get-ChaDefenderResult { [pscustomobject]@{ status = 'Unavailable'; detail = 'MOCK missing' } }
    Assert-Throws { Invoke-ChaSmoke -ArchivePath $package -OutputDirectory $caseRoot -RunExecutable } 'Execution blocked'
    Assert-True ((Read-LastReport $caseRoot).execution.status -eq 'Blocked' -and $script:runtimeCalls -eq 0) 'Not blocked'
}
Invoke-Case 'CI-only exception cannot be used locally' {
    Assert-Throws { Invoke-ChaSmoke -ArchivePath $package -OutputDirectory $caseRoot -RunExecutable -AllowUnavailableDefenderOnCI } 'restricted'
    Assert-True ($script:runtimeCalls -eq 0) 'Exception accepted locally'
}
Invoke-Case 'Hosted CI exception is explicit and reported' {
    $env:GITHUB_ACTIONS = 'true'; $env:RUNNER_ENVIRONMENT = 'github-hosted'; $env:RUNNER_OS = 'Windows'
    function Get-ChaDefenderResult { [pscustomobject]@{ status = 'Unavailable'; detail = 'MOCK missing' } }
    Assert-Throws { Invoke-ChaSmoke -ArchivePath $package -OutputDirectory $caseRoot -RunExecutable } 'Execution blocked'
    $r = Invoke-ChaSmoke -ArchivePath $package -OutputDirectory $caseRoot -RunExecutable -AllowUnavailableDefenderOnCI
    Assert-True ($r.status -eq 'PassedWithDefenderUnavailable' -and $r.ciDefenderExceptionUsed -and $script:runtimeCalls -eq 1) 'CI exception record'
}
foreach ($state in @('Detected', 'Error', 'Unknown')) {
    Invoke-Case "Defender $state blocks even CI exception" {
        $env:GITHUB_ACTIONS = 'true'; $env:RUNNER_ENVIRONMENT = 'github-hosted'; $env:RUNNER_OS = 'Windows'
        function Get-ChaDefenderResult { [pscustomobject]@{ status = $state; detail = 'MOCK failure' } }
        Assert-Throws { Invoke-ChaSmoke -ArchivePath $package -OutputDirectory $caseRoot -RunExecutable -AllowUnavailableDefenderOnCI } 'failed|blocked'
        Assert-True ($script:runtimeCalls -eq 0) 'Defender failure allowed execution'
    }
}
Invoke-Case 'Explicit execution checks the hash again and records exit' {
    $r = Invoke-ChaSmoke -ArchivePath $package -OutputDirectory $caseRoot -RunExecutable
    Assert-True ($script:runtimeCalls -eq 1 -and $r.execution.exitCode -eq 0 -and $r.status -eq 'Passed') 'Execution result'
    Assert-True ($r.integrity.preLaunchSha256 -eq '0391cac84bd25c18505db7a4586e931f3ba8fd4967f8b28b6d17128d80f0c3b2') 'No prelaunch hash'
}
Invoke-Case 'Post-scan file changes block launch' {
    function Get-ChaDefenderResult {
        param($Binary, $TimeoutSeconds)
        [IO.File]::WriteAllText($Binary, 'changed during scan')
        [pscustomobject]@{ status = 'NoDetections'; detail = 'MOCK' }
    }
    Assert-Throws { Invoke-ChaSmoke -ArchivePath $package -OutputDirectory $caseRoot -RunExecutable } 'changed before launch'
    Assert-True ($script:runtimeCalls -eq 0) 'Changed file launched'
}
Invoke-Case 'Runtime failure persists a failed report' {
    function Invoke-ChaRuntimeCheck {
        param($Binary, $TimeoutSeconds, $Result)
        $Result.status = 'Failed'
        $Result.error = 'MOCK dialog timeout'
        throw 'MOCK dialog timeout'
    }
    Assert-Throws { Invoke-ChaSmoke -ArchivePath $package -OutputDirectory $caseRoot -RunExecutable } 'dialog timeout'
    $r = Read-LastReport $caseRoot
    Assert-True ($r.status -eq 'Failed' -and $r.execution.status -eq 'Failed' -and $r.finishedUtc) 'Lost failure evidence'
}
Invoke-Case 'MOTW survives extraction without launching' {
    $download = Join-Path $caseRoot 'download.zip'
    Copy-Item -LiteralPath $package -Destination $download
    Set-Content -LiteralPath $download -Stream Zone.Identifier -Value "[ZoneTransfer]`r`nZoneId=3"
    $r = Invoke-ChaSmoke -ArchivePath $download -OutputDirectory $caseRoot
    $exe = Join-Path $r.runDirectory 'extracted/CHA_EXE_machine_code/CHA.exe'
    $zone = Get-Content -LiteralPath $exe -Stream Zone.Identifier -Raw
    Assert-True ($r.integrity.sourceZoneIdentifier -and $zone -match 'ZoneId=3' -and $script:runtimeCalls -eq 0) 'MOTW was lost'
}

# Exercise the actual Defender decision function with isolated command mocks.
function Invoke-DefenderCase([string]$Name, [scriptblock]$DefenderBody) {
    Invoke-Case $Name {
        # Restore original helper after the orchestration mock.
        . $smokeScript
        function Get-MpComputerStatus {
            [pscustomobject]@{ AMServiceEnabled = $true; AntivirusEnabled = $true; RealTimeProtectionEnabled = $true }
        }
        function Start-MpScan { param($ScanType, $ScanPath, [switch]$AsJob, $ErrorAction) [pscustomobject]@{ State = 'Completed' } }
        function Wait-Job { param($Job, $Timeout, $ErrorAction) $Job }
        function Receive-Job { param($Job, $ErrorAction) }
        function Remove-Job { param($Job, [switch]$Force, $ErrorAction) }
        function Stop-Job { param($Job, $ErrorAction) }
        function Get-MpThreatDetection { param($ErrorAction) }
        & $DefenderBody
    }
}
Invoke-DefenderCase 'Completed scan with no relevant detection is recorded' {
    $r = Get-ChaDefenderResult -Binary 'C:\unique\CHA.exe' -TimeoutSeconds 5
    Assert-True ($r.status -eq 'NoDetections' -and $r.scanCompleted) $r.detail
}
Invoke-DefenderCase 'Inactive Defender is unavailable' {
    function Get-MpComputerStatus { [pscustomobject]@{ AMServiceEnabled = $false; AntivirusEnabled = $false } }
    $r = Get-ChaDefenderResult -Binary 'C:\unique\CHA.exe' -TimeoutSeconds 5
    Assert-True ($r.status -eq 'Unavailable' -and -not $r.scanCompleted) $r.detail
}
Invoke-DefenderCase 'Missing Defender command is unavailable' {
    function Get-Command { param($Name, $ErrorAction) return $null }
    $r = Get-ChaDefenderResult -Binary 'C:\unique\CHA.exe' -TimeoutSeconds 5
    Assert-True ($r.status -eq 'Unavailable' -and -not $r.scanCompleted) $r.detail
}
Invoke-DefenderCase 'Status access failure is an error, not unavailable' {
    function Get-MpComputerStatus { throw 'access denied' }
    $r = Get-ChaDefenderResult -Binary 'C:\unique\CHA.exe' -TimeoutSeconds 5
    Assert-True ($r.status -eq 'Error' -and $r.detail -match 'access denied') $r.detail
}
Invoke-DefenderCase 'Scan timeout is an error' {
    function Wait-Job { param($Job, $Timeout, $ErrorAction) return $null }
    $r = Get-ChaDefenderResult -Binary 'C:\unique\CHA.exe' -TimeoutSeconds 5
    Assert-True ($r.status -eq 'Error' -and -not $r.scanCompleted -and $r.detail -match 'timed out') $r.detail
}
Invoke-DefenderCase 'Scan job failure is an error' {
    function Receive-Job { throw 'scan failed' }
    $r = Get-ChaDefenderResult -Binary 'C:\unique\CHA.exe' -TimeoutSeconds 5
    Assert-True ($r.status -eq 'Error' -and -not $r.scanCompleted) $r.detail
}
Invoke-DefenderCase 'Detection history failure is not a clean scan' {
    function Get-MpThreatDetection { throw 'history unavailable' }
    $r = Get-ChaDefenderResult -Binary 'C:\unique\CHA.exe' -TimeoutSeconds 5
    Assert-True ($r.status -eq 'Error' -and $r.scanCompleted) $r.detail
}
Invoke-DefenderCase 'Matching detection blocks; unrelated history is not logged' {
    function Get-MpThreatDetection {
        [pscustomobject]@{ Resources = @('file:_C:\other\private.exe'); ThreatID = 999 }
        [pscustomobject]@{ Resources = @('file:_C:\unique\CHA.exe'); ThreatID = 123 }
    }
    $r = Get-ChaDefenderResult -Binary 'C:\unique\CHA.exe' -TimeoutSeconds 5
    Assert-True ($r.status -eq 'Detected' -and $r.detectionCount -eq 1 -and $r.threatIds[0] -eq '123') $r.detail
}
Write-Host "$($count - $failures)/$count CHA smoke regression cases passed. Temporary evidence: $testRoot"
if ($failures -gt 0) { throw "$failures CHA smoke regression case(s) failed." }
