[org 0x7c00]          ; BIOS loads the bootloader at physical address 0x7c00

section .text
global _start

_start:
    ; Set up segment registers to 0
    xor ax, ax
    mov ds, ax
    mov es, ax
    mov ss, ax
    mov sp, 0x7c00    ; Stack grows down from 0x7c00

    ; Clear screen (BIOS Interrupt 0x10, AH=0x00, AL=0x03 - 80x25 text mode)
    mov ax, 0x0003
    int 0x10

    ; Print message to the screen
    mov si, msg_screen
    call print_string

    ; Print message to the serial port COM1
    mov si, msg_serial
    call print_serial_string

    ; Disable interrupts and halt
    cli
.halt:
    hlt
    jmp .halt

; Prints a null-terminated string to the screen via BIOS int 0x10 (teletype)
print_string:
    push ax
    push bx
    mov ah, 0x0e      ; BIOS teletype output function
    mov bh, 0x00      ; Page number 0
    mov bl, 0x07      ; Normal attribute
.loop:
    lodsb             ; Load byte from SI into AL, increment SI
    cmp al, 0         ; Check if null terminator
    je .done
    int 0x10          ; Call BIOS video services
    jmp .loop
.done:
    pop bx
    pop ax
    ret

; Prints a null-terminated string to the serial port COM1 (0x3f8)
print_serial_string:
    push ax
    push dx
.loop:
    lodsb
    cmp al, 0
    je .done
    mov cl, al
    
    ; Wait for transmit register to be empty (Line Status Register COM1 is 0x3FD)
    mov dx, 0x3fd
.wait:
    in al, dx
    test al, 0x20
    jz .wait
    
    ; Write character to transmitter holding register (COM1 port is 0x3f8)
    mov dx, 0x3f8
    mov al, cl
    out dx, al
    jmp .loop
.done:
    pop dx
    pop ax
    ret

msg_screen:
    db "MyOS Stage 1 Bootloader - System is alive.", 0x0d, 0x0a
    db "CPU is in 16-bit real mode. Next step: protected mode + kernel.", 0x0d, 0x0a, 0

msg_serial:
    db "MyOS Stage 1 Bootloader - System is alive.", 0x0a
    db "CPU is in 16-bit real mode. Next step: protected mode + kernel.", 0x0a, 0

; Boot sector padding
times 510-($-$$) db 0  ; Pad rest of the 512 bytes with zeros
dw 0xaa55             ; Mandatory boot signature (little-endian: 0x55, 0xAA)
