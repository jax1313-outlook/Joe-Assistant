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

# A shortcut to a .cmd flashes a black console every time it is used, because
# Windows gives cmd.exe a console before the batch file can do anything - and
# START_JOE.cmd's whole job is to find pyw and hand off to it. Pointing the
# JOE shortcut straight at pyw.exe removes the middleman and the flash.
#
# The check START_JOE.cmd performs, that a Python launcher exists, is not lost.
# It moves here, to install time, which is a better moment to discover a
# missing Python than the moment Mike wants to use the program. If pyw is not
# found the shortcut falls back to the batch file, which explains the problem
# properly.
$pyw = (Get-Command pyw.exe -ErrorAction SilentlyContinue |
        Select-Object -First 1).Source

foreach ($item in $shortcuts) {
    $target = Join-Path $PluginRoot $item.Target
    if (-not (Test-Path $target)) {
        $skipped += ("{0}  (missing {1})" -f $item.Name, $item.Target)
        continue
    }

    $arguments = ""
    if ($item.Name -eq "JOE" -and $pyw) {
        $target = $pyw
        $arguments = ('-X utf8 "{0}"' -f (Join-Path $PluginRoot "joe_main.py"))
    }

    $linkPath = Join-Path $desktop ($item.Name + ".lnk")
    $link = $shell.CreateShortcut($linkPath)
    $link.TargetPath = $target
    if ($arguments) { $link.Arguments = $arguments }
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
if ($pyw) {
    "  JOE opens with no console window (pyw at {0})" -f $pyw
} else {
    "  NOTE: no pyw.exe found on this machine, so the JOE shortcut goes"
    "        through START_JOE.cmd and will flash a console window."
    "        Install Python 3.10 or newer from python.org and run this again."
}

if ($made -eq 0) { exit 1 }
exit 0
