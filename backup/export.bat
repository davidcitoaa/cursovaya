@echo off
:loop

REM Запускаем скрипт Python
"D:\'Учеба'\'Универ'\'3 курс'\'5 семестр'\'БД'\'Курсач'\cursovaya\.venv\Scripts\python.exe" "D:\'Учеба'\'Универ'\'3 курс'\'5 семестр'\'БД'\'Курсач'\cursovaya\backup_script.py"

REM Ждем 60 секунд (1 минута) перед следующим запуском
timeout /t 60

REM Повторяем цикл
goto loop
