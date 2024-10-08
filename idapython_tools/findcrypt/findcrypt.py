import struct, copy
import idc, idautils, ida_name, ida_bytes, ida_ua, ida_search
from consts import non_sparse_consts, sparse_consts, operand_consts

if 'g_fc_prefix_cmt' not in globals():
    g_fc_prefix_cmt = "FC: "
if 'g_fc_prefix_var' not in globals():
    g_fc_prefix_var = "FC_"

if idc.BADADDR == 0xFFFFFFFF:
    digits = 8
else:
    digits = 16

def convert_to_byte_array(const, big_endian=False):
    byte_array = []
    if const["size"] == "B":
        byte_array = const["array"]
    elif const["size"] == "L":
        for val in const["array"]:
            if big_endian:
                byte_array += list(map(lambda x:x if type(x) == int else ord(x), struct.pack(">L", val)))
            else:
                byte_array += list(map(lambda x:x if type(x) == int else ord(x), struct.pack("<L", val)))
    elif const["size"] == "Q":
        for val in const["array"]:
            if big_endian:
                byte_array += list(map(lambda x:x if type(x) == int else ord(x), struct.pack(">Q", val)))
            else:
                byte_array += list(map(lambda x:x if type(x) == int else ord(x), struct.pack("<Q", val)))
    return byte_array

def main():
    print("[*] loading crypto constants")
    non_sparse_consts2 = []
    for const in non_sparse_consts:
        const["byte_array"] = convert_to_byte_array(const)
        non_sparse_consts2.append(const)
        if const["size"] != "B":
            const = copy.copy(const)
            const["byte_array"] = convert_to_byte_array(const, big_endian=True)
            non_sparse_consts2.append(const)

    for start in idautils.Segments():
        print("[*] searching for crypto constants in %s" % idc.get_segm_name(start))
        ea = start
        while ea < idc.get_segm_end(start):
            bbbb = list(struct.unpack("BBBB", idc.get_bytes(ea, 4)))
            for const in non_sparse_consts2:
                if bbbb != const["byte_array"][:4]:
                    continue
                if list(map(lambda x:x if type(x) == int else ord(x), idc.get_bytes(ea, len(const["byte_array"])))) == const["byte_array"]:
                    print(("0x%0" + str(digits) + "X: found const array %s (used in %s)") % (ea, const["name"], const["algorithm"]))
                    idc.set_name(ea, g_fc_prefix_var + const["name"], ida_name.SN_FORCE)
                    if const["size"] == "B":
                        ida_bytes.del_items(ea, 0, len(const["array"]))
                        idc.create_byte(ea)
                    elif const["size"] == "L":
                        ida_bytes.del_items(ea, 0, len(const["array"])*4)
                        idc.create_dword(ea)
                    elif const["size"] == "Q":
                        ida_bytes.del_items(ea, 0, len(const["array"])*8)
                        idc.create_qword(ea)
                    idc.make_array(ea, len(const["array"]))
                    ea += len(const["byte_array"]) - 4
                    break
            ea += 4

        ea = start
        if idc.get_segm_attr(ea, idc.SEGATTR_TYPE) == idc.SEG_CODE:
            while ea < idc.get_segm_end(start):
                d = ida_bytes.get_dword(ea)
                for const in sparse_consts:
                    if d != const["array"][0]:
                        continue
                    tmp = ea + 4
                    for val in const["array"][1:]:
                        for i in range(8):
                            if ida_bytes.get_dword(tmp + i) == val:
                                tmp = tmp + i + 4
                                break
                        else:
                            break
                    else:
                        print(("0x%0" + str(digits) + "X: found sparse constants for %s") % (ea, const["algorithm"]))
                        cmt = idc.get_cmt(idc.prev_head(ea), 0)
                        if cmt:
                            idc.set_cmt(idc.prev_head(ea), cmt + ' ' + g_fc_prefix_cmt + const["name"], 0)
                        else:
                            idc.set_cmt(idc.prev_head(ea), g_fc_prefix_cmt + const["name"], 0)
                        ea = tmp
                        break
                ea += 1

    print("[*] searching for crypto constants in immediate operand")
    funcs = idautils.Functions()
    for f in funcs:
        flags = idc.get_func_flags(f)
        if (not flags & (idc.FUNC_LIB | idc.FUNC_THUNK)):
            ea = f
            f_end = idc.get_func_attr(f, idc.FUNCATTR_END)
            while (ea < f_end):
                imm_operands = []
                insn = ida_ua.insn_t()
                ida_ua.decode_insn(insn, ea)
                for i in range(len(insn.ops)):
                    if insn.ops[i].type == ida_ua.o_void:
                        break
                    if insn.ops[i].type == ida_ua.o_imm:
                        imm_operands.append(insn.ops[i].value)
                if len(imm_operands) == 0:
                    ea = idc.find_code(ea, ida_search.SEARCH_DOWN)
                    continue
                for const in operand_consts:
                    if const["value"] in imm_operands:
                        print(("0x%0" + str(digits) + "X: found immediate operand constants for %s") % (ea, const["algorithm"]))
                        cmt = idc.get_cmt(ea, 0)
                        if cmt:
                            idc.set_cmt(ea, cmt + ' ' + g_fc_prefix_cmt + const["name"], 0)
                        else:
                            idc.set_cmt(ea, g_fc_prefix_cmt + const["name"], 0)
                        break
                ea = idc.find_code(ea, ida_search.SEARCH_DOWN)
    print("[*] finished")

if __name__ == '__main__':
    main()
