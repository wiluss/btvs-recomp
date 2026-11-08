"""Reviewed 535-arm factory switch in the hash-checked Buffy XBE.

The pin's two table readers default to 256 entries. The guest bounds index
to 0..534 in sub_0027C200; all 535 pointers at TABLE are local to that function.
Keep those arms local: making them callable entries changes the guest stack.
"""
TABLE = 0x00283100
ENTRIES = 535


def install():
    from tools.recomp.lifter import Lifter
    from tools.recomp.translator import FunctionTranslator
    original_read = Lifter._read_jump_table
    original_local = FunctionTranslator._read_local_jump_table

    def read(self, table_va, max_entries=256):
        return original_read(self, table_va,
                             ENTRIES if table_va == TABLE else max_entries)

    def local(self, table_va, lower, upper, max_entries=256, min_entry_va=None):
        return original_local(self, table_va, lower, upper,
                              ENTRIES if table_va == TABLE else max_entries,
                              min_entry_va)

    Lifter._read_jump_table = read
    FunctionTranslator._read_local_jump_table = local
