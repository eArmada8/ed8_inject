# Short script to patch a model with asset_nx.xml Falcom ED8 games.  It will create a backup,
# and then it will attempt to replace asset_D3D11.xml with asset_NX.xml.
#
# Requires aa_inject_model.py and unpackpkg.py, put in the same directory
#
# GitHub eArmada8/ed8_inject

import sys, os, shutil, struct, io, glob
import xml.etree.ElementTree as ET
from aa_inject_model import *

def convert_asset_xml (xml_binary):
    with io.BytesIO(xml_binary) as f:
        asset_xml = ET.parse(f)
        root = asset_xml.getroot()
        for asset in root:
            for cluster in asset:
                if 'path' in cluster.attrib:
                    cluster.attrib['path'] = cluster.attrib['path'].replace('data/D3D11', 'data/NX')
                if 'type' in cluster.attrib:
                    cluster.attrib['type'] = cluster.attrib['type'].replace('p_fx', 'binary')
        with io.BytesIO() as f2:
            asset_xml.write(f2, encoding='utf-8', xml_declaration=True)
            f2.seek(0)
            xml_data = f2.read()
            return (xml_data)

def replace_xml_in_pkg(pkg_filename, new_pkg_filename):
    with open(pkg_filename, 'rb') as f:
        file_contents = get_pkg_contents(f)
        new_file_contents = []
        new_file_stream = io.BytesIO()
        for i in range(len(file_contents)):
            if 'asset_D3D11' in file_contents[i]["file_entry_name"]:
                    file = retrieve_file (f, file_contents[i]["file_entry_name"], file_contents, decompress = True)
                    file = convert_asset_xml(file)
                    file_contents[i]["file_entry_name"] = file_contents[i]["file_entry_name"].replace('D3D11','NX')
                    file_contents[i]["file_entry_uncompressed_size"] = len(file)
                    file_contents[i]["file_entry_compressed_size"] = len(file)
                    file_contents[i]["file_entry_flags"] = 0
                    new_file_contents = insert_file_into_stream (new_file_stream, new_file_contents, file, file_contents[i])
            else:
                file = retrieve_file (f, file_contents[i]["file_entry_name"], file_contents, decompress = False)
                new_file_contents = insert_file_into_stream (new_file_stream, new_file_contents, file, file_contents[i])
        write_pkg_file (new_pkg_filename, new_file_stream, new_file_contents, magic = b'\x00\x00\x00\x00')
    return

def process_pkg (pkg_name):
    # Make a backup (prior backups will be overwritten)
    shutil.copy2(pkg_name + '.pkg', pkg_name + '.pkg.bak')
    # Patch xml into target
    replace_xml_in_pkg(pkg_name + '.pkg.bak', pkg_name + '.pkg')

if __name__ == '__main__':
    # Set current directory
    if getattr(sys, 'frozen', False):
        os.chdir(os.path.dirname(sys.executable))
    else:
        os.chdir(os.path.abspath(os.path.dirname(__file__)))

    # If argument given, attempt to export from file in argument
    if len(sys.argv) > 1:
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('pkg_filename', help="Name of pkg file to export from (required).")
        args = parser.parse_args()
        if os.path.exists(args.pkg_filename) and args.pkg_filename[-4:].lower() == '.pkg':
            process_pkg(args.pkg_filename[:-4])
    else:
        pkg_files = glob.glob('*.pkg')
        for i in range(len(pkg_files)):
            process_pkg(os.path.basename(pkg_files[i])[:-4])
