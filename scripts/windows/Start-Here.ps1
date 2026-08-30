[CmdletBinding()]
param(
    [string]$Distro = "Ubuntu-22.04",
    [string]$BundleRoot = "",
    [string]$SharedDir = "",
    [string]$Prefix = "~/wrfhydro_build",
    [string]$IntelHome = "~/intel/parallel_studio_xe_2018",
    [string]$PythonEnvHome = "~/wrfhydro_env",
    [switch]$NoInstallIntel,
    [switch]$NoPythonEnv,
    [switch]$RunExample,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Test-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function ConvertTo-WslPath {
    param([Parameter(Mandatory=$true)][string]$WindowsPath)
    $resolved = (Resolve-Path -LiteralPath $WindowsPath).Path
    if ($resolved -match '^([A-Za-z]):\\(.*)$') {
        $drive = $Matches[1].ToLowerInvariant()
        $rest = $Matches[2] -replace '\\', '/'
        return "/mnt/$drive/$rest"
    }
    throw "Only drive-letter paths are supported for WSL conversion: $resolved"
}

function Quote-Bash {
    param([Parameter(Mandatory=$true)][string]$Value)
    if ($Value.Contains("'")) {
        throw "Paths containing a single quote are not supported: $Value"
    }
    return "'" + $Value + "'"
}

function Resolve-BundleRoot {
    param([Parameter(Mandatory=$true)][string]$ScriptRoot)

    $root = (Resolve-Path -LiteralPath $ScriptRoot).Path

    if (
        (Test-Path -LiteralPath (Join-Path $root "Data_Shared")) -and
        (Test-Path -LiteralPath (Join-Path $root "easy_wrf-hydro_build\scripts\linux\prepare_blank_ubuntu.sh"))
    ) {
        return $root
    }

    if (Test-Path -LiteralPath (Join-Path $root "scripts\linux\prepare_blank_ubuntu.sh")) {
        return $root
    }

    $projectRoot = (Resolve-Path -LiteralPath (Join-Path $root "..\..")).Path
    if (Test-Path -LiteralPath (Join-Path $projectRoot "scripts\linux\prepare_blank_ubuntu.sh")) {
        return $projectRoot
    }

    $parent = Split-Path -Parent $root
    if (
        $parent -and
        (Test-Path -LiteralPath (Join-Path $parent "Data_Shared")) -and
        (Test-Path -LiteralPath (Join-Path $parent "easy_wrf-hydro_build\scripts\linux\prepare_blank_ubuntu.sh"))
    ) {
        return $parent
    }

    throw "Cannot infer bundle root from script location: $root"
}

function Get-WslList {
    try {
        $output = & wsl.exe --list --verbose 2>&1
        return @{
            ExitCode = $LASTEXITCODE
            Output = $output
        }
    } catch {
        return @{
            ExitCode = 1
            Output = @($_.Exception.Message)
        }
    }
}

function Ensure-WslAndDistro {
    if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
        if (-not (Test-Administrator)) {
            throw "WSL is not installed. Please rerun PowerShell as Administrator."
        }
        Write-Host "Installing WSL and $Distro. Restart Windows if prompted, then rerun this script."
        wsl.exe --install -d $Distro
        exit $LASTEXITCODE
    }

    $wslList = Get-WslList
    $listText = ($wslList.Output -join "`n")
    if ($wslList.ExitCode -ne 0 -or $listText -notmatch [regex]::Escape($Distro)) {
        if (-not (Test-Administrator)) {
            throw "$Distro is not installed. Please rerun PowerShell as Administrator."
        }
        Write-Host "Installing $Distro under WSL2. Create the Ubuntu user when the installer opens, then rerun this script."
        wsl.exe --set-default-version 2
        wsl.exe --install -d $Distro
        exit $LASTEXITCODE
    }
}

if ([string]::IsNullOrWhiteSpace($BundleRoot)) {
    $BundleRoot = Resolve-BundleRoot -ScriptRoot $PSScriptRoot
} else {
    $BundleRoot = (Resolve-Path -LiteralPath $BundleRoot).Path
}

$projectDir = Join-Path $BundleRoot "easy_wrf-hydro_build"
if (-not (Test-Path -LiteralPath $projectDir)) {
    $projectDir = $BundleRoot
}
if (-not (Test-Path -LiteralPath (Join-Path $projectDir "scripts\linux\prepare_blank_ubuntu.sh"))) {
    throw "Cannot find easy_wrf-hydro_build project under $BundleRoot"
}

if ([string]::IsNullOrWhiteSpace($SharedDir)) {
    $bundledShared = Join-Path $BundleRoot "Data_Shared"
    if (Test-Path -LiteralPath $bundledShared) {
        $SharedDir = $bundledShared
    } else {
        $userProfile = [Environment]::GetFolderPath("UserProfile")
        $SharedDir = Join-Path $userProfile "Downloads\WRF-Hydro-Packages"
    }
}
if (-not (Test-Path -LiteralPath $SharedDir)) {
    throw "Shared package directory not found: $SharedDir"
}

Ensure-WslAndDistro

$wslProject = ConvertTo-WslPath $projectDir
$wslShared = ConvertTo-WslPath $SharedDir

$linuxArgs = @(
    "--shared-dir", (Quote-Bash $wslShared),
    "--prefix", (Quote-Bash $Prefix),
    "--intel-home", (Quote-Bash $IntelHome),
    "--python-env-home", (Quote-Bash $PythonEnvHome),
    "--repo-dir", (Quote-Bash $wslProject)
)

if ($NoInstallIntel) {
    $linuxArgs += "--no-install-intel"
}
if ($NoPythonEnv) {
    $linuxArgs += "--no-python-env"
}
if ($RunExample) {
    $linuxArgs += "--run-example"
}
if ($DryRun) {
    $linuxArgs += "--dry-run"
}

$cmd = "cd $(Quote-Bash $wslProject) && bash scripts/linux/prepare_blank_ubuntu.sh " + ($linuxArgs -join " ")
Write-Host "Running inside ${Distro}:"
Write-Host $cmd
wsl.exe -d $Distro -- bash -lc $cmd
exit $LASTEXITCODE
