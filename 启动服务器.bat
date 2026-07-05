@echo off
cd /d "%~dp0"
echo ============================================
echo   小区间势段信号系统 — 手机Web版
echo ============================================
echo.
echo 正在安装依赖（首次运行可能需要几分钟）...
pip install -q flask pandas numpy requests openpyxl 2>nul
echo.
python app.py
pause
