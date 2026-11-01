@echo off
chcp 65001 >nul
title 助农AI平台 - 一键启动
echo.
echo  ==========================================
echo          助农 AI 平台 · 一键启动
echo  ==========================================
echo.

REM ── 1/3 后端 FastAPI（端口 8000）──
netstat -ano | findstr "LISTENING" | findstr ":8000" >nul 2>&1
if not errorlevel 1 (
    echo  [提示] 后端已在运行（端口 8000），跳过启动
) else (
    echo  [1/3] 启动后端服务 FastAPI ...
    start "助农AI平台-后端(8000)" /D "%~dp0backend" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
)

REM ── 2/3 前端 Vite（端口 5173）──
netstat -ano | findstr "LISTENING" | findstr ":5173" >nul 2>&1
if not errorlevel 1 (
    echo  [提示] 前端已在运行（端口 5173），跳过启动
) else (
    echo  [2/3] 启动前端服务 Vite ...
    start "助农AI平台-前端(5173)" /D "%~dp0frontend" cmd /k "npm run dev"
)

REM ── 3/3 等待服务就绪后打开浏览器 ──
echo  [3/3] 等待服务就绪 ...

set /a tries=0
:wait_backend
powershell -NoProfile -Command "try{Invoke-RestMethod 'http://127.0.0.1:8000/api/health' -TimeoutSec 2|Out-Null;exit 0}catch{exit 1}" >nul 2>&1
if not errorlevel 1 goto backend_ok
set /a tries+=1
if %tries% geq 15 (
    echo  [警告] 后端 30 秒内未就绪，请查看「助农AI平台-后端」窗口的报错信息
    goto open_browser
)
timeout /t 2 /nobreak >nul
goto wait_backend
:backend_ok
echo        后端已就绪 √

set /a tries=0
:wait_frontend
powershell -NoProfile -Command "try{Invoke-WebRequest 'http://127.0.0.1:5173/' -UseBasicParsing -TimeoutSec 2|Out-Null;exit 0}catch{exit 1}" >nul 2>&1
if not errorlevel 1 goto open_browser
set /a tries+=1
if %tries% geq 10 goto open_browser
timeout /t 1 /nobreak >nul
goto wait_frontend

:open_browser
start "" "http://127.0.0.1:5173"
echo.
echo  启动完成！浏览器将打开 http://127.0.0.1:5173
echo.
echo  停止服务：关闭「助农AI平台-后端」和「助农AI平台-前端」两个窗口
echo  （测试账号：farmertest / buyertest / admin，密码均为 123456）
echo.
pause
