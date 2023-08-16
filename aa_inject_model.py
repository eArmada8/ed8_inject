# Short script to inject one model into another in Falcom games.  If a source backup exists, it will use the backup
# instead of the existing file.  If no target backup exists, it will create one before erasing the target.
#
# Requires my fork of unpackpkg.py, put in the same directory
#
# GitHub eArmada8/misc_kiseki

import sys, os, shutil, struct, io
from unpackpkg import * # Needed for games that compress the XML file

def get_pkg_contents (f, package_name = ''):
    f.seek(0,0)
    file_contents = []
    magic = f.read(4)
    total_files, = struct.unpack("<I", f.read(4))
    for i in range(total_files):
        file = {}
        file["file_entry_name"], file["file_entry_uncompressed_size"],\
            file["file_entry_compressed_size"], file["file_entry_offset"],\
            file["file_entry_flags"] = struct.unpack("<64s4I", f.read(80))
        file["file_entry_name"] = file["file_entry_name"].rstrip(b"\x00").decode('utf-8')
        file["package_name"] = package_name
        file_contents.append(file)
    return(file_contents)

def retrieve_file (f, file_entry_name, file_contents, decompress = True):
    file_entry = [x for x in file_contents if file_entry_name in x["file_entry_name"]]
    if len(file_entry) > 0:
        f.seek(file_entry[0]["file_entry_offset"],0)
        if file_entry[0]["file_entry_flags"] & 0x1 and decompress:
            return(uncompress_nislzss(f, file_entry[0]["file_entry_uncompressed_size"], file_entry[0]["file_entry_compressed_size"]))
        elif file_entry[0]["file_entry_flags"] & 0x4 and decompress:
            return(uncompress_lz4(f, file_entry[0]["file_entry_uncompressed_size"], file_entry[0]["file_entry_compressed_size"]))
        elif file_entry[0]["file_entry_flags"] & 0x8 and decompress:
            return(uncompress_zstd(f, file_entry[0]["file_entry_uncompressed_size"], file_entry[0]["file_entry_compressed_size"]))
        else:
            return(f.read(file_entry[0]["file_entry_compressed_size"]))
    else:
        return False

def retrieve_xml_file (f, file_contents):
    xml_entry = [x for x in file_contents if 'xml' in x["file_entry_name"]]
    if len(xml_entry) > 0:
        return retrieve_file(f, xml_entry[0]["file_entry_name"], file_contents, decompress = True)
    else:
        return False

# Input is a file stream of a pkg file
def retrieve_asset_symbol (f):
    file_contents = get_pkg_contents(f)
    xml_file_data = retrieve_xml_file (f, file_contents)
    asset_symbol_offset = xml_file_data.find(b'asset symbol') + 14
    rest_of_file_offset = xml_file_data.find(b'"', asset_symbol_offset+1)
    return(xml_file_data[asset_symbol_offset:rest_of_file_offset].decode('utf-8'))

# Takes binary file data, new symbol as string.  Uses binary search, as parsing XML is overkill.
def change_xml_asset_symbol (xml_file_data, new_asset_symbol):
    asset_symbol_offset = xml_file_data.find(b'asset symbol') + 14
    rest_of_file_offset = xml_file_data.find(b'"', asset_symbol_offset+1)
    return(xml_file_data[0:asset_symbol_offset] + new_asset_symbol.encode('utf-8') + xml_file_data[rest_of_file_offset:])

# Adds file onto the end of the stream, and appends name/size to contents.  Offsets are not calculated.
def insert_file_into_stream (f, content_struct, binary_file_data, file_details):
    f.write(binary_file_data)
    content_struct.append(file_details)
    return(content_struct)

# Updates all file offsets in the TOC based on current file size
def update_file_offsets (content_struct):
    current_file_offset = len(content_struct) * 80 + 8 # First file offset is always here
    for i in range(len(content_struct)):
        content_struct[i]["file_entry_offset"] = current_file_offset
        current_file_offset += content_struct[i]["file_entry_compressed_size"]
    return(content_struct)

def write_pkg_file (newfilename, file_stream, content_struct, magic = b'\x00\x00\x00\x00'):
    # Assume all the file offsets are wrong, and fix them
    content_struct = update_file_offsets(content_struct)
    with open(newfilename, 'wb') as f:
        f.write(magic)
        f.write(struct.pack("<I", len(content_struct)))
        for i in range(len(content_struct)):
            f.write(struct.pack("<64s4I", content_struct[i]["file_entry_name"].encode("utf-8").ljust(64,b'\x00'),\
                content_struct[i]["file_entry_uncompressed_size"],\
                content_struct[i]["file_entry_compressed_size"],\
                content_struct[i]["file_entry_offset"],\
                content_struct[i]["file_entry_flags"]))
        file_stream.seek(0)
        f.write(file_stream.read())
    return

