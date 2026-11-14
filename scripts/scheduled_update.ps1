# 在这台电脑上抓取新澳门彩、有新期号时重训并推送到 GitHub。
# 由计划任务调用：每天 08:20、22:40，以及登录后。没有新开奖时不提交。
$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = "C:\Users\ASUS\AppData\Local\Programs\Python\Python312\python.exe"
$Git = "C:\Program Files\Git\cmd\git.exe"
$StateDir = Join-Path $env:LOCALAPPDATA "新澳门彩自动更新"
$LogFile = Join-Path $StateDir "update.log"
$LockFile = Join-Path $StateDir "update.lock"
$Managed = @(
    "data/newam6hc_5y_verified.csv",
    "data/newam6hc_5y.csv",
    "data/forecasts.json",
    "data/train_report.json",
    "models/hgb_special.pkl",
    "models/logreg_special.pkl"
)

New-Item -ItemType Directory -Force -Path $StateDir | Out-Null

function Write-Log {
    param([string]$Message)
    $line = "{0}  {1}{2}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message, [Environment]::NewLine
    $encoding = New-Object System.Text.UTF8Encoding $true
    if (Test-Path $LogFile) {
        $encoding = New-Object System.Text.UTF8Encoding $false
    }
    [System.IO.File]::AppendAllText($LogFile, $line, $encoding)
}

function Invoke-Git {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$GitArgs)
    & $Git -C $Root @GitArgs
    if ($LASTEXITCODE -ne 0) {
        throw "git $($GitArgs -join ' ') 失败，退出码 $LASTEXITCODE"
    }
}

function Invoke-Python {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$PyArgs)
    $start = New-Object System.Diagnostics.ProcessStartInfo
    $start.FileName = $Python
    $start.WorkingDirectory = $Root
    $start.UseShellExecute = $false
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $start.CreateNoWindow = $true
    $utf8 = New-Object System.Text.UTF8Encoding $false
    $start.StandardOutputEncoding = $utf8
    $start.StandardErrorEncoding = $utf8
    $start.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8"
    $start.EnvironmentVariables["PYTHONUTF8"] = "1"
    $quoted = foreach ($arg in $PyArgs) {
        if ($arg -match '[\s"]') { '"' + ($arg -replace '"', '\"') + '"' } else { $arg }
    }
    $start.Arguments = $quoted -join " "
    $proc = [System.Diagnostics.Process]::Start($start)
    $stdoutTask = $proc.StandardOutput.ReadToEndAsync()
    $stderrTask = $proc.StandardError.ReadToEndAsync()
    $proc.WaitForExit()
    $script:LASTEXITCODE = $proc.ExitCode
    return (($stdoutTask.Result + $stderrTask.Result).Trim())
}

if (Test-Path $LockFile) {
    $oldPid = Get-Content $LockFile -ErrorAction SilentlyContinue
    if ($oldPid -and (Get-Process -Id $oldPid -ErrorAction SilentlyContinue)) {
        Write-Log "已有任务在运行 (pid $oldPid)，本次跳过"
        exit 0
    }
}
Set-Content -Path $LockFile -Value $PID -Encoding ascii

try {
    Set-Location $Root
    Write-Log "开始检查新开奖"
    $env:PYTHONIOENCODING = "utf-8"
    $env:PYTHONUTF8 = "1"
    $env:GIT_TERMINAL_PROMPT = "0"

    $porcelain = & $Git -C $Root status --porcelain
    if ($LASTEXITCODE -ne 0) { throw "无法读取 git 状态" }
    if (-not $porcelain) {
        Invoke-Git pull --ff-only origin main
    }

    $updateText = Invoke-Python "scripts\update_newam6hc.py"
    if ($updateText) { Write-Log $updateText }
    if ($LASTEXITCODE -ne 0) { throw "采集失败，退出码 $LASTEXITCODE" }
    if ($updateText -notmatch "changed=True") {
        Write-Log "没有新开奖，结束"
        exit 0
    }

    Write-Log "发现新开奖，开始训练"
    $trainText = Invoke-Python -m ml.run_train --save-fit all
    if ($LASTEXITCODE -ne 0) { throw "训练失败，退出码 $LASTEXITCODE`n$trainText" }
    $exportText = Invoke-Python -m ml.export_forecasts
    if ($LASTEXITCODE -ne 0) { throw "导出预测失败，退出码 $LASTEXITCODE`n$exportText" }
    if ($exportText) { Write-Log $exportText }

    Invoke-Git add -- @Managed
    $staged = & $Git -C $Root diff --cached --name-only
    if ($LASTEXITCODE -ne 0) { throw "无法确认暂存文件" }
    if (-not $staged) {
        Write-Log "文件没有变化，不推送"
        exit 0
    }

    Invoke-Git commit -m "Update draws, retrain models, and rebuild forecasts."
    Invoke-Git push origin main
    Write-Log "已推送到 GitHub"
}
catch {
    Write-Log "失败: $($_.Exception.Message)"
    exit 1
}
finally {
    Remove-Item $LockFile -Force -ErrorAction SilentlyContinue
}
