"""CPU functionality."""

from os import name
from re import finditer, MULTILINE
from time import time

from kbhit import KBHit
from opcodes import ALU, ALU_MASK, ALU_OP, BITS
from opcodes import IRET_OPCODE, OPCODES, REGISTERS

MAX_MEM = 1 << BITS

IM_REG = REGISTERS - 3
IS_REG = REGISTERS - 2
SP_REG = REGISTERS - 1

INTERRUPTS = BITS
RESERVED = 3
STACK_BASE = KEY_BUFFER = MAX_MEM - INTERRUPTS - RESERVED - 1
NULL_INTERRUPT = MAX_MEM - INTERRUPTS - 1

TIMER_INTERRUPT = 0
KEYBOARD_INTERRUPT = 1


def nested_property(func):
    """ Nest getter, setter and deleter

    https://pythonguide.readthedocs.io/en/latest/python/decorator.html
    """
    names = func()
    names['doc'] = func.__doc__
    return property(**names)


class CPU:
    """Main CPU class."""

    def __init__(self):
        """Construct a new CPU."""
        self._running = False

        del self.reg  # Set registers to 0
        del self.SP  # Set stack pointer to STACK_BASE
        del self.PC  # Set program counter to 0
        del self.FL  # Set flags to 0
        del self.ram  # Set RAM to 0

        del self.IM, self.IS  # Set interrupt mask, state to 0

        # initialize NULL_INTERUPT to IRET_OPCODE
        self.ram_write(NULL_INTERRUPT, IRET_OPCODE)
        # initialize interrupt vectors to NULL_INTERRUPT
        for i in range(INTERRUPTS):
            self.ram_write(MAX_MEM-INTERRUPTS+i, NULL_INTERRUPT)

    ###  GENERAL PURPOSE RGISTERS  #######################################
    @nested_property
    def reg():
        """General Purpose Registers"""

        def fget(self):
            try:
                return self._reg
            except:
                self._reg = [0] * REGISTERS
                return self._reg

        def fset(self, value):
            assert isinstance(value, int), \
                'reg.fset: value must be int'
            self._reg = [value & (MAX_MEM - 1)] * REGISTERS

        def fdel(self):
            self._reg = [0] * REGISTERS
        return locals()

    @nested_property
    def IM():
        """Interrupt Mask"""

        def fget(self):
            return self.reg[IM_REG]

        def fset(self, value):
            self.reg[IM_REG] = value & (MAX_MEM - 1)

        def fdel(self):
            self.reg[IM_REG] = 0
        return locals()

    @nested_property
    def IS():
        """Interrupt State"""

        def fget(self):
            return self.reg[IS_REG]

        def fset(self, value):
            self.reg[IS_REG] = value & (MAX_MEM - 1)

        def fdel(self):
            self.reg[IS_REG] = 0
        return locals()

    @nested_property
    def SP():
        """Stack Pointer"""

        def fget(self):
            return self.reg[SP_REG]

        def fset(self, value):
            value = value & (MAX_MEM - 1)
            assert 0 <= value <= STACK_BASE, \
                f'stack pointer out of range'
            pc = self.PC + (self.IR >> 6)
            assert pc < value or pc == NULL_INTERRUPT, \
                f'stack cannot overlap executing code'
            self.reg[SP_REG] = value

        def fdel(self):
            self.reg[SP_REG] = STACK_BASE
        return locals()

    ###  INTERNAL REGISTERS  #############################################
    @nested_property
    def PC():
        """Program Counter"""

        def fget(self):
            try:
                return self._program_counter
            except:
                self._program_counter = 0
                return self._program_counter

        def fset(self, value):
            value = value & (MAX_MEM - 1)
            assert (0 <= value < self.SP) or value == NULL_INTERRUPT, \
                f'invalid program counter: {value}, stack: {self.SP}'
            self._program_counter = value

        def fdel(self):
            self._program_counter = 0
        return locals()

    @nested_property
    def IR():
        """Instruction Register"""

        def fget(self):
            try:
                return self._instruction_register
            except:
                self._instruction_register = 0
                return self._instruction_register

        def fset(self, value):
            value = value & (MAX_MEM - 1)
            assert value in OPCODES or value in ALU, \
                f'CPU.IR: invalid opcode: {value:08b} at: {self.PC}'
            self._instruction_register = value
            if value & (1 << BITS - 2):  # one operand
                assert self.PC + 1 < self.SP, \
                    f'CPU.IR: instruction operands in stack at: {self.PC}'
                self.OP_A = self.ram_read(self.PC + 1)
                self.OP_B = None
            elif value & (1 << BITS - 1):  # two operands
                assert self.PC + 2 < self.SP, \
                    f'CPU.IR: instruction operands in stack at: {self.PC}'
                self.OP_A = self.ram_read(self.PC + 1)
                self.OP_B = self.ram_read(self.PC + 2)
            else:  # zero operands
                self.OP_A = None
                self.OP_B = None

        def fdel(self):
            self._instruction_register = 0
        return locals()

    @nested_property
    def MAR():
        """Memory Address Register"""

        def fget(self):
            try:
                return self._memory_address_register
            except:
                self._memory_address_register = 0
                return self._memory_address_register

        def fset(self, value):
            value = value & (MAX_MEM - 1)
            # assert (0 <= value < MAX_MEM), \
            #     f'address out of range: {value} at: {self.PC}'
            self._memory_address_register = value

        def fdel(self):
            self._memory_address_register = 0
        return locals()

    @nested_property
    def MDR():
        """Memory Data Register"""

        def fget(self):
            try:
                return self._memory_data_register
            except:
                self._memory_data_register = 0
                return self._memory_data_register

        def fset(self, value):
            value = value & (MAX_MEM - 1)
            self._memory_data_register = value

        def fdel(self):
            self._memory_data_register = 0
        return locals()

    @nested_property
    def FL():
        """Flags: `00000LGE`"""

        def fget(self):
            try:
                return self._flags
            except:
                self._flags = 0
                return self._flags

        def fset(self, value):
            value = value & (MAX_MEM - 1)
            self._flags = value

        def fdel(self):
            self._flags = 0
        return locals()

    @nested_property
    def OP_A():
        """Operand A, can only be a register number"""

        def fget(self):
            try:
                return self._operand_a
            except:
                self._operand_a = 0
                return self._operand_a

        def fset(self, value):
            if value is not None:
                value = value & (MAX_MEM - 1)
            assert value is None or 0 <= value < REGISTERS, \
                f'operand_a out of range: {value}'
            self._operand_a = value

        def fdel(self):
            self._operand_a = 0
        return locals()

    @nested_property
    def OP_B():
        """Operand B, can be a register number or immediate value"""

        def fget(self):
            try:
                return self._operand_b
            except:
                self._operand_b = 0
                return self._operand_b

        def fset(self, value):
            if value is not None:
                value = value & (MAX_MEM - 1)
            assert value is None or (
                value < (REGISTERS if self.IR & ALU_MASK else MAX_MEM)
            ), f'operand_b out of range for ALU operation: {value}'
            self._operand_b = value

        def fdel(self):
            self._operand_b = 0
        return locals()

    ###  MEMORY  #########################################################
    @nested_property
    def ram():
        """Memory"""

        def fget(self):
            try:
                return self._ram
            except:
                self._ram = [0] * MAX_MEM
                return self._ram

        def fset(self, value):
            assert isinstance(value, int), \
                f'ram.fset: value must be int'
            self._ram = [value & (MAX_MEM - 1)] * MAX_MEM

        def fdel(self):
            self._ram = [0] * MAX_MEM
        return locals()

    def ram_read(self, address):
        self.MAR = address
        self.MDR = self.ram[self.MAR]
        return self.MDR

    def ram_write(self, address, value):
        self.MAR, self.MDR = address, value
        self.ram[self.MAR] = self.MDR

    ###  CPU OPERATIONS  #################################################
    def load(self, filename):
        """Load a program into memory."""
        # reset state
        self.__init__()

        """Load a program into memory."""
        with open(filename, 'r') as f:
            program = f.read()

        for address, match in enumerate(
            finditer(r'^[01]{8}', program, MULTILINE)
        ):
            assert address < STACK_BASE, \
                'program too large to fit in memory'
            instruction = match.group()
            self.ram_write(address, int(instruction, 2))

    def alu(self, op, reg_a, reg_b):
        """ALU operations."""

        try:
            x = self.reg[reg_a]
            y = self.reg[reg_b] if reg_b is not None else None
            result = ALU_OP[op](x, y)
            if op == 'CMP':
                self.FL = result
            else:
                self.reg[reg_a] = result
                self.reg[reg_a] &= (MAX_MEM - 1)
        except ZeroDivisionError:
            print(f'ALU ERROR: {op} by 0 at {self.PC}')
            self.__running__ = False
        except Exception:
            raise SystemError(f'Unsupported ALU operation: {op} at {self.PC}')

    def trace(self):
        """
        Handy function to print out the CPU state. You might want to call this
        from run() if you need help debugging.
        """

        print(f"TRACE: %02X | %02X %02X %02X |" % (
            self.PC,
            # self.FL,
            # self.ie,
            self.ram_read(self.PC),
            self.ram_read(self.PC + 1),
            self.ram_read(self.PC + 2)
        ), end='')

        for i in range(REGISTERS):
            print(" %02X" % self.reg[i], end='')

        print()

    def interrupt(self, interrupt):
        """Sets N bit in IS register."""
        assert interrupt < INTERRUPTS, \
            f'invalid interrupt: {interrupt}'
        self.IS |= (1 << interrupt)

    def run(self):
        """Run the CPU."""
        self._running = True
        old_time = time()
        kb = KBHit()
        while self._running:
            # trigger timer interrupt every second (approx)
            new_time = time()
            if new_time - old_time > 1:
                self.interrupt(TIMER_INTERRUPT)
                old_time = new_time

            # trigger keyboard interrupt on keypress
            if kb.kbhit():
                c = kb.getch()
                if ord(c[0]) == 27:  # ESC
                    self._running = False
                    break
                self.ram_write(KEY_BUFFER, ord(c[0]))
                self.interrupt(KEYBOARD_INTERRUPT)

            self.check_interrupts()

            # process instruction at program counter
            self.IR = self.ram_read(self.PC)
            if self.IR & ALU_MASK:
                self.alu(ALU[self.IR], self.OP_A, self.OP_B)
            else:
                OPCODES[self.IR](self)

            # adjust program counter if necessary
            if not self.IR & 0b10000:
                self.PC += (1 + (self.IR >> 6))

        kb.set_normal_term()

    def check_interrupts(self):
        """Checks and handles pending interupts."""
        maskedInterrupts = self.IM & self.IS
        for interrupt in range(8):
            bit = 1 << interrupt
            if maskedInterrupts & bit:  # if interrupt is triggered
                self._old_IM = self.IM  # save interrupt state
                self.IM = 0  # disable interrupts
                self.IS &= (255 ^ bit)  # clear interrupt
                self.SP -= 1  # push program counter
                self.ram_write(self.SP, self.PC)
                self.SP -= 1  # push flags
                self.ram_write(self.SP, self.FL)
                for i in range(REGISTERS-1):  # push R0-R6
                    self.SP -= 1
                    self.ram_write(self.SP, self.reg[i])
                self.PC = self.ram[MAX_MEM - INTERRUPTS +
                                   interrupt]  # PC <- handler
                break  # stop checking interrupts


if __name__ == '__main__':
    from os.path import dirname, join, realpath
    cur_dir = dirname(realpath(__file__))
    files = [
        join(cur_dir, 'examples/stackoverflow.ls8'),
        join(cur_dir, 'examples/addi.ls8'),
        join(cur_dir, 'examples/print8.ls8'),
        join(cur_dir, 'examples/mult.ls8'),
        join(cur_dir, 'examples/stack.ls8'),
        join(cur_dir, 'examples/call.ls8'),
        join(cur_dir, 'examples/printstr.ls8'),
        join(cur_dir, 'examples/sctest.ls8'),
        join(cur_dir, 'examples/histogram.ls8'),
        join(cur_dir, 'examples/keyboard.ls8'),
        join(cur_dir, 'examples/interrupts.ls8'),
    ]
    c = CPU()
    for f in files:
        name = f.split('/')[-1].split('.')[0]
        print(f'{"-"*8}  {name}  {"-"*8}')
        c.load(f)
        try:
            c.run()
        except Exception as ex:
            print(f'EXCEPTION: {ex}')
