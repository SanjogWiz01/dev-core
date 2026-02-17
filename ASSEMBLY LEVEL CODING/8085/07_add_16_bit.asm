; 16-bit addition example in 8085 assembly language

LHLD 2050H        ; Load first 16-bit number into HL
XCHG              ; DE ← first number

LHLD 2052H        ; Load second 16-bit number into HL
DAD D             ; HL = HL + DE

MVI A, 00H        ; Clear A
JNC NO_CARRY      ; Jump if no carry
INR A             ; A = 01H if carry occurred

NO_CARRY:
SHLD 3050H        ; Store result (LSB→3050H, MSB→3051H)
STA 3052H         ; Store carry (00H or 01H)
HLT
; This program adds two 16-bit numbers stored at memory locations 2050H-2051H and 2052H-2053H
; The result is stored at memory locations 3050H-3051H and the carry (if any) is stored at 3052H