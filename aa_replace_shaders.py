# Short script to patch a model with new shaders in Falcom ED8 games.  It will create a backup,
# and then it will attempt to insert all new shaders.  Thank you to My Name for pointing out
# the method and the necessity.
#
# Requires aa_inject_model.py and unpackpkg.py, put in the same directory
#
# GitHub eArmada8/misc_kiseki

import sys, os, shutil, struct, io, glob
from aa_inject_model import *

#Much of this code is taken from uyjulian/unpackpka, thank you to uyjulian
#Note there WILL be duplicate entries - e.g. asset_D3D11.xml
def get_pka_individual_file_contents (f):
    f.seek(0,0)
    # Check for proper file format
    pka_header, = struct.unpack("<I", f.read(4))
    if pka_header != 0x7FF7CF0D:
        raise Exception("This isn't a pka file")
    # Grab the total number of .pkg files in the .pka file
    total_package_entries, = struct.unpack("<I", f.read(4))
    # Grab the names of all .pkg files in the .pka file as well how many files in each package
    package_entries = {}
    for _ in range(total_package_entries):
        package_name, number_files = struct.unpack("<32sI", f.read(32+4))
        # Grab the names of all files in each individual .pkg archive as well as their hashes
        file_entries = []
        for _ in range(number_files):
            file_entry_name, file_entry_hash = struct.unpack("<64s32s", f.read(64+32))
            file_entries.append([file_entry_name.rstrip(b"\x00"), file_entry_hash])
        package_entries[package_name.rstrip(b"\x00").decode("ASCII")] = file_entries
    total_file_entries, = struct.unpack("<I", f.read(4))
    # Grab the metadata of all files in the .pka file, indexed by file hashes
    file_entries = {}
    for _ in range(total_file_entries):
        file_entry_hash, file_entry_offset, file_entry_compressed_size, file_entry_uncompressed_size,\
            file_entry_flags = struct.unpack("<32sQIII", f.read(32+8+4+4+4))
        file_entries[file_entry_hash] = [file_entry_offset, file_entry_compressed_size, file_entry_uncompressed_size, file_entry_flags]
    all_files = [x+[y] for y in package_entries.keys() for x in package_entries[y]]
    file_contents = []
    for i in range(len(all_files)):
        file_contents.append({"file_entry_name": all_files[i][0].decode('utf-8'),\
            "file_entry_uncompressed_size": file_entries[all_files[i][1]][2],\
            "file_entry_compressed_size": file_entries[all_files[i][1]][1],\
            "file_entry_offset": file_entries[all_files[i][1]][0],\
            "file_entry_flags": file_entries[all_files[i][1]][3],
            "package_name": all_files[i][2]})
    return(file_contents)

def find_file_in_pkg(file_to_find, list_of_pkgs_to_avoid = []):
    pkgs = [x for x in glob.glob('*.pkg') if x not in list_of_pkgs_to_avoid]
    match = False
    for i in range(len(pkgs)):
        with open(pkgs[i],'rb') as f:
            file_contents = [x["file_entry_name"] for x in get_pkg_contents(f)]
            if file_to_find in file_contents:
                match = pkgs[i]
                break
    return(match)

# Shaders can be pulled from either a PKA or the current folder can be searched
def replace_shaders_in_pkg(pkg_filename, new_pkg_filename, pka_filename = False):
    missing_shaders = False
    using_pka = False
    if pka_filename != False:
        asset_f = open(pka_filename, 'rb')
        using_pka = True
        archive_files = get_pka_individual_file_contents(asset_f)
    else:
        archive_files = []
    with open(pkg_filename, 'rb') as f:
        file_contents = get_pkg_contents(f)
        new_file_contents = []
        new_file_stream = io.BytesIO()
        for i in range(len(file_contents)):
            if 'fx#' in file_contents[i]["file_entry_name"]:
                if not using_pka:
                    file_match = find_file_in_pkg(file_contents[i]["file_entry_name"],\
                        list_of_pkgs_to_avoid = [pkg_filename, new_pkg_filename]) # We don't want the old shader!
                    if file_match != False:
                        asset_f = open(file_match, 'rb')
                        archive_files = get_pkg_contents(asset_f, file_match)
                shader_entries = [x for x in archive_files if file_contents[i]["file_entry_name"] == x["file_entry_name"]]
                if len(shader_entries) > 0:
                    print("Shader {0} found, replacing from {1}...".format(file_contents[i]["file_entry_name"],\
                        shader_entries[0]["package_name"]))
                    file = retrieve_file (asset_f, shader_entries[0]["file_entry_name"], archive_files, decompress = False)
                    new_file_contents = insert_file_into_stream (new_file_stream, new_file_contents, file,\
                        shader_entries[0]) # Offset will be fixed at time of packing
                    if not using_pka:
                        asset_f.close()
                else:
                    print("Shader {0} not found, including original...".format(file_contents[i]["file_entry_name"]))
                    file = retrieve_file (f, file_contents[i]["file_entry_name"], file_contents, decompress = False)
                    new_file_contents = insert_file_into_stream (new_file_stream, new_file_contents, file, file_contents[i])
                    missing_shaders = True
            else:
                file = retrieve_file (f, file_contents[i]["file_entry_name"], file_contents, decompress = False)
                new_file_contents = insert_file_into_stream (new_file_stream, new_file_contents, file, file_contents[i])
        write_pkg_file (new_pkg_filename, new_file_stream, new_file_contents, magic = b'\x00\x00\x00\x00')
    if using_pka == True:
        asset_f.close()
    return(missing_shaders)

