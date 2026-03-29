include 'emu8086.inc'

.model small
.stack 100h

.data

.code
main proc

    ; initialize data segment
    mov ax, @data
    mov ds, ax

    print 'Enter your character: '

    mov ah, 01h      ; read character from keyboard
    int 21h          ; AL = input character

    mov dl, al       ; move input to DL for display
    mov ah, 02h      ; display character function
    int 21h

    ; exit program
    mov ah, 4ch
    int 21h

main endp
end main