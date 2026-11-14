# Package a Windows app that runs after unzipping. Torch and TensorFlow stay out.
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = "C:\Users\ASUS\AppData\Local\Programs\Python\Python312\python.exe"
Set-Location $Root

& npm.cmd --prefix web run build
if ($LASTEXITCODE -ne 0) { throw "web build failed" }

& $Python -m PyInstaller --noconfirm --clean --windowed --name MarkSixPredict `
    --collect-submodules bs4 `
    --collect-all sklearn `
    --collect-all webview `
    --hidden-import newam6hc_lib `
    --hidden-import desktop_server `
    --hidden-import scripts.update_newam6hc `
    --hidden-import ml.web_prediction `
    --hidden-import ml.run_train `
    --hidden-import ml.export_forecasts `
    --hidden-import ml.regular `
    --hidden-import ml.features `
    --hidden-import ml.probability `
    --hidden-import ml.evaluate `
    --hidden-import ml.baselines `
    --exclude-module torch `
    --exclude-module torchvision `
    --exclude-module torchaudio `
    --exclude-module tensorflow `
    --exclude-module tensorboard `
    --exclude-module matplotlib `
    --exclude-module cv2 `
    --exclude-module PySide6 `
    --exclude-module shiboken6 `
    --exclude-module PyQt5 `
    --exclude-module sympy `
    --exclude-module sqlalchemy `
    --exclude-module IPython `
    --exclude-module notebook `
    --exclude-module jupyter `
    --exclude-module pytest `
    --exclude-module numba `
    --exclude-module llvmlite `
    --exclude-module dask `
    --exclude-module pyarrow `
    --add-data "web\dist;web" `
    --add-data "data\newam6hc_5y_verified.csv;data" `
    --add-data "data\newam6hc_5y.csv;data" `
    --add-data "data\am6hc_5y_verified.csv;data" `
    --add-data "data\am6hc_5y.csv;data" `
    --add-data "data\macau6hc_168_verified.csv;data" `
    --add-data "data\macau6hc_168.csv;data" `
    --add-data "data\model_benchmark.json;data" `
    --add-data "data\model_benchmark.csv;data" `
    --add-data "data\forecasts.json;data" `
    --add-data "data\regular_benchmark.json;data" `
    --add-data "data\train_report.json;data" `
    --add-data "data\next_reference.json;data" `
    --add-data "data\prediction_reference.json;data" `
    --add-data "models\hgb_special.pkl;models" `
    --add-data "models\logreg_special.pkl;models" `
    serve_app.py

& $Python -c "import shutil; from pathlib import Path; root=Path(r'$Root'); out=root/'dist'/'MarkSixPredict'; [shutil.copy2(src, out/src.name) for src in (root/'portable').iterdir() if src.suffix.lower() in {'.bat', '.txt'}]"
Write-Output "built"
