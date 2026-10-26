# cap.ps1 -- one isolated headless Chrome, then run a whole screenshot script through CDP.
#
# Why one Chrome for all scenarios: launching a browser per screenshot costs ~1.5s each
# and, worse, every launch gets its own warm-up timing. One process + a fresh page load
# per scenario gives identical composition run after run.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File _redesign\tools\cap.ps1
#   powershell -ExecutionPolicy Bypass -File _redesign\tools\cap.ps1 -Out _redesign\shots\before
#   powershell -ExecutionPolicy Bypass -File _redesign\tools\cap.ps1 -Scenario card,card-video
#   powershell -ExecutionPolicy Bypass -File _redesign\tools\cap.ps1 -Html _redesign\baseline\index.html
#   powershell -ExecutionPolicy Bypass -File _redesign\tools\cap.ps1 -Smoke
#
#  -Html <file>  serve THIS html instead of the one the dev server has (CDP Fetch intercepts
#                the top-level document only). Use it to shoot the "before" baseline from
#                _redesign\baseline\index.html even after web/index.html has been rewritten.
#  -Smoke        run smoke.mjs (functional regression) instead of cap.mjs (screenshots).
#
# Exit code: 0 = every scenario ok / all assertions pass, 1 = something failed.
#
# NOTE: keep this file ASCII-only. Windows PowerShell 5.1 reads a BOM-less .ps1 as
# ANSI/GBK on a Chinese system, which corrupts non-ASCII text and can break the parser.

param(
  [int]$Port = 8800,
  [string]$Out = "",
  [string[]]$Scenario = @("all"),
  [int]$Width = 1280,
  [int]$Height = 880,
  [int]$CdpPort = 9223,
  [string]$Scenarios = "",
  [string]$DevHost = "127.0.0.1",
  [string]$Html = "",
  [string]$Only = "",
  [switch]$Smoke,
  [switch]$KeepChrome,
  [switch]$NoShot
)

$ErrorActionPreference = 'Continue'
$chrome = "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
if (-not (Test-Path $chrome)) { Write-Error "Chrome not found: $chrome"; exit 1 }

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent (Split-Path -Parent $here)
if (-not $Out) {
  if ($Smoke) { $Out = Join-Path $root "_redesign\shots" }
  else { $Out = Join-Path $root "_redesign\shots\before" }
}
if (-not $Scenarios) { $Scenarios = Join-Path $here "scenarios.json" }

function Resolve-AbsPath([string]$p) {
  if ([System.IO.Path]::IsPathRooted($p)) {
    return [System.IO.Path]::GetFullPath($p)
  }
  return [System.IO.Path]::GetFullPath((Join-Path (Get-Location).Path $p))
}

$Out = Resolve-AbsPath $Out
if (-not (Test-Path $Out)) { New-Item -ItemType Directory -Force -Path $Out | Out-Null }
$Scenarios = Resolve-AbsPath $Scenarios

function Test-DebugPort([int]$p) {
  try {
    $null = Invoke-RestMethod -Uri ("http://127.0.0.1:{0}/json/version" -f $p) -TimeoutSec 1
    return $true
  } catch { return $false }
}

function Get-OurChrome([string]$profile) {
  Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -and $_.CommandLine.Contains($profile) }
}

function Stop-OurChrome([string]$profile) {
  Get-OurChrome $profile | ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
  }
  Start-Sleep -Milliseconds 200
}

# --- dev server health -------------------------------------------------------
$base = "http://{0}:{1}/" -f $DevHost, $Port
try {
  $h = Invoke-RestMethod -Uri ($base + "health") -TimeoutSec 3
  Write-Host ("[cap] dev server ok: " + $base + "  pytracer=" + $h.engine.pytracer)
} catch {
  Write-Host ("[cap] WARNING dev server not reachable: " + $base + "health")
  Write-Host ("[cap]   start it with: python app/main.py --no-window --port " + $Port)
}

