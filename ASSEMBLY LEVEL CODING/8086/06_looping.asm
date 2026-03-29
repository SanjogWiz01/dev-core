include 'emu8086.inc'

.model small
.stack 100h

.data

.code
main proc

    mov ax, @data
    mov ds, ax ; till this step its all is basics

    mov cx, 5 ; this is a loop counter 

start:
    print 'hello'

    mov dl, 10h
    mov ah, 02h
    int 21h

    loop start ; automitacallly decreste the value of the cx by 1 in this linr

main endp
end main