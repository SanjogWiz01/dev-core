 Write an Assembly Language Program that retrieves a data located at 2050H and it displays, 
if it is even and stores FFH on that location if it is odd.

LDA 2050H      ; A ← data from memory

ANI 01H        ; check LSB (odd/even) this is pre define that chech odd or even
JZ EVEN        ; if zero → EVEN

; -------- ODD --------
MVI A,FFH
STA 2050H      ; replace number with FFH
HLT

; -------- EVEN --------
EVEN:
LDA 2050H      ; reload original number
OUT 01H        ; display on port
HLT
