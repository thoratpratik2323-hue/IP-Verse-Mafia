@echo off
echo [MyOS] Assembling bootloader...
if not exist build mkdir build
nasm -f bin boot\boot.asm -o build\boot.bin

if errorlevel 1 (
    echo [MyOS] Assembly failed. Please ensure nasm is installed and in PATH.
    pause
    exit /b 1
)

echo [MyOS] Bootloader binary assembled (512 bytes).
dir build\boot.bin

echo [MyOS] Launching QEMU...
qemu-system-x86_64 -drive format=raw,file=build\boot.bin -serial stdio
if errorlevel 1 (
    echo [MyOS] Failed to launch QEMU. Please ensure QEMU is installed and in PATH.
    pause
)
