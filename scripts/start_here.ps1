# 在另一台电脑上：安装运行所需依赖，抓取最新开奖，有新期号时训练，然后打开页面。
$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

function Resolve-Python {
    $attempts = @(
        @{ Name = "py"; Args = @("-3") },
        @{ Name = "python"; Args = @() },
        @{ Name = "python3"; Args = @() }
    )
    foreach ($attempt in $attempts) {
        if (-not (Get-Command $attempt.Name -ErrorAction SilentlyContinue)) { continue }
        $executable = & $attempt.Name @($attempt.Args) -c "import sys; print(sys.executable)"
        if ($LASTEXITCODE -eq 0 -and $executable) {
            return $executable.Trim()
        }
    }
    throw "没有找到 Python 3。请先安装 Python 3.12，并勾选 Add python.exe to PATH。https://www.python.org/downloads/"
}

function Resolve-Npm {
    foreach ($name in @("npm.cmd", "npm")) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command) { return $command.Source }
    }
    throw "没有找到 Node.js。请先安装 Node.js 22。https://nodejs.org/"
}

Write-Host "项目目录: $Root"
$Python = Resolve-Python
$Npm = Resolve-Npm
$env:PATH = "$(Split-Path $Python);$env:PATH"
Write-Host "Python: $Python"
Write-Host "npm: $Npm"

& $Python -c "import bs4, pandas, numpy, sklearn"
if ($LASTEXITCODE -ne 0) {
    Write-Host "正在安装 Python 依赖..."
    & $Python -m pip install -r (Join-Path $Root "requirements-app.txt")
    if ($LASTEXITCODE -ne 0) { throw "Python 依赖安装失败" }
}

if (-not (Test-Path (Join-Path $Root "web\node_modules"))) {
    Write-Host "正在安装网页依赖，第一次会久一些..."
    & $Npm ci --prefix (Join-Path $Root "web")
    if ($LASTEXITCODE -ne 0) { throw "网页依赖安装失败" }
}

Write-Host "正在采集最新开奖..."
$updateText = & $Python (Join-Path $Root "scripts\update_newam6hc.py") 2>&1 | Out-String
Write-Host $updateText
if ($LASTEXITCODE -ne 0) { throw "采集失败" }

$modelsReady = (Test-Path (Join-Path $Root "models\hgb_special.pkl")) -and
    (Test-Path (Join-Path $Root "models\logreg_special.pkl")) -and
    (Test-Path (Join-Path $Root "data\forecasts.json"))
if ($updateText -match "changed=True" -or -not $modelsReady) {
    Write-Host "开始训练，大约需要几分钟..."
    & $Python -m ml.run_train --save-fit all
    if ($LASTEXITCODE -ne 0) { throw "训练失败" }
    & $Python -m ml.export_forecasts
    if ($LASTEXITCODE -ne 0) { throw "导出预测失败" }
} else {
    Write-Host "没有新开奖，使用现有模型打开页面。"
}

Write-Host "正在打开页面。关闭这个窗口就会停止。"
& $Npm run dev --prefix (Join-Path $Root "web") -- --open --host 127.0.0.1
if ($LASTEXITCODE -ne 0) { throw "页面启动失败" }
