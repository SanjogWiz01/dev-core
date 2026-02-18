;positive and negative numbers in assembly language
LXI 2050H;
MOV A,M;
RAL
JC LOOP:
MVI 00H;
STA 3050H;
HLT;
LOOP:
MVI 01H;
STA 3050H;
HLT;
;This program checks if a number is positive or negative.