include 'emu8086.inc'

.model small
.stack 100h

.data
msg db 'Computer Engineering is easy$'

.code
main proc

    mov ax, @data
    mov ds, ax

    mov si, offset msg   ; SI points to string

next_char:
    mov al, [si]         ; load character
    cmp al, '$'          ; end of string check
    je exit

    cmp al, ' '          ; check space
    je new_line

    mov dl, al           ; print character
    mov ah, 02h
    int 21h
    jmp continue

new_line:
    ; print newline (CR + LF)

    mov dl, 0Dh
    mov ah, 02h
    int 21h

    mov dl, 0Ah
    mov ah, 02h
    int 21h

continue:
    inc si
    jmp next_char

exit:
    mov ah, 4Ch
    int 21h

main endp
end main