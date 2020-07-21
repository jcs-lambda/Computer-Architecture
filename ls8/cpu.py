"""CPU functionality."""

import re
import sys


class CPU:
    """Main CPU class."""

    __STACK_BASE__ = 0xf4
    __IM__ = 5  # register for interrupt mask
    __IS__ = 6  # register for interrupt status
    __SP__ = 7  # register for stack pointer

    __ALU__ = {  # ALU opcode to command map
        0b10100000: 'ADD',
        0b10101000: 'AND',
        0b10100111: 'CMP',
        0b01100110: 'DEC',
        0b10100011: 'DIV',
        0b01100101: 'INC',
        0b10100100: 'MOD',
        0b10100010: 'MUL',
        0b01101001: 'NOT',
        0b10101010: 'OR',
        0b10101100: 'SHL',
        0b10101101: 'SHR',
        0b10100001: 'SUB',
        0b10101011: 'XOR',
    }

    __ALU_OP__ = {  # ALU command to operation map
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

    def __init_opcodes__(self):
        self.__OPCODES__ = {
            0b01010000: self.CALL,
            0b00000001: self.HLT,
            0b01010010: self.INT,
            0b00010011: self.IRET,
            0b01010101: self.JEQ,
            0b01011010: self.JGE,
            0b01010111: self.JGT,
            0b01011001: self.JLE,
            0b01011000: self.JLT,
            0b01010100: self.JMP,
            0b01010110: self.JNE,
            0b10000011: self.LD,
            0b10000010: self.LDI,
            0b00000000: self.NOP,
            0b01000110: self.POP,
            0b01001000: self.PRA,
            0b01000111: self.PRN,
            0b01000101: self.PUSH,
            0b00010001: self.RET,
            0b10000100: self.ST,
        }

    def __init__(self):
        """Construct a new CPU."""
        self.ram = [0] * 256  # total memory
        self.reg = [0] * 8  # general purpose registers
        self.fl = 0  # flags 00000LGE (less than, greater than, equal)

        # initialze program counter / instruction register
        self.__program_counter__ = 0
        self.__instruction_register__ = 0

        # initialze memory read/write registers
        self.__memory_address_register__ = 0
        self.__memory_data_register__ = 0

        # initialize stack pointer
        self.reg[self.__SP__] = self.__STACK_BASE__

        self.__init_opcodes__()

    def load(self, filename):
        """Load a program into memory."""
        with open(filename, 'r') as f:
            program = f.read()

        for address, match in enumerate(
            re.finditer(r'^[01]{8}', program, re.MULTILINE)
        ):
            assert address < self.__STACK_BASE__, \
                'program too large to fit in memory'
            instruction = match.group()
            self.ram_write(address, int(instruction, 2))

        # set default empty interrupt handlers
        self.ram_write(0xF7, 0b00010011)  # IRET opcode into reserved memory
        for address in range(0xF8, 0x100):  # for each interrupt vector
            self.ram_write(address, 0xF7)  # point to IRET in reserved memory

    def alu(self, op, reg_a, reg_b):
        """ALU operations."""
        assert reg_a >= 0 and reg_a < len(self.reg), \
            f'invalid register: {reg_a}'
        assert reg_b is None or (reg_b >= 0 and reg_b < len(self.reg)), \
            f'invalid register: {reg_b}'

        try:
            x = self.reg[reg_a]
            y = self.reg[reg_b] if reg_b is not None else None
            result = self.__ALU_OP__[op](x, y)
            if op == 'CMP':
                self.fl = result
            else:
                self.reg[reg_a] = result
                self.reg[reg_a] &= 0xFF
        except ZeroDivisionError:
            print(f'ERROR: {op} by 0 near {self.pc}')
            self.__running__ = False
        except Exception:
            raise SystemError('Unsupported ALU operation')

    def trace(self):
        """
        Handy function to print out the CPU state. You might want to call this
        from run() if you need help debugging.
        """

        print(f"TRACE: %02X | %02X %02X %02X |" % (
            self.pc,
            # self.fl,
            # self.ie,
            self.ram_read(self.pc),
            self.ram_read(self.pc + 1),
            self.ram_read(self.pc + 2)
        ), end='')

        for i in range(8):
            print(" %02X" % self.reg[i], end='')

        print()

    def run(self):
        """Run the CPU."""
        self.__running__ = True
        while self.__running__:
            self.check_interrupts()

            # initialize intruction register and any operands
            self.ir = self.ram_read(self.pc)
            if self.ir & 0b100000 > 0:
                # ALU operation
                self.alu(self.__ALU__[self.ir], self.operand_a, self.operand_b)
            else:
                # non-ALU opcode
                self.__OPCODES__[self.ir]()

            # if instruction does not modify program counter
            if self.ir & 0b10000 == 0:
                # move to next instruction
                self.pc += 1

    def check_interrupts(self):
        """Checks and handles pending interupts."""
        maskedInterrupts = self.reg[self.__IM__] & self.reg[self.__IS__]
        for interrupt in range(8):
            bit = 1 << interrupt
            if maskedInterrupts & bit:  # if interrupt is triggered
                self.__OLD_IM__ = self.reg[self.__IM__]  # save interrupt state
                self.reg[self.__IM__] = 0  # disable interrupts
                self.reg[self.__IS__] &= (255 ^ bit)  # clear interrupt
                self.reg[self.__SP__] -= 1  # push program counter
                self.ram_write(self.reg[self.__SP__], self.pc + 1)
                self.reg[self.__SP__] -= 1  # push flags
                self.ram_write(self.reg[self.__SP__], self.fl)
                for i in range(7):  # push R0-R6
                    self.reg[self.__SP__] -= 1
                    self.ram_write(self.reg[self.__SP__], self.reg[i])
                self.pc = self.ram[0xF8 + interrupt]  # pc <- handler
                break  # stop checking interrupts

    # OPCODES ############################################################
    def CALL(self):
        """Calls a subroutine at the address stored in the register.

        Opcode: 01010000

        `CALL register`
        """
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        self.reg[self.__SP__] -= 1
        self.ram_write(self.reg[self.__SP__], self.pc + 1)
        self.pc = self.reg[self.operand_a]

    def HLT(self):
        """Halt the CPU (and exit the emulator).
        
        Opcode: 00000001
        
        `HLT`
        """
        self.__running__ = False

    def INT(self):
        """Issue the interrupt number stored in the given register.

        Opcode: 01010010

        `INT register`
        """
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        assert self.reg[self.operand_a] <= 7, \
            f'invalid interrupt: {self.reg[self.operand_a]}'
        self.reg[self.__IS__] |= (1 << self.reg[self.operand_a])

    def IRET(self):
        """Return from an interrupt handler.

        Opcode: 00010011

        `IRET`
        """
        for i in range(6, -1, -1):  # pop R6-R0
            self.reg[i] = self.ram_read(self.reg[self.__SP__])
            self.reg[self.__SP__] += 1
        self.fl = self.ram_read(self.reg[self.__SP__])  # pop flags
        self.reg[self.__SP__] += 1
        self.pc = self.ram_read(self.reg[self.__SP__])  # pop program counter
        self.reg[self.__SP__] += 1
        self.reg[self.__IM__] = self.__OLD_IM__  # enable interrupts

    def JEQ(self):
        """If equal flag is set (true),
        jump to the address stored in the given register.

        Opcode: 01010101

        `JEQ register`
        """
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        if self.fl & 0b1:
            self.pc = self.reg[self.operand_a]
        else:
            self.pc += 1

    def JGE(self):
        """If greater-than flag or equal flag is set (true),
        jump to the address stored in the given register.

        Opcode: 01011010

        `JGE register`
        """
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        if self.fl & 0b11:
            self.pc = self.reg[self.operand_a]
        else:
            self.pc += 1

    def JGT(self):
        """If greater-than flag is set (true),
        jump to the address stored in the given register.

        Opcode: 01010111

        `JGT register`
        """
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        if self.fl & 0b10:
            self.pc = self.reg[self.operand_a]
        else:
            self.pc += 1

    def JLE(self):
        """If less-than flag or equal flag is set (true),
        jump to the address stored in the given register.

        Opcode: 01011001

        `JLE register`
        """
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        if self.fl & 0b101:
            self.pc = self.reg[self.operand_a]
        else:
            self.pc += 1

    def JLT(self):
        """If less-than flag is set (true),
        jump to the address stored in the given register.

        Opcode: 01011000

        `JLT register`
        """
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        if self.fl & 0b100:
            self.pc = self.reg[self.operand_a]
        else:
            self.pc += 1

    def JMP(self):
        """Jump to the address stored in the given register.

        Opcode: 01010100

        `JMP register`
        """
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        self.pc = self.reg[self.operand_a]

    def JNE(self):
        """If E flag is clear (false, 0),
        jump to the address stored in the given register.

        Opcode: 01010110

        `JNE register`
        """
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        if not self.fl & 0b1:
            self.pc = self.reg[self.operand_a]
        else:
            self.pc += 1
        pass

    def LD(self):
        """Loads registerA with the value at the memory address
        stored in registerB.

        Opcode: 10000011

        `LD registerA registerB`
        """
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        assert self.operand_b >= 0 and self.operand_b < len(self.reg), \
            f'invalid register: {self.operand_b}'
        self.reg[self.operand_a] = self.ram_read(self.reg[self.operand_b])

    def LDI(self):
        """Set the value of a register to an integer.

        Opcode: 10000010

        `LDI registerA registerB`
        """
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        self.reg[self.operand_a] = self.operand_b

    def NOP(self):
        """No operation.

        Opcode: 00000000

        `NOP`
        """
        pass

    def POP(self):
        """Pop the value at the top of the stack into the given register.

        Opcode: 01000110

        `POP register`
        """
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        assert self.reg[self.__SP__] < self.__STACK_BASE__, \
            'empty stack - cannot POP'
        self.reg[self.operand_a] = self.ram_read(self.reg[self.__SP__])
        self.reg[self.__SP__] += 1

    def PRA(self):
        """Print alpha character value stored in the given register.

        Opcode: 01001000

        `PRA register`
        """
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        print(chr(self.reg[self.operand_a]), end='')

    def PRN(self):
        """Print numeric value stored in the given register.

        Opcode: 01000111

        `PRN register`
        """
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        print(self.reg[self.operand_a])

    def PUSH(self):
        """Push the value in the given register on the stack.

        Opcode: 01000101

        `PUSH register`
        """
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        self.reg[self.__SP__] -= 1
        self.ram_write(self.reg[self.__SP__], self.reg[self.operand_a])

    def RET(self):
        """Return from subroutine.

        Opcode: 00010001

        `RET`
        """
        assert self.reg[self.__SP__] < self.__STACK_BASE__, \
            'empty stack - cannot POP'
        self.pc = self.ram_read(self.reg[self.__SP__])
        self.reg[self.__SP__] += 1

    def ST(self):
        """Store value in registerB in the address stored in registerA.

        Opcode: 10000100

        `ST registerA registerB`
        """
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        assert self.operand_b >= 0 and self.operand_b < len(self.reg), \
            f'invalid register: {self.operand_b}'
        self.ram_write(self.reg[self.operand_a], self.reg[self.operand_b])
    
    # END OPCODES ########################################################

    # memory address register, points to address in ram
    # for target of read / write operations
    @property
    def mar(self):
        return self.__memory_address_register__

    @mar.setter
    def mar(self, address):
        assert address >= 0 and address < len(self.ram), \
            '__memory_address_register__ out of range'
        self.__memory_address_register__ = address & 0xFF

    @mar.deleter
    def mar(self):
        self.__memory_address_register__ = 0

    # memory data register, hold value read from or to write to
    # ram[memory address register] in read/write operations
    @property
    def mdr(self):
        return self.__memory_data_register__

    @mdr.setter
    def mdr(self, value):
        self.__memory_data_register__ = value & 0xFF

    @mdr.deleter
    def mdr(self):
        self.__memory_data_register__ = 0

    # program counter, points to next instruction to be executed
    @property
    def pc(self):
        return self.__program_counter__

    @pc.setter
    def pc(self, value):
        assert value < self.reg[self.__SP__] or value == 0xF7, \
            'program counter cannot point into stack'
        self.__program_counter__ = value & 0xFF

    @pc.deleter
    def pc(self):
        self.__program_counter__ = 0

    # instruction register, holds the currently executing opcode
    @property
    def ir(self):
        return self.__instruction_register__

    @ir.setter
    def ir(self, opcode):
        assert opcode in self.__OPCODES__ or opcode in self.__ALU__, \
            f'unknown opcode: {opcode:08b} at {self.pc}'
        self.__instruction_register__ = opcode
        # load potential operands
        self.operand_a = self.ram_read(self.pc + 1) \
            if opcode >> 6 > 0 else None
        self.operand_b = self.ram_read(self.pc + 2) \
            if opcode >> 6 > 1 else None
        # move program counter past any operands
        self.pc += (opcode >> 6)

    @ir.deleter
    def ir(self):
        self.__instruction_register__ = 0

    def ram_read(self, mar):
        """Returns a byte from ram."""
        self.mar = mar
        self.mdr = self.ram[self.mar]
        return self.mdr

    def ram_write(self, mar, mdr):
        """Writes a byte to ram."""
        self.mar = mar
        self.mdr = mdr
        self.ram[self.mar] = self.mdr
