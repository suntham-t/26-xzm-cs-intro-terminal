# shot.ps1 -- launch an isolated headless Chrome, drive a page via CDP, screenshot, clean up.
#
# Usage:
#   .\shot.ps1 -Url http://127.0.0.1:8770/ -Out out.png
#   .\shot.ps1 -Url http://127.0.0.1:8770/ -Out play.png -JsFile steps.js -WaitMs 2500
#
# -JsFile holds JS to run inside the page (may use await; it is wrapped in an async IIFE
# by the caller's file, not here -- just write a self-invoking async function).
#
# NOTE: keep this file ASCII-only. Windows PowerShell 5.1 reads .ps1 as ANSI/GBK when
# there is no BOM, which corrupts any non-ASCII text and can break the parser.

param(
  [Parameter(Mandatory = $true)][string]$Url,
  [Parameter(Mandatory = $true)][string]$Out,
  [int]$WaitMs = 2500,
  [string]$JsFile = "",
  [int]$Width = 1500,
  [int]$Height = 1000,
  [int]$Port = 9223
)

$ErrorActionPreference = 'Continue'
$chrome = "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
if (-not (Test-Path $chrome)) { Write-Error "Chrome not found: $chrome"; exit 1 }

$profileDir = "$env:TEMP\ptchrome-$Port"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not (Test-Path (Join-Path $here "drive2.mjs"))) { $here = "D:\opencode\course-terminal\_redesign\tools" }

function Stop-OurChrome {
  Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -and $_.CommandLine.Contains($profileDir) } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
}

Stop-OurChrome
Start-Sleep -Milliseconds 300

# Wipe the profile dir so Chrome has a COLD HTTP cache every run.
# Without this, a persisted profile can serve a stale viewer.html and the
# screenshots look identical even though the page changed underneath.
if (Test-Path $profileDir) {
  Remove-Item -Recurse -Force $profileDir -ErrorAction SilentlyContinue
}

$chromeArgs = @(
  '--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-sandbox',
  '--disable-extensions', '--disable-background-networking',
  '--disable-application-cache', '--disk-cache-size=1',
  "--remote-debugging-port=$Port",
  "--user-data-dir=$profileDir",
  "--window-size=$Width,$Height",
  'about:blank'
)
Start-Process -FilePath $chrome -ArgumentList $chromeArgs -WindowStyle Hidden | Out-Null

$ok = $false
for ($i = 0; $i -lt 40; $i++) {
  Start-Sleep -Milliseconds 300
  try {
    $null = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/json/version" -TimeoutSec 2
    $ok = $true
    break
  } catch { }
}
if (-not $ok) {
  Write-Error "Chrome debug port $Port did not come up"
  Stop-OurChrome
  exit 1
}

$env:CDP_PORT = "$Port"
if ($JsFile -and (Test-Path $JsFile)) {
  $env:PAGE_JS_FILE = (Resolve-Path $JsFile).Path
} else {
  Remove-Item Env:PAGE_JS_FILE -ErrorAction SilentlyContinue
}

$env:PAGE_W = "$Width"
$env:PAGE_H = "$Height"
& node "$here\drive2.mjs" $Url $Out "$WaitMs"
$code = $LASTEXITCODE

Stop-OurChrome
exit $code
