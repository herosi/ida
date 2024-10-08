import idc, idaapi, ida_search, ida_name, ida_bytes, ida_pro
import os, binascii, struct

try:
    import ida_struct
    add_struc = ida_struct.add_struc
    get_struc_id = ida_struct.get_struc_id
    add_struc_member = ida_struct.add_struc_member
    get_struc_size = ida_struct.get_struc_size
    get_struc = ida_struct.get_struc
    get_member_by_name = ida_struct.get_member_by_name
except ModuleNotFoundError:
    # from IDA 9.0, many of them are in idc.
    add_struc = idc.add_struc
    get_struc_id = idc.get_struc_id
    add_struc_member = idc.add_struc_member
    get_struc_size = idc.get_struc_size
    
    # for IDA 9.0
    # Some of them are needed to implement.
    def get_struc(struct_tid):
        tif = ida_typeinf.tinfo_t()
        if tif.get_type_by_tid(struct_tid):
            if tif.is_struct():
                return tif
        return ida_idapi.BADADDR
    
    def get_member_by_name(tif, name):
        if not tif.is_struct():
            return None
    
        udm = ida_typeinf.udm_t()
        udm.name = name
        idx = tif.find_udm(udm, ida_typeinf.STRMEM_NAME)
        if idx != -1:
            return udm
        return None

GUID_LIST_DIR = os.path.join(os.path.dirname(__file__), 'guid_list')
GUID_LIST= []
# [name, prefix, filepath]
GUID_LIST.append(['Class ID', 'CLSID_', os.path.join(GUID_LIST_DIR, 'class.txt')])
GUID_LIST.append(['Interface ID', 'IID_', os.path.join(GUID_LIST_DIR, 'interface.txt')])
GUID_LIST.append(['Folder ID', 'FOLDERID_', os.path.join(GUID_LIST_DIR, 'folder.txt')])
GUID_LIST.append(['Media Type', '', os.path.join(GUID_LIST_DIR, 'media.txt')])

def get_guid_tid():
    tid = get_struc_id('GUID')
    if tid == idaapi.BADADDR:
        print("[*] create GUID struct")
        tid = add_struc(0xffffffff, 'GUID', 0)
        sptr = get_struc(tid)
        add_struc_member(sptr, 'Data1', 0x0, 0x20000000, None, 4)
        add_struc_member(sptr, 'Data2', 0x4, 0x10000000, None, 2)
        add_struc_member(sptr, 'Data3', 0x6, 0x10000000, None, 2)
        add_struc_member(sptr, 'Data4', 0x8, 0x00000000, None, 8)
    return tid

def make_binary_pattern(guid):
    # sample guid: 0F87369F-A4E5-4CFC-BD3E-73E6154572DD
    tmp = guid.split('-')
    data = b''
    data += struct.pack('<L', int(tmp[0], 16))
    data += struct.pack('<H', int(tmp[1], 16))
    data += struct.pack('<H', int(tmp[2], 16))
    data += struct.pack('>H', int(tmp[3], 16))
    data += binascii.a2b_hex(tmp[4])

    binary_pattern = ' '.join(map(lambda x:format(x if type(x) == int else ord(x), '02x'), list(data)))
    return binary_pattern

def main():
    tid = get_guid_tid()
    for type_name, type_prefix, filepath in GUID_LIST:
        print('[*] scanning {}'.format(type_name))
        fp = open(filepath, 'r')
        for line in fp.readlines():
            line = line.strip()
            if line == "":
                continue
            guid, guid_name = line.split(' ')
            guid_name = type_prefix + guid_name
            binary_pattern = make_binary_pattern(guid)

            ea = 0
            while True:
                if ida_pro.IDA_SDK_VERSION >= 900:
                    ea = ida_bytes.find_bytes(binary_pattern, ea, flags=ida_bytes.BIN_SEARCH_FORWARD | ida_bytes.BIN_SEARCH_NOSHOW)
                else:
                    ea = idc.find_binary(ea, ida_search.SEARCH_DOWN | ida_search.SEARCH_NEXT | ida_search.SEARCH_NOSHOW, binary_pattern)
                if ea == idaapi.BADADDR:
                    break

                idc.del_items(ea, 16, 0)
                ida_bytes.create_struct(ea, get_struc_size(tid), tid)
                if idc.set_name(ea, guid_name, ida_name.SN_NOWARN) != 1:
                    for i in range(0, 100):
                        if idc.set_name(ea, guid_name + "_" + str(i), ida_name.SN_NOWARN) == 1:
                            break
                    else:
                        print("[!] 0x{:X}: failed to apply {}".format(ea, guid_name))
                print("[*] 0x{:X}: {}".format(ea, guid_name))
                
                # add a byte size for find_bytes because it does not have SEARCH_NEXT option like find_binary
                if ida_pro.IDA_SDK_VERSION >= 900:
                    ea += 1

    print("[*] finished")

if __name__ == "__main__":
    main()
