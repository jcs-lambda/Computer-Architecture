    LDI R1, 1   ; number of times to print char
    LDI R2, 64  ; max number of times to print char
    LDI R3, 1   ; steps to shift left
    LDI R4, 42  ; '*' char to print
LineLoop:
    PUSH R1     ; save current char count
    LDI R0, PrinterLoop
    CALL R0     ; print char in R4, R1 number of times
    POP R1      ; restore current char count
    SHL R1, R3  ; double current char count
    CMP R1, R2
    LDI R0, LineLoop
    JLE R0      ; if current char count <= max, goto LineLoop
    HLT
PrinterLoop:
;   R1 holds count remaining on enter
;   R4 holds char to print
    PRA R4      ; print char in R4
    DEC R1      ; decrement char count
    LDI R0, 0
    CMP R1, R0
    LDI R0, PrinterLoop
    JGT R0      ; if char count in R1 is > 0, goto PrinterLoop
    LDI R0, 10  ; '\n' char
    PRA R0      ; print newline char from R0
    RET
