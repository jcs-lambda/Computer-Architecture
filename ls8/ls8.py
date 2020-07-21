"""Main."""

import sys
from os.path import realpath, exists
from cpu import CPU


if len(sys.argv) == 2 and exists(realpath(sys.argv[1])):
    cpu = CPU()

    cpu.load(realpath(sys.argv[1]))
    cpu.run()
else:
    print(f'python {sys.argv[0]} file_name.ls8')
