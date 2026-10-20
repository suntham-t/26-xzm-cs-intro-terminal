# =====================================================================
#  智能计算概论学习终端 —— 打包脚本（PyInstaller onefile + 桌面快捷方式）
#
#  用法（在任意目录）：
#      powershell -ExecutionPolicy Bypass -File D:\opencode\course-terminal\app\build.ps1
#      可选参数： -NoShortcut  -Clean  -Name "计算概论学习终端"  -SkipDeps
#
#  产物：
#      D:\opencode\course-terminal\app\dist\计算概论学习终端.exe
#      桌面快捷方式「计算概论学习终端.lnk」
#
#  注意：web\ 与 content\ 是别的代理的目录，本脚本只读、只打包，不写。
#        如果 web\index.html 还不存在，会**警告但不失败**（exe 里 /  会显示一句人话）。
# =====================================================================
[CmdletBinding()]
param(
    [string]$Name = "计算概论学习终端",
    [switch]$Clean,
    [switch]$NoShortcut,
    [switch]$SkipDeps,
    # 自测用：拿别处的 web\ / content\ 顶替（默认就是项目的 web\ / content\）
    [string]$WebSource = "",
    [string]$ContentSource = ""
)

$ErrorActionPreference = "Stop"
# 本文件必须存成 **UTF-8 with BOM** —— Windows PowerShell 5.1 读无 BOM 的 .ps1
# 会按系统 ANSI 代码页（中文系统是 GBK）解码，脚本里的中文会变乱码并直接解析失败。
# ★ 用"替换文本"的方式改完本文件后，务必确认首字节仍是 EF BB BF 且 CRLF 还在
#   （丢了 BOM 的症状：本文件自己能跑，但 PS 5.1 下解析出 20+ 个乱码错误）。
try { [Console]::OutputEncoding = [Text.UTF8Encoding]::new() } catch { }

# 冒烟测试里凡是碰 /open 的地方都别真去开用户的浏览器：这个路由的语义就是
# "交给系统默认浏览器"。目前只测了危险 scheme（应 400、不开），但先把开关设上，
# 免得以后有人加了正向断言，就变成"每次打包弹一个 cs101.openjudge.cn 标签页"。
$env:CT_NO_BROWSER = "1"

$AppDir  = $PSScriptRoot
$Root    = Split-Path $AppDir -Parent
$WebDir  = Join-Path $Root "web"
$Content = Join-Path $Root "content"
$Pytutor = "D:\opencode\tools\pytutor"
$MainPy  = Join-Path $AppDir "main.py"
if ($WebSource)     { $WebDir = $WebSource }
if ($ContentSource) { $Content = $ContentSource }
$WorkDir = Join-Path $env:TEMP "ct-build"
$DistDir = Join-Path $AppDir "dist"
$SpecDir = Join-Path $env:TEMP "ct-build-spec"

function Say($msg, $color = "Gray") { Write-Host $msg -ForegroundColor $color }
function Step($msg) { Write-Host ""; Write-Host "==> $msg" -ForegroundColor Cyan }

Say "智能计算概论学习终端 · 打包" Cyan
Say "  项目根目录 : $Root"
Say "  app 目录   : $AppDir"
Say "  临时目录   : $WorkDir（$env:TEMP 下，不污染项目）"

# ---------------------------------------------------------------- 0. 前置检查
Step "0/5 前置检查"

if (-not (Test-Path $MainPy))  { throw "找不到 $MainPy" }
Say "  [ok] main.py"

