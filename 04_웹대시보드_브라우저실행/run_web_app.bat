@echo off
chcp 65001 > nul
echo Azure 백업 모니터링 웹 대시보드
echo ===============================
echo 🌐 웹 브라우저에서 실행되는 대시보드
echo.

cd /d "%~dp0"

echo 📦 필요한 패키지 설치 확인 중...
python -c "import streamlit, plotly, pandas" 2>nul
if errorlevel 1 (
    echo ❌ 필요한 패키지가 설치되지 않았습니다.
    echo 📦 패키지 설치 중...
    pip install streamlit plotly pandas
    if errorlevel 1 (
        echo ❌ 패키지 설치 실패. 수동으로 설치해주세요:
        echo    pip install streamlit plotly pandas
        pause
        exit /b 1
    )
)

echo ✅ 패키지 확인 완료
echo.
echo 🚀 웹 대시보드 시작 중...
echo 📍 브라우저가 자동으로 열립니다.
echo 🛑 종료하려면 Ctrl+C를 누르세요.
echo.

streamlit run backup_monitor_web.py --server.port 8501 --server.headless false

echo.
echo 웹 대시보드가 종료되었습니다.
pause