#!/bin/bash
set -e

echo "[MyOS] Assembling bootloader..."
mkdir -p build
nasm -f bin boot/boot.asm -o build/boot.bin

echo "[MyOS] Bootloader binary assembled (512 bytes)."
ls -l build/boot.bin

echo "[MyOS] Launching QEMU..."
qemu-system-x86_64 -drive format=raw,file=build/boot.bin -serial stdio
