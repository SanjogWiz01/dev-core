; question 
; add two 8bit number from memory location 2050 h znd 2051 h and store the  result ay memory location 3050h

LDA 2050H     ; Load first number into A
MOV B, A     ; Save first number in B
LDA 2051H     ; Load second number into A
ADD B         ; A = A + B
STA 3050H     ; Store result at 3050H
HLT

; answer for not carry operation 

; for carry operation
LDA 2050H      ; Load first number into A
MOV B, A      ; Save first number in B
LDA 2051H      ; Load second number into A
ADD B          ; A = A + B      ; Store sum at 3050H

MVI A, 00H     ; Clear A
ADC A          ; A = A + carry
STA 3051H      ; Store carry at 3051H

HLT
