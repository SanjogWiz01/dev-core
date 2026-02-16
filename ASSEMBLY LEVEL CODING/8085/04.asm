Add two numbers stored in memory

Location 2050H = 15H
Location 2051H = 25H

Add them and store the result in 2052H.

LXI H, 2050H  ; Load HL pair with address 2050H
MOV A, M      ; Move the value at address 2050H to accumulator
INX H         ; Increment HL to point to 2051H