"""CPU functionality."""

import sys


class CPU:
    """Main CPU class."""

    __STACK_BASE__ = 0xf4
    __IM__ = 5
    __IS__ = 6
    __SP__ = 7

    def __init__(self):
        """Construct a new CPU."""
        self.ram = [0] * 256
        # IM = interrupt mask = registers[5]
        # IS = interrupt status = registers[6]
        # SP = stack pointer = registers[7]
        self.reg = [0] * 8
        # program counter, instruction register,
        self.pc = self.ir = 0
        # flags 00000LGE
        # less than, greater than, equal
        self.fl = 0

        # initialze memory read/write registers
        self.__memory_address_register__ = 0
        self.__memory_data_register__ = 0

        # initialize stack pointer
        self.reg[7] = CPU.__STACK_BASE__

    def load(self):
        """Load a program into memory."""

        address = 0

        # For now, we've just hardcoded a program:

        program = [
            # From print8.ls8
            0b10000010,  # LDI R0,8
            0b00000000,
            0b00001000,
            0b01000111,  # PRN R0
            0b00000000,
            0b00000001,  # HLT
        ]

        for instruction in program:
            self.ram[address] = instruction
            address += 1

    def alu(self, op, reg_a, reg_b):
        """ALU operations."""

        if op == "ADD":
            self.reg[reg_a] += self.reg[reg_b]
        # elif op == "SUB": etc
        else:
            raise Exception("Unsupported ALU operation")

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
        pass

    # memory address register, points to address in ram
    # for target of read / write operations
    @property
    def mar(self):
        return self.__memory_address_register__

    @mar.setter
    def mar(self, address):
        assert address >=0 and address < len(self.ram), \
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

    def ram_read(self, mar):
        """Returns a byte from ram."""
        self.mar = mar
        self.mad = self.ram[self.mar]
        return self.mad
    
    def ram_write(self, mar, mad):
        """Writes a byte to ram."""
        self.mar = mar
        self.mad = mad
        self.ram[self.mar] = self.mad
