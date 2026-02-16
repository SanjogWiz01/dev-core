;Load 10H into A, load 20H into B, then add B to A.

;Expected: A = 30H
MVI A, 10H
MVI B, 20H
ADD B
HLT
;Load 10H into A, load 20H into B, then add B to A. --- IGNORE ---