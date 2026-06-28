@echo off
echo [MyOS] Assembling bootloader...
if not exist build mkdir build
"C:\Users\thora\AppData\Local\bin\nasm.exe" -f bin boot\boot.asm -o build\boot.bin

if errorlevel 1 (
    echo [MyOS] Assembly failed. Please ensure nasm is installed.
    pause
    exit /b 1
)

echo [MyOS] Bootloader binary assembled (512 bytes).
dir build\boot.bin

echo [MyOS] Launching QEMU...
"C:\Program Files\qemu\qemu-system-x86_64.exe" -drive format=raw,file=build\boot.bin -serial stdio
if errorlevel 1 (
    echo [MyOS] Failed to launch QEMU.
    pause
)