if __name__ == "__main__":
    # Set current directory
    os.chdir(os.path.abspath(os.path.dirname(__file__)))

    # Determine the assets.pka filename, use the first argument as default
    try:
        asset_file = sys.argv[1].lower()
        if asset_file == "none":
            pass
        elif not os.path.exists(asset_file):
            raise Exception('Error: Asset archive "' + asset_file + '" does not exist!')
    except IndexError:
        input_string = "Please enter the name of assets archive.\n[default: assets.pka, can also be the name of a folder (of .pkg files) in the current folder, type \"None\" for Hajimari]  "
        asset_file = str(input(input_string) or "assets.pka").lower()
        while not (os.path.exists(asset_file) or asset_file == "none"):
            asset_file = str(input("File does not exist.  " + input_string) or "assets.pka").lower()
    if asset_file == "none":
        asset_file = False

    # Grab the name of the target model (model to be have all shaders replaced)
    try:
        targetfile = sys.argv[2].lower()
        if targetfile[-4:] == '.pkg':
            targetfile = targetfile[:-4] # Strip off the '.pkg' if present
        if not os.path.exists(targetfile + '.pkg'):
            raise Exception('Error: Package "' + targetfile + '" does not exist!')
    except IndexError:
        if not asset_file == False:
            targetfile = str(input("Please enter the name (e.g. C_CHR000_C02) of model to patch with new shaders: [default: All PKG files] "))
        else:
            targetfile = str(input("Please enter the name (e.g. C_CHR000_C02) of model to patch with new shaders: "))
        if targetfile[-4:] == '.pkg':
            targetfile = targetfile[:-4] # Strip off the '.pkg' if present
        while not (os.path.exists(targetfile + '.pkg') or ((not asset_file == False) and targetfile == '')):
            targetfile = str(input("File does not exist.  Please enter the name (e.g. C_CHR000_C02) of model to patch with new shaders: "))
            if targetfile[-4:] == '.pkg':
                targetfile = targetfile[:-4] # Strip off the '.pkg' if present
    targetfile = targetfile.upper()

    # Patch model into target
    pkgs_with_missing_shaders = []
    if (not asset_file == False) and targetfile == '':
        pkg_files = [os.path.basename(x).lower().split('.pkg')[0] for x in glob.glob('*.pkg')]
        if asset_file.lower()[-4:] == '.pka': # Mass replace with .pka mode
            for i in range(len(pkg_files)):
                print("\r\nProcessing {}.pkg...".format(pkg_files[i]))
                shutil.copy2(pkg_files[i] + '.pkg', pkg_files[i] + '.pkg.bak')
                result = replace_shaders_in_pkg(pkg_files[i] + '.pkg.bak', pkg_files[i] + '.pkg', asset_file)
                if result == True:
                    pkgs_with_missing_shaders.append(pkg_files[i])
        elif os.path.exists(asset_file) and os.path.isdir(asset_file) and len(glob.glob(asset_file+'/*.pkg')) > 0: # Folder with .pkg files mode
            base_dir = os.getcwd()
            os.chdir(base_dir+'/'+asset_file)
            for i in range(len(pkg_files)):
                print("\r\nProcessing {}.pkg...".format(pkg_files[i]))
                shutil.copy2('../'+pkg_files[i] + '.pkg', '../'+pkg_files[i] + '.pkg.bak')
                result = replace_shaders_in_pkg('../'+pkg_files[i] + '.pkg.bak', '../'+pkg_files[i] + '.pkg', False)
                if result == True:
                    pkgs_with_missing_shaders.append(pkg_files[i])
            os.chdir(base_dir)
    else:
        # Make a target backup (prior backups will be overwritten)
        shutil.copy2(targetfile + '.pkg', targetfile + '.pkg.bak')
        if asset_file == False or asset_file.lower()[-4:] == '.pka':
            result = replace_shaders_in_pkg(targetfile + '.pkg.bak', targetfile + '.pkg', asset_file)
        elif os.path.exists(asset_file) and os.path.isdir(asset_file) and len(glob.glob(asset_file+'/*.pkg')) > 0:
            base_dir = os.getcwd()
            os.chdir(base_dir+'/'+asset_file)
            result = replace_shaders_in_pkg('../'+targetfile + '.pkg.bak', '../'+targetfile + '.pkg', False)
        if result == True:
            pkgs_with_missing_shaders.append(targetfile)
    if len(pkgs_with_missing_shaders) > 0:
        print("\r\nWarning! Shader replacement was not successful in the following .pkg files: {}.".format([x.upper()+'.pkg' for x in pkgs_with_missing_shaders]))
        input("Press Enter to continue.")
