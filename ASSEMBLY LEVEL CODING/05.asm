 Write a program to load memory locations 7090 H and 7080 H with data 40H and 50H and then swap these 
data.
lxi h, 7090h  ; Load HL register pair with address 7090H
mvi m, 40h    ; Store 40H at memory location 7090H
lxi h, 7080h  ; Load HL register pair with address 7080H
mvi m, 50h    ; Store 50H at memory location 7080H
; Now swap the data
lxi h, 7090h  ; Load HL register pair with address 7090
mov a, m      ; Load accumulator with data from 7090H (40H)
lxi h, 7080h  ; Load HL register pair with address 7080
mov b, m      ; Load register B with data from 7080H (50H)
lxi h, 7090h  ; Load HL register pair with address 7090
mov m, b      ; Store data from register B (50H) into 7090H
lxi h, 7080h  ; Load HL register pair with address 7080
mov m, a      ; Store data from accumulator (40H) into 7080H
hlt            ; Halt the program
; End of program
                                      






















                                      
 MVI H, 70H 
MVI L, 90H 
MVI A, 40H 
MOV M, A 
MOV C, M 
MVI L, 80H 
MVI B, 50H 
MOV M, B 
MOV D, M
 MOV M, C 
MVI L, 90H 
MOV M, D 
HLT