@echo off
echo ========================================
echo HandMouse EXE Olusturucu
echo ========================================
echo.
echo EXE dosyasi olusturuluyor...
echo Bu islem birkaç dakika surebilir.
echo.

py -3.10 build_exe.py

echo.
echo ========================================
echo TAMAMLANDI!
echo ========================================
echo.
echo dist\HandMouse.exe dosyasina cift tiklayin!
echo.
pause
