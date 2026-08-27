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

# Three icons, not four. MIC_TEST already lists every recording device, so a
# separate Microphone List icon was a second way to do part of the same job -
# and an extra icon is one more thing to read past on a desktop.
$shortcuts = @(
    @{ Name = "JOE";
       Target = "START_JOE.cmd";
       Icon = 175;
       Description = "JOE, the Level 1 Assistant" },

    @{ Name = "JOE Microphone Test";
       Target = "launchers\MIC_TEST.cmd";
       Icon = 168;
       Description = "Which microphone JOE hears, and whether it understands you" },

    @{ Name = "JOE Status";
       Target = "launchers\JOE_STATUS.cmd";
       Icon = 109;
       Description = "What JOE is connected to right now, and what it is not" }
)

# Names this script has used before. Removed on every run so a rename leaves
# nothing orphaned on the desktop. Only names this script itself created are
# ever touched - nothing else on the desktop is read, moved, or deleted.
$retired = @("JOE Microphone List", "JOE Settings and Status")

$shell = New-Object -ComObject WScript.Shell
$made = 0
$skipped = @()

# The JOE shortcut points straight at a Python interpreter. Two things had to
# be removed to stop a black console flashing on every launch, and the second
# only became visible once the first was gone.
#
# A shortcut to a .cmd always flashes: Windows gives cmd.exe a console before
# the batch file can run a line, and START_JOE.cmd's whole job is to locate an
# interpreter and hand off to it. So the middleman goes.
#
# And the interpreter must be a REAL executable, not a Store app-execution
# alias. The pyw.exe in WindowsApps\ is a zero-byte reparse point that Windows
# resolves through the app model, and that resolution flashes too - it was the
# one Mike could still see after the adapters were fixed. A real pythonw.exe is
# a GUI-subsystem binary and owns no console at any point, which is what the
# subsystem check below confirms rather than assumes.
#
# The check START_JOE.cmd performs, that an interpreter exists at all, is not
# lost. It moves here, to install time, which is a better moment to discover a
# missing Python than the moment Mike wants to use the program. With none
# found the shortcut falls back to the batch file, which explains the problem
# properly.
function Find-RealPythonw {
    $candidates = @()
    $candidates += (Get-Command pythonw.exe -All -ErrorAction SilentlyContinue |
                    ForEach-Object { $_.Source })
    $candidates += (Join-Path $env:LOCALAPPDATA "Python\bin\pythonw.exe")
    $candidates += (Get-ChildItem (Join-Path $env:LOCALAPPDATA "Python") `
                    -Recurse -Filter pythonw.exe -ErrorAction SilentlyContinue |
                    ForEach-Object { $_.FullName })
    $candidates += (Get-Command pyw.exe -All -ErrorAction SilentlyContinue |
                    ForEach-Object { $_.Source })

    foreach ($path in $candidates) {
        if (-not $path -or -not (Test-Path $path)) { continue }
        $file = Get-Item $path -Force -ErrorAction SilentlyContinue
        # A zero-length entry is an app-execution alias, not a program.
        if (-not $file -or $file.Length -eq 0) { continue }
        try {
            $stream = [IO.File]::OpenRead($path)
            $reader = New-Object IO.BinaryReader($stream)
            $stream.Seek(0x3C, 'Begin') | Out-Null
            $header = $reader.ReadInt32()
            $stream.Seek($header + 0x5C, 'Begin') | Out-Null
            $subsystem = $reader.ReadInt16()
            $reader.Close(); $stream.Close()
        } catch { continue }
        # 2 is the Windows GUI subsystem: no console, ever.
        if ($subsystem -eq 2) { return $path }
    }
    return $null
}

$pyw = Find-RealPythonw

# Clear retired names first, so a rename never leaves a dead icon behind.
foreach ($name in $retired) {
    $old = Join-Path $desktop ($name + ".lnk")
    if (Test-Path $old) {
        Remove-Item $old -Force -ErrorAction SilentlyContinue
        "  removed   {0}  (retired)" -f $name
    }
}

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

    # Read the shortcut back and confirm it resolves to something that exists.
    # A .lnk saves happily whether or not its target is real, so writing one is
    # not evidence that clicking it will do anything.
    if (Test-Path $linkPath) {
        $check = $shell.CreateShortcut($linkPath)
        if (Test-Path $check.TargetPath) {
            "  created   {0}" -f $item.Name
            $made++
        } else {
            $skipped += ("{0}  (points at a missing {1})" -f $item.Name,
                         $check.TargetPath)
        }
    } else {
        $skipped += ("{0}  (could not be written)" -f $item.Name)
    }
}

""
foreach ($s in $skipped) { "  SKIPPED   $s" }
"  {0} shortcut(s) on {1}" -f $made, $desktop
if ($pyw) {
    "  JOE opens with no console window" 
    "  interpreter: {0}" -f $pyw
} else {
    "  NOTE: no real pythonw.exe found - only Store aliases, which flash."
    "        The JOE shortcut goes through START_JOE.cmd instead."
    "        Install Python 3.10 or newer from python.org and run this again."
}

if ($made -eq 0) { exit 1 }
exit 0
