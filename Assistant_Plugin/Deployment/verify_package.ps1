# Verify a deployment candidate before anyone can deploy it.
#
# This exists because the candidate went stale without saying so. It was built
# before the program was renamed to JOE, kept the name Assistant_Plugin_v1.0.0,
# and sat in the Deployment folder looking finished while the source moved on
# without it. Anyone deploying from it would have got a build in which mail,
# calendar and contacts all refused - and its own bundled proof suite would
# have reported 24 of 24, because that suite was stale too.
#
# So every check below compares the candidate against the SOURCE it was built
# from, rather than against a list written down once and left to rot.

param([Parameter(Mandatory = $true)][string]$Out)

$ErrorActionPreference = 'Stop'
$source = Split-Path -Parent (Split-Path -Parent $Out)
$problems = @()
$checks = 0

function Test-It($label, $ok, $detail) {
    $script:checks++
    if ($ok) {
        Write-Host ("   PASS  " + $label)
    } else {
        Write-Host ("   FAIL  " + $label + "   " + $detail)
        $script:problems += $label
    }
}

Write-Host ""

# --- the launcher and entry point the instructions actually name ----------
foreach ($required in @('START_JOE.cmd', 'joe_main.py')) {
    Test-It "ships $required" (Test-Path (Join-Path $Out $required)) "missing"
}

# --- the machine's own configuration must never travel -------------------
$leaked = Get-ChildItem -Path $Out -Recurse -File -Force -ErrorAction SilentlyContinue |
          Where-Object { $_.Name -eq 'joe.config.json' }
Test-It "carries no machine configuration" (-not $leaked) `
        ($(if ($leaked) { $leaked[0].FullName } else { '' }))

Test-It "ships the configuration template" `
        (Test-Path (Join-Path $Out 'configuration\joe.config.template.json')) "missing"

# --- no runtime state, no credentials, no logs ---------------------------
$state = Get-ChildItem -Path $Out -Recurse -File -Force -ErrorAction SilentlyContinue |
         Where-Object { $_.FullName -match '\\(runtime_data|logs|__pycache__|_workspace)\\' }
Test-It "carries no runtime state or logs" (-not $state) `
        ($(if ($state) { "$($state.Count) file(s), e.g. $($state[0].Name)" } else { '' }))

$secrets = Get-ChildItem -Path $Out -Recurse -File -Force -ErrorAction SilentlyContinue |
           Where-Object { $_.Extension -eq '.bin' -or $_.Name -like '*token*' }
Test-It "carries no token cache" (-not $secrets) `
        ($(if ($secrets) { $secrets[0].Name } else { '' }))

# --- the candidate must match the source it was built from ---------------
# Compared file by file rather than by a written-down list, because a written
# list is the thing that went stale last time.
# The skip pattern is applied to the path RELATIVE to each root, never to the
# absolute path. The candidate lives inside Deployment\, so matching absolute
# paths would filter out every file in the candidate and report the whole
# package missing - which is exactly what the first version of this script did.
$skip = '(^|\\)(runtime_data|logs|__pycache__|_workspace|Deployment|\.git)(\\|$)'

function Get-Relative($root) {
    $table = @{}
    Get-ChildItem -Path $root -Recurse -File -Force -ErrorAction SilentlyContinue |
        ForEach-Object {
            $rel = $_.FullName.Substring($root.Length + 1)
            if ($rel -notmatch $skip -and
                $_.Name -notin @('joe.config.json', 'last_test_run.txt')) {
                $table[$rel] = $_.Length
            }
        }
    return $table
}

$sourceFiles = Get-Relative $source
$outFiles = Get-Relative $Out

$missing = @($sourceFiles.Keys | Where-Object { -not $outFiles.ContainsKey($_) })
$stale = @($sourceFiles.Keys | Where-Object {
    $outFiles.ContainsKey($_) -and $outFiles[$_] -ne $sourceFiles[$_] })

Test-It "every source file is present" ($missing.Count -eq 0) `
        ($(if ($missing.Count) { "$($missing.Count) missing, e.g. $($missing[0])" } else { '' }))
Test-It "no file differs from source" ($stale.Count -eq 0) `
        ($(if ($stale.Count) { "$($stale.Count) differ, e.g. $($stale[0])" } else { '' }))

$files = @(Get-ChildItem -Path $Out -Recurse -File -Force -ErrorAction SilentlyContinue)
$mb = [math]::Round((($files | Measure-Object Length -Sum).Sum / 1MB), 2)

Write-Host ""
Write-Host ("   files: " + $files.Count + "   size: " + $mb + " MB")
Write-Host ("   " + ($checks - $problems.Count) + " of " + $checks + " checks passed")

if ($problems.Count) { exit 1 }
exit 0
