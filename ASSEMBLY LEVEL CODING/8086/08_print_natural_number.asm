include 'emu8086.inc'

.model small
.stack 100h

.data

.code
main proc

    mov ax, @data
    mov ds, ax

    mov cx, 10        ; loop counter = 10
    mov bl, 1         ; starting number = 1

start:
    mov al, bl        ; move number to AL
    add al, 30h       ; convert to ASCII

    mov dl, al
    mov ah, 02h
    int 21h           ; print number

    ; print space
    mov dl, ' '
    mov ah, 02h
    int 21h

    inc bl            ; next number
    loop start        ; CX = CX - 1

    mov ah, 4Ch
    int 21h

main endp
end main