@echo off
:: 유튜브 트렌드 주간 리포트 실행 스크립트
:: Windows 작업 스케줄러에 이 파일을 등록해.

cd /d "%~dp0"

echo [%date% %time%] 리포트 시작 >> logs\scheduler.log

python tools\main.py

echo [%date% %time%] 리포트 종료 >> logs\scheduler.log
