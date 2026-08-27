# Creates JOE's desktop shortcuts.
#
# Only shortcuts this script itself created are ever replaced. Nothing else on
# the desktop is read, moved, or removed.
#
# JOE gets the plain name. The two proof utilities are prefixed "JOE" so they
# sort together and are obviously part of the same program.

param(
    [Parameter(Mandatory = $true)][string]$PluginRoot
)

$ErrorActionPreference = 'Stop'

$desktop = [Environment]::GetFolderPath('Desktop')
if (-not (Test-Path $desktop)) {
    Write-Host "  Could not find the desktop folder."
    exit 1
}

# A stock Windows icon each shortcut can use, so JOE does not appear as a
# generic script file. imageres.dll is present on every supported build.
$iconLibrary = Join-Path $env:SystemRoot "System32\imageres.dll"

$shortcuts = @(
    @{ Name = "JOE";
       Target = "START_JOE.cmd";
       Icon = 175;
       Description = "JOE, the Level 1 Assistant" },

    @{ Name = "JOE Microphone Test";
       Target = "launchers\MIC_TEST.cmd";
       Icon = 168;
       Description = "Check which microphone JOE can hear, and test it" },

    @{ Name = "JOE Microphone List";
       Target = "launchers\MIC_LIST.cmd";
       Icon = 24;
       Description = "Which microphone JOE can hear - no speaking required" },

    @{ Name = "JOE Settings and Status";
       Target = "launchers\JOE_STATUS.cmd";
       Icon = 109;
       Description = "What JOE is connected to right now" }
)

$shell = New-Object -ComObject WScript.Shell
$made = 0
$skipped = @()

foreach ($item in $shortcuts) {
    $target = Join-Path $PluginRoot $item.Target
    if (-not (Test-Path $target)) {
        $skipped += ("{0}  (missing {1})" -f $item.Name, $item.Target)
        continue
    }

    $linkPath = Join-Path $desktop ($item.Name + ".lnk")
    $link = $shell.CreateShortcut($linkPath)
    $link.TargetPath = $target
    $link.WorkingDirectory = $PluginRoot
    $link.Description = $item.Description
    $link.WindowStyle = 1
    if (Test-Path $iconLibrary) {
        $link.IconLocation = "{0},{1}" -f $iconLibrary, $item.Icon
    }
    $link.Save()

    if (Test-Path $linkPath) {
        "  created   {0}" -f $item.Name
        $made++
    } else {
        $skipped += ("{0}  (could not be written)" -f $item.Name)
    }
}

""
foreach ($s in $skipped) { "  SKIPPED   $s" }
"  {0} shortcut(s) on {1}" -f $made, $desktop

if ($made -eq 0) { exit 1 }
exit 0