# 上一轮跑着的 exe 会锁住 dist\*.exe，PyInstaller 报 WinError 5 拒绝访问。
# 先自动收掉（只杀我们自己这个名字的进程），免得打包莫名其妙失败。
$running = @(Get-Process -Name $Name -ErrorAction SilentlyContinue)
if ($running.Count -gt 0) {
    Say "  收掉正在运行的 $($running.Count) 个「$Name」进程（否则 dist\*.exe 被锁）" Yellow
    $running | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

$missing = @()
if (-not (Test-Path (Join-Path $WebDir "index.html"))) { $missing += "$WebDir\index.html" }
if (-not (Test-Path (Join-Path $Content "ch03.json"))) { $missing += "$Content\ch03.json" }
if ($missing.Count -gt 0) {
    Say "  [警告] 以下文件还不存在（别的代理尚未产出），仍会打包，运行时相应页面会显示一句人话：" Yellow
    $missing | ForEach-Object { Say "         - $_" Yellow }
}

$TutorFiles = @("pytracer.py", "explain.py", "server.py", "viewer.html")
foreach ($f in $TutorFiles) {
    if (-not (Test-Path (Join-Path $Pytutor $f))) { throw "找不到可视化引擎文件 $Pytutor\$f（只读复用，不要改它）" }
}
Say "  [ok] 可视化引擎 4 个文件都在 $Pytutor"

# 图标：缺了 PyInstaller 会**静默**用它的默认图标（不报错），所以这里必须显式检查。
# 文件由 app\make-icon.py 从美术稿生成，别手改。
$IconFile = Join-Path $AppDir "assets\icon.ico"
if (-not (Test-Path $IconFile)) {
    throw "找不到图标 $IconFile —— 先跑：python app\make-icon.py"
}
Say ("  [ok] 图标 {0}（{1:N0} 字节）" -f $IconFile, (Get-Item $IconFile).Length)

foreach ($d in @($WorkDir, $DistDir, $SpecDir)) {
    if ($Clean -and (Test-Path $d)) { Remove-Item $d -Recurse -Force }
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
}

# ---------------------------------------------------------------- 1. 依赖
Step "1/5 依赖"
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { throw "PATH 里找不到 python" }
Say "  python : $py"
Say ("  版本   : " + (& python --version 2>&1))
if ($SkipDeps) {
    Say "  [跳过] -SkipDeps" Yellow
} else {
    & python -m pip install --disable-pip-version-check -q -r (Join-Path $AppDir "requirements.txt")
    if ($LASTEXITCODE -ne 0) { throw "pip install 失败（exit $LASTEXITCODE）" }
    Say "  [ok] requirements.txt 已装齐"
}

$ver = & python -c "import importlib.metadata as m; print('pywebview', m.version('pywebview'), '| pyinstaller', m.version('pyinstaller'))" 2>&1
if ($LASTEXITCODE -ne 0) { $ver = (& python -c "import webview, PyInstaller; print('webview / PyInstaller 均可导入')" 2>&1) }
Say "  [ok] $ver"

# ---------------------------------------------------------------- 2. PyInstaller
Step "2/5 PyInstaller 打包（onefile / windowed）"

# 引擎文件先复制到临时目录再整目录 --add-data，避免中文路径 + 通配符踩坑
$Stage = Join-Path $WorkDir "tutor"
if (Test-Path $Stage) { Remove-Item $Stage -Recurse -Force }
New-Item -ItemType Directory -Path $Stage -Force | Out-Null
foreach ($f in $TutorFiles) { Copy-Item (Join-Path $Pytutor $f) $Stage }
Say "  引擎暂存 : $Stage"

# 重建流水线也要烤进去（方案丙）：一键重建在 app **同进程**跑 _build-json.py，
# 所以它必须能被 find_asset("content", "notes/_build-json.py") 找到。
$RebuildStage = Join-Path $WorkDir "rebuild-content"
if (Test-Path $RebuildStage) { Remove-Item $RebuildStage -Recurse -Force }
New-Item -ItemType Directory -Path (Join-Path $RebuildStage "notes") -Force | Out-Null
$RebuildFiles = @("_build-json.py", "_chapters.json", "_point-ids.txt")
$rebuildMissing = @()
foreach ($f in $RebuildFiles) {
    $src = Join-Path $Content "notes\$f"
    if (Test-Path $src) { Copy-Item $src (Join-Path $RebuildStage "notes") }
    else { $rebuildMissing += "content\notes\$f" }
}

# ★ 讲义正文必须**打真的进去**，绝不能放占位文件。
#   这里曾经塞过一个 299 字节的"占位讲义"（理由是"重建时会从课程站取回真的"），
#   结果 exe 内嵌的就是那 299 字节 —— 用户不重建的话，讲义原文直接是坏的。
#   它是在验收里露出来的：/content/notes/ch03.md 返回 299 B 而不是 56,657 B。
#   三章讲义加起来才 ~170KB，对 118MB 的 exe 毫无影响，没有理由不放真的。
#   一并带上 100days 索引：build_refs() 缺它会把每个知识点的「100 Days 关联阅读」
#   **静默清空**（只打印一行就返回空集合），而 id/点数/结构全对，验收发现不了。
foreach ($ch in @("ch01", "ch02", "ch03")) {
    $src = Join-Path $Content "notes\$ch.md"
    if (Test-Path $src) { Copy-Item $src (Join-Path $RebuildStage "notes") }
    else { $rebuildMissing += "content\notes\$ch.md" }
}
$IdxSrc = Join-Path $Content "100days\index.json"
if (Test-Path $IdxSrc) {
    New-Item -ItemType Directory -Path (Join-Path $RebuildStage "100days") -Force | Out-Null
    Copy-Item $IdxSrc (Join-Path $RebuildStage "100days")
} else {
    $rebuildMissing += "content\100days\index.json"
}
if ($rebuildMissing.Count -gt 0) {
    Say "  [警告] 重建流水线缺文件（exe 里将没有一键重建）：" Yellow
    $rebuildMissing | ForEach-Object { Say "         - $_" Yellow }
} else {
    Say "  重建暂存 : $RebuildStage（流水线 + 注册表 + id 基线 + 三章讲义 + 100days 索引）"
}

$pyArgs = @(
    "--noconfirm", "--onefile", "--windowed",
    "--name", $Name,
    "--distpath", $DistDir,
    "--workpath", (Join-Path $WorkDir "work"),
    "--specpath", $SpecDir,
    # 引擎暂存目录一定存在
    "--add-data", "$Stage;tutor",
    # 重建流水线（目录会与后面的 content 合并进 _MEIPASS\content\）
    "--add-data", "$RebuildStage;content",
    # 打包后 main.py 用 sys._MEIPASS\tutor 当 sys.path，再 import pytracer/explain
    "--paths", $Stage,
    # 应用图标。★ 必须是**多尺寸** .ico：Windows 按场景挑帧（任务栏 16px、
    #   资源管理器超大图标 256px），只放一张 256 会在大图标边缘发糊、小图标丢细节。
    #   这个文件由 app\make-icon.py 从原始美术稿生成，**不要手改**。
    "--icon", (Join-Path $AppDir "assets\icon.ico"),
    # pywebview 的 Windows 后端是动态 import 的，PyInstaller 静态分析看不见
    "--hidden-import", "webview.platforms.edgechromium",
    "--hidden-import", "webview.platforms.winforms",
    "--hidden-import", "clr_loader",
    "--collect-submodules", "webview",
    # 方案丙：pypdfium2 在**运行期**才 import，且它的原生库 pypdfium2_raw\pdfium.dll
    # 是动态加载的 —— 两者静态分析都看不见，必须显式收进来，否则 exe 里
    # rebuild_supported 会是 false（或更糟：跑到渲染那一步才崩）。
    "--collect-submodules", "pypdfium2",
    "--collect-data", "pypdfium2_raw",
    "--hidden-import", "pypdfium2_raw",
    "$MainPy"
)

# web\ 与 content\ 可能还不存在（别的代理在写）。PyInstaller 遇到 --add-data
# 指向不存在的目录会**直接报错退出**，所以这里必须先判存在再拼参数。
foreach ($pair in @(@($WebDir, "web"), @($Content, "content"))) {
    if (Test-Path $pair[0]) {
        $pyArgs += @("--add-data", "$($pair[0]);$($pair[1])")
    } else {
        Say "  [警告] $($pair[0]) 不存在 → 不打包进 exe（该代理产出后重跑本脚本即可）" Yellow
    }
}

Say "  pyinstaller $($pyArgs -join ' ')" DarkGray
& python -m PyInstaller @pyArgs
if ($LASTEXITCODE -ne 0) { throw "PyInstaller 失败（exit $LASTEXITCODE）" }

$Exe = Join-Path $DistDir "$Name.exe"
if (-not (Test-Path $Exe)) { throw "没找到产物 $Exe" }
$size = [math]::Round((Get-Item $Exe).Length / 1MB, 1)
Say "  [ok] $Exe（$size MB）" Green

# ---------------------------------------------------------------- 3. 冒烟测试（真的起一次 exe）
Step "3/5 冒烟测试（启动 exe → 探端口 → /health → /tutor）"

$PortFile = Join-Path $env:TEMP "course-terminal-port.txt"
if (Test-Path $PortFile) { Remove-Item $PortFile -Force }

$proc = Start-Process -FilePath $Exe -PassThru
$port = $null
for ($i = 0; $i -lt 400; $i++) {
    Start-Sleep -Milliseconds 150
    if (Test-Path $PortFile) {
        $line = (Get-Content $PortFile -First 1) -as [int]
        if ($line -gt 0 -and $line -ne $proc.Id) {
            $port = $line
            # 确认这个端口上确实是我们的服务（而不是别的进程占着同一个号）
            try {
                $h = Invoke-RestMethod "http://127.0.0.1:$port/health" -TimeoutSec 3
                if ($h.ok) { break } else { $port = $null }
            } catch { $port = $null }
        }
    }
    if ($i -ge 266) { break }   # 最多等 40 秒，别把打包脚本挂死
    if ($proc.HasExited) { break }
}

if ($port) {
    Say "  exe 自己选的端口 = $port（端口文件 $PortFile）" Green
    try {
        $h = Invoke-RestMethod "http://127.0.0.1:$port/health" -TimeoutSec 5
        Say ("  /health    -> ok=$($h.ok) frozen=$($h.frozen) engine=$($h.engine | ConvertTo-Json -Compress)")
        Say ("  /health    -> log=$($h.log) streams=$($h.streams | ConvertTo-Json -Compress)")
        Say ("  /          -> $((Invoke-WebRequest "http://127.0.0.1:$port/" -UseBasicParsing -TimeoutSec 5).StatusCode)（web/index.html）")
    } catch { Say "  [失败] /health 或 / : $_" Red }

    try {
        $body = '{"code":"x = [1,2,3]\nfor i in x:\n    print(i*i)\n","stdin":""}'
        $run = Invoke-RestMethod "http://127.0.0.1:$port/run" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 30
        $hasExplain = @($run.steps[0].PSObject.Properties.Name) -contains "explain"
        Say ("  /run       -> ok=$($run.ok) steps=$($run.steps.Count) 步骤带 explain=$hasExplain error_cn键=$(@($run.PSObject.Properties.Name) -contains 'error_cn')")
    } catch { Say "  [失败] /run : $_" Red }

    # 回归判据：windowed 打包后三个标准流都是 None → input() 会抛 RuntimeError: lost sys.*
    # （stdout/stderr/stdin 谁先撞上 None 就抛谁）。这条不合格，「作业陪跑」场景全废。
    try {
        $icode = "n = int(input())`nfor _ in range(n):`n    a, b = map(int, input().split())`n    print(a + b)`n"
        $ibody = @{ code = $icode; stdin = "2`n1 2`n3 4`n" } | ConvertTo-Json -Compress
        $irun = Invoke-RestMethod "http://127.0.0.1:$port/run" -Method Post -ContentType "application/json" -Body $ibody -TimeoutSec 30
        $ishow = $irun.stdout_final -replace "`r?`n", '\n'
        if ($irun.kind -eq "ok" -and $irun.stdout_final -eq "3`n7`n") {
            Say "  /run input -> kind=ok steps=$($irun.steps.Count) stdout=[$ishow]  ✅" Green
        } else {
            Say "  /run input -> kind=$($irun.kind) steps=$($irun.steps.Count) stdout=[$ishow] error=$($irun.error | ConvertTo-Json -Compress)" Red
            Say "  [失败] input() 回归！打包后标准流没补上（RuntimeError: lost sys.*）" Red
        }
    } catch { Say "  [失败] /run input() : $_" Red }

    # 内置 REPL（/repl）：持久性 + 死循环守卫 + 中文报错，三条硬判据
    try {
        function Repl([string]$c) {
            $b = @{ code = $c } | ConvertTo-Json -Compress
            return Invoke-RestMethod "http://127.0.0.1:$port/repl" -Method Post -ContentType "application/json" -Body $b -TimeoutSec 60
        }
        Invoke-RestMethod "http://127.0.0.1:$port/repl/reset" -Method Post -ContentType "application/json" -Body '{}' -TimeoutSec 10 | Out-Null
        Repl "a = 1" | Out-Null
        $r1 = Repl "a + 1"
        Say "  /repl      -> 持久性 a+1 => out=[$(($r1.out) -replace "`r?`n", '\n')]"
        Repl "import math" | Out-Null
        $r2 = Repl "1/0"
        Say "  /repl      -> 中文报错 title=$($r2.error_cn.title)"
        $sw = [Diagnostics.Stopwatch]::StartNew()
        $r3 = Repl "while True: pass"
        $sw.Stop()
        $secs = [math]::Round($sw.Elapsed.TotalSeconds, 2)
        if ($r1.out -eq "2`n" -and $r3.ok -eq $false -and $secs -lt 10) {
            Say "  /repl      -> 死循环守卫 ${secs}s 中止，cn=$($r3.error_cn.title)  ✅" Green
        } else {
            Say "  /repl      -> ok=$($r3.ok) ${secs}s out=[$($r1.out)] cn=$($r3.error_cn.title)" Red
            Say "  [失败] REPL 回归（持久性 / 死循环守卫）" Red
        }
    } catch { Say "  [失败] /repl : $_" Red }

    try {
        # 注意：Windows PowerShell 5.1 的 Invoke-WebRequest 不带 -UseBasicParsing 会去调
        # IE 引擎（无 IE 的机器上抛 NullReferenceException），必须加这个开关。
        $tutor = Invoke-WebRequest "http://127.0.0.1:$port/tutor?code=print(1)" -UseBasicParsing -TimeoutSec 10
        $hasBridge = $tutor.Content.Contains('course-terminal nav bridge')
        $hasPill = $tutor.Content.Contains('id="ctBackPill"')
        Say ("  /tutor     -> $($tutor.StatusCode)  $($tutor.RawContentLength) bytes 导航桥=$hasBridge 药丸=$hasPill")
        if (-not ($hasBridge -and $hasPill)) { Say "  [失败] /tutor 注入不完整（导航桥或药丸缺了）" Red }
    } catch { Say "  [失败] /tutor : $_" Red }

    # 外链安全边界：危险 scheme 必须 400（且服务端不该去调浏览器 —— 由 attempts 计数器保证）
    # 注意：Windows PowerShell 5.1 的 Invoke-WebRequest 遇到 4xx 会**抛异常**，
    # 状态码必须从异常里取；用 -ErrorAction SilentlyContinue 会让 $bad 为空、拿不到码。
    try {
        $c1 = (Invoke-WebRequest "http://127.0.0.1:$port/open/count" -UseBasicParsing -TimeoutSec 10).Content | ConvertFrom-Json
        $code = 0
        try {
            $bad = Invoke-WebRequest "http://127.0.0.1:$port/open?url=javascript%3Aalert%281%29" -UseBasicParsing -TimeoutSec 10
            $code = [int]$bad.StatusCode
        } catch {
            if ($_.Exception.Response) { $code = [int]$_.Exception.Response.StatusCode }
        }
        $c2 = (Invoke-WebRequest "http://127.0.0.1:$port/open/count" -UseBasicParsing -TimeoutSec 10).Content | ConvertFrom-Json
        Say ("  /open      -> 危险 scheme HTTP $code（应 400）；attempts $($c1.attempts)->$($c2.attempts)（应不变）")
        if ($code -ne 400 -or $c1.attempts -ne $c2.attempts) { Say "  [失败] /open 安全边界没拦住" Red }
    } catch { Say "  [失败] /open : $_" Red }
} else {
    Say "  [警告] 没探到端口（可能这台机器没有图形界面/窗口起不来）" Yellow
    Say "         进程 HasExited=$($proc.HasExited)" Yellow
}

if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue }
if (Test-Path $PortFile) { Remove-Item $PortFile -Force }

# ---------------------------------------------------------------- 4. 桌面快捷方式
Step "4/5 桌面快捷方式"

if ($NoShortcut) {
    Say "  [跳过] -NoShortcut" Yellow
} else {
    $desktop = [Environment]::GetFolderPath("Desktop")
    $lnk = Join-Path $desktop "$Name.lnk"
    $shell = New-Object -ComObject WScript.Shell
    $sc = $shell.CreateShortcut($lnk)
    $sc.TargetPath       = $Exe
    $sc.WorkingDirectory = $DistDir
    $sc.IconLocation     = "$Exe,0"
    $sc.Description      = "智能计算概论学习终端（双击即用，关窗即退出）"
    $sc.Save()
    if (Test-Path $lnk) {
        Say "  [ok] $lnk" Green
    } else {
        Say "  [失败] 快捷方式没建出来" Red
    }
}

# ---------------------------------------------------------------- 5. 收尾
Step "5/5 完成"
Say "  exe      : $Exe"
Say "  体积     : $size MB"
Say "  双击快捷方式即可使用；关窗即退出进程（无托盘、无开机自启）"
Say "  端口会自动从 8770 起找空闲端口，当前端口写在 $PortFile"