# --- pick a free CDP port (never fight a Chrome we do not own) ---------------
$profileDir = Join-Path $env:TEMP ("captool-" + $CdpPort)
# A leftover process from an interrupted run is ours (matched by profile dir): kill it.
Stop-OurChrome $profileDir
$tries = 0
while ((Test-DebugPort $CdpPort) -and $tries -lt 20) {
  Write-Host ("[cap] cdp port {0} busy (not ours), trying next" -f $CdpPort)
  $CdpPort++
  $profileDir = Join-Path $env:TEMP ("captool-" + $CdpPort)
  Stop-OurChrome $profileDir
  $tries++
}
if (Test-DebugPort $CdpPort) {
  Write-Error "no free CDP port found"
  exit 1
}

# Cold cache every run: a persisted profile can serve a stale index.html and the
# screenshots then look identical even though the source changed underneath.
if (Test-Path $profileDir) { Remove-Item -Recurse -Force $profileDir -ErrorAction SilentlyContinue }

$chromeArgs = @(
  '--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-sandbox',
  '--disable-extensions', '--disable-background-networking',
  '--disable-application-cache', '--disk-cache-size=1',
  '--force-color-profile=srgb', '--force-device-scale-factor=1',
  '--disable-features=Translate,MediaRouter,OptimizationHints',
  '--no-first-run', '--no-default-browser-check',
  "--remote-debugging-port=$CdpPort",
  "--user-data-dir=$profileDir",
  "--window-size=$Width,$Height",
  'about:blank'
)
Write-Host ("[cap] launching chrome headless, cdp={0}, profile={1}" -f $CdpPort, $profileDir)
Start-Process -FilePath $chrome -ArgumentList $chromeArgs -WindowStyle Hidden | Out-Null

$ok = $false
for ($i = 0; $i -lt 60; $i++) {
  Start-Sleep -Milliseconds 250
  if (Test-DebugPort $CdpPort) { $ok = $true; break }
}
if (-not $ok) {
  Write-Error "Chrome debug port $CdpPort did not come up"
  Stop-OurChrome $profileDir
  exit 1
}

if ($Html) {
  $Html = Resolve-AbsPath $Html
  if (-not (Test-Path $Html)) { Write-Error "Html file not found: $Html"; Stop-OurChrome $profileDir; exit 1 }
  Write-Host ("[cap] document override: " + $Html)
}

$exit = 1
try {
  if ($Smoke) {
    $smokeArgs = @(
      (Join-Path $here "smoke.mjs"),
      ("--baseUrl=" + $base),
      ("--cdpPort=" + $CdpPort),
      ("--width=" + $Width),
      ("--height=" + $Height),
      ("--json=" + (Join-Path $Out "smoke-report.json")),
      ("--failShots=" + (Join-Path $Out "_fail"))
    )
    if ($Html) { $smokeArgs += ("--html=" + $Html) }
    Write-Host "[cap] node smoke.mjs (functional regression)"
    & node @smokeArgs
  } else {
    $nodeArgs = @(
      (Join-Path $here "cap.mjs"),
      ("--baseUrl=" + $base),
      ("--out=" + $Out),
      ("--cdpPort=" + $CdpPort),
      ("--scenarios=" + $Scenarios),
      ("--width=" + $Width),
      ("--height=" + $Height)
    )
    if ($Scenario -and $Scenario.Count -gt 0) { $nodeArgs += ("--scenario=" + ($Scenario -join ",")) }
    if ($Only) { $nodeArgs += ("--only=" + $Only) }
    if ($NoShot) { $nodeArgs += "--noshot" }
    if ($Html) { $nodeArgs += ("--html=" + $Html) }
    Write-Host ("[cap] node cap.mjs " + ($Scenario -join ","))
    & node @nodeArgs
  }
  $exit = $LASTEXITCODE
  if ($null -eq $exit) { $exit = 0 }
} finally {
  if ($KeepChrome) {
    Write-Host ("[cap] keeping chrome alive on cdp {0} (profile {1})" -f $CdpPort, $profileDir)
  } else {
    Stop-OurChrome $profileDir
    Remove-Item -Recurse -Force $profileDir -ErrorAction SilentlyContinue
  }
}
Write-Host ("[cap] exit " + $exit)
exit $exit
