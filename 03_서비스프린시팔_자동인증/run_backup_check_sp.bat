@echo off
chcp 65001 > nul
echo Azure 백업 모니터링 자동화 시스템 (Service Principal)
echo ====================================================
echo 🔒 자동 인증 - 브라우저 팝업 없음
echo.

cd /d "%~dp0"

python backup_monitor_sp.py

echo.
echo 실행 완료! 아무 키나 누르면 창이 닫힙니다.
pause > nul