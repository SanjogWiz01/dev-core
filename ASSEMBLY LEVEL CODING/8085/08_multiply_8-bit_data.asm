; muntiply 2 8-bit numbers using repeated addition
LXI 2050H;
MOV B,A; ; move first number to B
INR H;
MOV C,M;
MVI A 00H;
MVI D 00H; ; clear D to use as counter

LOOP2:
ADD B;
JNC LOOP1;
INR C;
LOOP1;
DCR D;
JNZ LOOP2;
STA 3050H;
MOV A,C;
STA 3051H;
HLT;
