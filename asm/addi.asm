; Demonstrate ADDI opcode
;
; Expected output:
; 15
; 255

    LDI R0, 0x0F  ; value to print: 15
    PRN R0        ; print
    ADDI R0, 0xF0 ; add 240 to value in R0
    PRN R0        ; print
    HLT
