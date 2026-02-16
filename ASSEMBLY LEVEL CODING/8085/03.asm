;problem

Load 09H into register C
Load 05H into register D
Subtract D from C
Final result should be: C = 04H

MVI C,O9H
MVI D,05H
MOV A,C ; SUBTRACT instruction works with Accumulator
SUB 
MOV C,A
HLT