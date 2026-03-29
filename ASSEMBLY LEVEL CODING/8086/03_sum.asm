# WAP to declare 3 variables A1, B1 and C1. Store 05H in A1, 06H in B1. Compute the sum 
of A1 and B1 and store the result in C1.
.model small
.data
A1 DW 00H
B1 DW 00H
C1  DW 00H
.code
MOV A1, 05H
MOV B1, 06 H
MOV AX, A1
ADD AX, B1
MOV C1, AX ; store the result 


MOV AH, 4CH
INT 21H
END