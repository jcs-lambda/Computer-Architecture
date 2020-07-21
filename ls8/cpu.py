"""CPU functionality."""

import re
import sys


class CPU:
    """Main CPU class."""

    __STACK_BASE__ = 0xf4
    __IM__ = 5
    __IS__ = 6
    __SP__ = 7

    def __init_opcodes__(self):
        self.__OPCODES__ = {
            0b00000001: self.HLT,
            0b10000010: self.LDI,
            0b01000111: self.PRN,
            0b10100010: self.MUL,
            0b01000110: self.POP,
            0b01000101: self.PUSH,
            0b01010000: self.CALL,
            0b00010001: self.RET,
            0b10100000: self.ADD,
            0b10100111: self.CMP,
            0b01010101: self.JEQ,
            0b01011010: self.JGE,
            0b01010111: self.JGT,
            0b01011001: self.JLE,
            0b01011000: self.JLT,
            0b01010100: self.JMP,
            0b01010110: self.JNE,
            0b10101000: self.AND,
            0b01100110: self.DEC,
            0b10100011: self.DIV,
            0b01100101: self.INC,
            0b10100100: self.MOD,
            0b01101001: self.NOT,
            0b10101010: self.OR,
            0b10101100: self.SHL,
            0b10101101: self.SHR,
            0b10100001: self.SUB,
            0b10101011: self.XOR,
            0b10000011: self.LD,
            0b10000100: self.ST,
            0b00000000: self.NOP,
            0b01001000: self.PRA,
        }

    def __init__(self):
        """Construct a new CPU."""
        self.ram = [0] * 256
        # IM = interrupt mask = registers[5]
        # IS = interrupt status = registers[6]
        # SP = stack pointer = registers[7]
        self.reg = [0] * 8
        # flags 00000LGE
        # less than, greater than, equal
        self.fl = 0

        # initialze program counter / instruction register
        self.__program_counter__ = 0
        self.__instruction_register__ = 0

        # initialze memory read/write registers
        self.__memory_address_register__ = 0
        self.__memory_data_register__ = 0

        # initialize stack pointer
        self.reg[7] = self.__STACK_BASE__

        self.__init_opcodes__()

    def load(self, filename):
        """Load a program into memory."""
        with open(filename, 'r') as f:
            program = f.read()

        address = 0
        for match in re.finditer(r'^[01]{8}', program, re.MULTILINE):
            instruction = match.group()
            self.ram_write(address, int(instruction, 2))
            address += 1

    def alu(self, op, reg_a, reg_b):
        """ALU operations."""

        if op == "ADD":
            self.reg[reg_a] += self.reg[reg_b]
        elif op == "MUL":
            self.reg[reg_a] *= self.reg[reg_b]
        elif op == "CMP":
            if self.reg[reg_a] == self.reg[reg_b]:
                self.fl = 0b001
            elif self.reg[reg_a] < self.reg[reg_b]:
                self.fl = 0b010
            elif self.reg[reg_a] > self.reg[reg_b]:
                self.fl = 0b100
        elif op == "AND":
            self.reg[reg_a] &= self.reg[reg_b]
        elif op == "DEC":
            self.reg[reg_a] -= 1
        elif op == "DIV":
            self.reg[reg_a] //= self.reg[reg_b]
        elif op == "INC":
            self.reg[reg_a] += 1
        elif op == "MOD":
            self.reg[reg_a] %= self.reg[reg_b]
        elif op == "NOT":
            self.reg[reg_a] = ~self.reg[reg_a]
        elif op == "OR":
            self.reg[reg_a] |= self.reg[reg_b]
        elif op == "SHL":
            self.reg[reg_a] << self.reg[reg_b]
        elif op == "SHR":
            self.reg[reg_a] >> self.reg[reg_b]
        elif op == "SUB":
            self.reg[reg_a] -= self.reg[reg_b]
        elif op == "XOR":
            self.reg[reg_a] ^= self.reg[reg_b]
        else:
            raise Exception("Unsupported ALU operation")

        self.reg[reg_a] &= 0xFF

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
            # initialize intruction register and any operands
            self.ir = self.ram_read(self.pc)
            if self.ir & 0b100000 > 0:
                # ALU operation
                self.__OPCODES__[self.ir]()
            else:
                # execute instruction
                self.__OPCODES__[self.ir]()
            if self.ir & 0b10000 == 0:
                # move to next instruction
                self.pc += 1

    # OPCODES
    def HLT(self):
        self.__running__ = False

    def LDI(self):
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        self.reg[self.operand_a] = self.operand_b

    def PRN(self):
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        print(self.reg[self.operand_a])

    def MUL(self):
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        assert self.operand_b >= 0 and self.operand_b < len(self.reg), \
            f'invalid register: {self.operand_b}'
        self.alu('MUL', self.operand_a, self.operand_b)

    def POP(self):
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        assert self.reg[self.__SP__] < self.__STACK_BASE__, \
            'empty stack - cannot POP'
        self.reg[self.operand_a] = self.ram_read(self.reg[self.__SP__])
        self.reg[self.__SP__] += 1

    def PUSH(self):
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        self.reg[self.__SP__] -= 1
        self.ram_write(self.reg[self.__SP__], self.reg[self.operand_a])

    def CALL(self):
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        self.reg[self.__SP__] -= 1
        self.ram_write(self.reg[self.__SP__], self.pc + 1)
        self.pc = self.reg[self.operand_a]

    def RET(self):
        assert self.reg[self.__SP__] < self.__STACK_BASE__, \
            'empty stack - cannot POP'
        self.pc = self.ram_read(self.reg[self.__SP__])
        self.reg[self.__SP__] += 1

    def ADD(self):
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        assert self.operand_b >= 0 and self.operand_b < len(self.reg), \
            f'invalid register: {self.operand_b}'
        self.alu('ADD', self.operand_a, self.operand_b)

    def CMP(self):
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        assert self.operand_b >= 0 and self.operand_b < len(self.reg), \
            f'invalid register: {self.operand_b}'
        self.alu('CMP', self.operand_a, self.operand_b)

    def JEQ(self):
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        if self.fl & 0b1:
            self.pc = self.reg[self.operand_a]
        else:
            self.pc += 1

    def JGE(self):
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        if self.fl & 0b11:
            self.pc = self.reg[self.operand_a]
        else:
            self.pc += 1

    def JGT(self):
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        if self.fl & 0b10:
            self.pc = self.reg[self.operand_a]
        else:
            self.pc += 1

    def JLE(self):
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        if self.fl & 0b101:
            self.pc = self.reg[self.operand_a]
        else:
            self.pc += 1

    def JLT(self):
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        if self.fl & 0b100:
            self.pc = self.reg[self.operand_a]
        else:
            self.pc += 1

    def JMP(self):
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        self.pc = self.reg[self.operand_a]

    def JNE(self):
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        if not self.fl & 0b1:
            self.pc = self.reg[self.operand_a]
        else:
            self.pc += 1
        pass

    def AND(self):
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        assert self.operand_b >= 0 and self.operand_b < len(self.reg), \
            f'invalid register: {self.operand_b}'
        self.alu('AND', self.operand_a, self.operand_b)

    def DEC(self):
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        self.alu('DEC', self.operand_a, self.operand_b)

    def DIV(self):
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        assert self.operand_b >= 0 and self.operand_b < len(self.reg), \
            f'invalid register: {self.operand_b}'
        assert self.reg[self.operand_b] != 0, \
            'divide by zero'
        self.alu('DIV', self.operand_a, self.operand_b)

    def INC(self):
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        self.alu('INC', self.operand_a, self.operand_b)

    def MOD(self):
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        assert self.operand_b >= 0 and self.operand_b < len(self.reg), \
            f'invalid register: {self.operand_b}'
        assert self.reg[self.operand_b] != 0, \
            'divide by zero'
        self.alu('MOD', self.operand_a, self.operand_b)

    def NOT(self):
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        self.alu('NOT', self.operand_a, self.operand_b)

    def OR(self):
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        assert self.operand_b >= 0 and self.operand_b < len(self.reg), \
            f'invalid register: {self.operand_b}'
        self.alu('OR', self.operand_a, self.operand_b)

    def SHL(self):
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        assert self.operand_b >= 0 and self.operand_b < len(self.reg), \
            f'invalid register: {self.operand_b}'
        self.alu('SHL', self.operand_a, self.operand_b)

    def SHR(self):
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        assert self.operand_b >= 0 and self.operand_b < len(self.reg), \
            f'invalid register: {self.operand_b}'
        self.alu('SHR', self.operand_a, self.operand_b)

    def SUB(self):
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        assert self.operand_b >= 0 and self.operand_b < len(self.reg), \
            f'invalid register: {self.operand_b}'
        self.alu('SUB', self.operand_a, self.operand_b)

    def XOR(self):
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        assert self.operand_b >= 0 and self.operand_b < len(self.reg), \
            f'invalid register: {self.operand_b}'
        self.alu('XOR', self.operand_a, self.operand_b)

    def LD(self):
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        assert self.operand_b >= 0 and self.operand_b < len(self.reg), \
            f'invalid register: {self.operand_b}'
        self.reg[self.operand_a] = self.ram_read(self.reg[self.operand_b])

    def ST(self):
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        assert self.operand_b >= 0 and self.operand_b < len(self.reg), \
            f'invalid register: {self.operand_b}'
        self.ram_write(self.reg[self.operand_a], self.reg[self.operand_b])

    def NOP(self):
        pass

    def PRA(self):
        assert self.operand_a >= 0 and self.operand_a < len(self.reg), \
            f'invalid register: {self.operand_a}'
        print(chr(self.reg[self.operand_a]), end='')

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
        assert value < self.reg[self.__SP__], \
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
        assert opcode in self.__OPCODES__, \
            'unknown opcode'
        self.__instruction_register__ = opcode
        # load potential operands
        self.operand_a = self.ram_read(self.pc + 1)
        self.operand_b = self.ram_read(self.pc + 2)
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