def inject_asset_symbol_into_pkg(pkg_filename, new_pkg_filename, asset_symbol):
    with open(pkg_filename, 'rb') as f:
        file_contents = get_pkg_contents(f)
        new_file_contents = []
        new_file_stream = io.BytesIO()
        for i in range(len(file_contents)):
            if 'xml' in file_contents[i]["file_entry_name"]:
                file = retrieve_file (f, file_contents[i]["file_entry_name"], file_contents, decompress = True)
                file = change_xml_asset_symbol(file, asset_symbol)
                new_file_contents = insert_file_into_stream (new_file_stream, new_file_contents, file,\
                    {"file_entry_name": file_contents[i]["file_entry_name"],\
                    "file_entry_uncompressed_size": len(file),\
                    "file_entry_compressed_size": len(file),\
                    "file_entry_offset": 0, "file_entry_flags": 0}) # Offset will be fixed at time of packing
            else:
                file = retrieve_file (f, file_contents[i]["file_entry_name"], file_contents, decompress = False)
                new_file_contents = insert_file_into_stream (new_file_stream, new_file_contents, file, file_contents[i])
    write_pkg_file (new_pkg_filename, new_file_stream, new_file_contents, magic = b'\x00\x00\x00\x00')

if __name__ == "__main__":
    # Set current directory
    os.chdir(os.path.abspath(os.path.dirname(__file__)))

    # Grab the name of the source model (model to inject)
    try:
        sourcefile = sys.argv[1].lower()
        if sourcefile[-4:] == '.pkg':
            sourcefile = sourcefile[:-4] # Strip off the '.pkg' if present
        if not os.path.exists(sourcefile + '.pkg'):
            raise Exception('Error: Package "' + sourcefile + '" does not exist!')
    except IndexError:
        sourcefile = str(input("Please enter the name (e.g. C_CHR000_C02) of model to inject: "))
        if sourcefile[-4:] == '.pkg':
            sourcefile = sourcefile[:-4] # Strip off the '.pkg' if present
        while not os.path.exists(sourcefile + '.pkg'):
            sourcefile = str(input("File does not exist.  Please enter the name (e.g. C_CHR000_C02) of model to inject: "))
            if sourcefile[-4:] == '.pkg':
                sourcefile = sourcefile[:-4] # Strip off the '.pkg' if present
    sourcefile = sourcefile.upper()

    # Figure out which file to inject.  If an original file exists, use that file, otherwise use the current file.
    if os.path.exists(sourcefile + '.pkg.original'):
        file_to_inject = sourcefile + '.pkg.original'
    else:
        file_to_inject = sourcefile + '.pkg'

    # Grab the name of the target model (model to be replaced)
    try:
        targetfile = sys.argv[2].lower()
        if targetfile[-4:] == '.pkg':
            targetfile = targetfile[:-4] # Strip off the '.pkg' if present
        if not os.path.exists(targetfile + '.pkg'):
            raise Exception('Error: Package "' + targetfile + '" does not exist!')
    except IndexError:
        targetfile = str(input("Please enter the name (e.g. C_CHR000_C02) of model to replace: "))
        if targetfile[-4:] == '.pkg':
            targetfile = targetfile[:-4] # Strip off the '.pkg' if present
        while not os.path.exists(targetfile + '.pkg'):
            targetfile = str(input("File does not exist.  Please enter the name (e.g. C_CHR000_C02) of model to replace: "))
            if targetfile[-4:] == '.pkg':
                targetfile = targetfile[:-4] # Strip off the '.pkg' if present
    targetfile = targetfile.upper()

    # Make a target backup, only if no backup exists.
    if not os.path.exists(targetfile + '.pkg.original'):
        shutil.copy2(targetfile + '.pkg', targetfile + '.pkg.original')

    # Grab original asset symbol
    with open(targetfile + '.pkg.original', 'rb') as f:
        new_asset_symbol = retrieve_asset_symbol(f)

    # Write patched model into target
    inject_asset_symbol_into_pkg(sourcefile + '.pkg', targetfile + '.pkg', new_asset_symbol)
