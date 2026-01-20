@echo off
REM 🧠 ЛОГИКА: запускаем движок из папки проекта, чтобы engine_log.txt лежал рядом с engine_main.py

set ENGINE_DIR=C:\Users\Boris\Desktop\DragonEngine
pushd %ENGINE_DIR%

pythonw.exe engine_main.py

popd
exit