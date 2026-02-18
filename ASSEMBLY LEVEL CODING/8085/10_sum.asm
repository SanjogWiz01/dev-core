Add two numbers located at 3030H and 4040H. Display sum on Port 1. If carry is generated, 
display it on Port 2. Store sum on 5050H.

lda 3030h; load to the accumlaotor 
mov a,b; move to b
lda 4040h; load to the accumulator 
add b; adding the given data
sta 5050h; store the data
out 01h; give output at the port 1
JNC LOOP;
MVI A,01H
OUT 02H
loop:
hlt;end of code
