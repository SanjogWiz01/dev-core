;# Program to add two 16-bit numbers
'ASSUME CS: Code, DS: Data
Data Segment
N1 DW 1234H
N2 DW 5678H
R DW ?
Data ENDS
Code Segment{
 MOV AX, @Data     ; Load the address of DATA segment into AX
 MOV DS, AX 
}         
; Initialize DS with DATA segment address
MOV AX, N1 ; n1 values goes to ax
ADD AX, N2; n2 value added to ax to n1
MOV R, AX ; moxw the sum to r
; RESULT IS STOED IN R
MOV AH, 4CH
INT 21H
Code ENDS
END