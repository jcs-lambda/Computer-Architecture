"""LS-8 Opcode implementation"""

# constants needed by CPU
BITS = 8
REGISTERS = 8
IRET_OPCODE = 0b00010011
ALU_MASK = 0b00100000

ALU = {  # ALU opcode to command map
    0b10100000: 'ADD', 0b10101000: 'AND', 0b10100111: 'CMP',
    0b01100110: 'DEC', 0b10100011: 'DIV', 0b01100101: 'INC',
    0b10100100: 'MOD', 0b10100010: 'MUL', 0b01101001: 'NOT',
    0b10101010: 'OR', 0b10101100: 'SHL', 0b10101101: 'SHR',
    0b10100001: 'SUB', 0b10101011: 'XOR',
}

ALU_OP = {  # ALU command to operation map
    'ADD': lambda x, y: x + y,
    'AND': lambda x, y: x & y,
    'CMP': lambda x, y: 1 if x == y else 2 if x > y else 4,
    'DEC': lambda x, y: x - 1,
    'DIV': lambda x, y: x // y,
    'INC': lambda x, y: x + 1,
    'MOD': lambda x, y: x % y,
    'MUL': lambda x, y: x * y,
    'NOT': lambda x, y: ~x,
    'OR': lambda x, y: x | y,
    'SHL': lambda x, y: x << y,
    'SHR': lambda x, y: x >> y,
    'SUB': lambda x, y: x - y,
    'XOR': lambda x, y: x ^ y,
}

# opcode to implementation map
# filled with `@opcode(0b123123)` decorator
OPCODES = {}

# https://stackoverflow.com/questions/38679349/python-decorator-to-create-dictionary
# opcode = lambda code: lambda func: OPCODES.setdefault(code, function)


def opcode(code):
    """Decorator to build OPCODES table."""
    def _(func):
        return OPCODES.setdefault(code, func)
    return _


@opcode(0b01010000)
def CALL(cpu):
    """Calls a subroutine at the address stored in the register."""
    cpu.SP -= 1
    cpu.ram_write(cpu.SP, cpu.PC + 2)
    cpu.PC = cpu.reg[cpu.OP_A]


@opcode(0b00000001)
def HLT(cpu):
    """Halt the CPU (and exit the emulator)."""
    cpu._running = False


@opcode(0b01010010)
def INT(cpu):
    """Issue the interrupt number stored in the given register."""
    assert cpu.reg[cpu.OP_A] < BITS, \
        f'invalid interrupt: {cpu.reg[cpu.OP_A]}'
    cpu.IS |= (1 << cpu.reg[cpu.OP_A])
    cpu.PC += 2


@opcode(0b00010011)
def IRET(cpu):
    """Return from an interrupt handler."""
    for i in range(6, -1, -1):  # pop R6-R0
        cpu.reg[i] = cpu.ram_read(cpu.SP)
        cpu.SP += 1
    cpu.FL = cpu.ram_read(cpu.SP)  # pop flags
    cpu.SP += 1
    cpu.PC = cpu.ram_read(cpu.SP)  # pop program counter
    cpu.SP += 1
    cpu.IM = cpu._old_IM  # restore interrupt mask


@opcode(0b01010101)
def JEQ(cpu):
    """If equal flag is set (true),
    jump to the address stored in the given register.
    """
    if cpu.FL & 0b1:  # check E flag
        cpu.PC = cpu.reg[cpu.OP_A]
    else:
        cpu.PC += 2


@opcode(0b01011010)
def JGE(cpu):
    """If greater-than flag or equal flag is set (true),
    jump to the address stored in the given register.
    """
    if cpu.FL & 0b11:  # chek G and E flags
        cpu.PC = cpu.reg[cpu.OP_A]
    else:
        cpu.PC += 2


@opcode(0b01010111)
def JGT(cpu):
    """If greater-than flag is set (true),
    jump to the address stored in the given register.
    """
    if cpu.FL & 0b10:  # check G flag
        cpu.PC = cpu.reg[cpu.OP_A]
    else:
        cpu.PC += 2


@opcode(0b01011001)
def JLE(cpu):
    """If less-than flag or equal flag is set (true),
    jump to the address stored in the given register.
    """
    if cpu.FL & 0b101:  # check L and E flags
        cpu.PC = cpu.reg[cpu.OP_A]
    else:
        cpu.PC += 2


@opcode(0b01011000)
def JLT(cpu):
    """If less-than flag is set (true),
    jump to the address stored in the given register.
    """
    if cpu.FL & 0b100:  # check L flag
        cpu.PC = cpu.reg[cpu.OP_A]
    else:
        cpu.PC += 2


@opcode(0b01010100)
def JMP(cpu):
    """Jump to the address stored in the given register."""
    cpu.PC = cpu.reg[cpu.OP_A]


@opcode(0b01010110)
def JNE(cpu):
    """If E flag is clear (false, 0),
    jump to the address stored in the given register.
    """
    if not cpu.FL & 0b1:  # check E flag
        cpu.PC = cpu.reg[cpu.OP_A]
    else:
        cpu.PC += 2


@opcode(0b10000011)
def LD(cpu):
    """Loads registerA with the value at the memory address
    stored in registerB.
    """
    assert cpu.OP_B >= 0 and cpu.OP_B < len(cpu.reg), \
        f'invalid register: {cpu.OP_B}'
    cpu.reg[cpu.OP_A] = cpu.ram_read(cpu.reg[cpu.OP_B])


@opcode(0b10000010)
def LDI(cpu):
    """Set the value of a register to an integer."""
    cpu.reg[cpu.OP_A] = cpu.OP_B


@opcode(0b00000000)
def NOP(cpu):
    """No operation."""
    pass


@opcode(0b01000110)
def POP(cpu):
    """Pop the value at the top of the stack into the given register."""
    cpu.reg[cpu.OP_A] = cpu.ram_read(cpu.SP)
    cpu.SP += 1


@opcode(0b01001000)
def PRA(cpu):
    """Print alpha character value stored in the given register."""
    print(chr(cpu.reg[cpu.OP_A]), end='', flush=True)


@opcode(0b01000111)
def PRN(cpu):
    """Print numeric value stored in the given register."""
    print(cpu.reg[cpu.OP_A])


@opcode(0b01000101)
def PUSH(cpu):
    """Push the value in the given register on the stack."""
    cpu.SP -= 1
    cpu.ram_write(cpu.SP, cpu.reg[cpu.OP_A])


@opcode(0b00010001)
def RET(cpu):
    """Return from subroutine."""
    cpu.PC = cpu.ram_read(cpu.SP)
    cpu.SP += 1


@opcode(0b10000100)
def ST(cpu):
    """Store value in registerB in the address stored in registerA."""
    assert cpu.OP_B >= 0 and cpu.OP_B < len(cpu.reg), \
        f'invalid register: {cpu.OP_B}'
    cpu.ram_write(cpu.reg[cpu.OP_A], cpu.reg[cpu.OP_B])

@opcode(0b10000000)
def ADDI(cpu):
    """Add an immediate value to a register."""
    cpu.reg[cpu.OP_A] += cpu.OP_B
    cpu.reg[cpu.OP_A] &= ((1 << BITS) - 1)


if __name__ == '__main__':
    print(f'{len(ALU)} ALU opcodes:')
    for opcode, cmd in ALU.items():
        print(f'{opcode:08b}\t{cmd}\t{ALU_OP[cmd]}')
    print()
    print(f'{len(OPCODES)} non-ALU opcodes')
    for opcode, cmd in OPCODES.items():
        print(f'{opcode:08b}\t{cmd}')
