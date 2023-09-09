# ED8/ED9 Model Injection Tools
A set of scripts that allow replacing one model with another in the Trails of Cold Steel games (including Hajimari CLE) and in Tokyo Xanadu eX+.

## Credits:
The pka and pkg libraries are forked from Julian Uy (github.com/uyjulian), all credit to them.  These scripts were developed with a fellow modder at LL who wishes to not be credited, but I am grateful for his research and contribution.

## Requirements:
1. Python 3.9 and newer is required for use of these scripts.  It is free from the Microsoft Store, for Windows users.  For Linux users, please consult your distro.

2. The zstandard for python is needed.  Install by typing "python3 -m pip install zstandard" in the command line / shell.  (The sys, os, shutil, struct, io, glob, and zlib modules are also required, but these are all already included in most basic python installations.)

3. My forks of uyjulian's unpackpka and upackpkg, available respectively at https://github.com/eArmada8/unpackpkg and at https://github.com/eArmada8/unpackpka.  Releases come with the necessary files.

## CS1 / CS2 / CS3 / CS4 / Hajimari
### Usage:
1. *Model Names:*

You need to know what models you want to mess with.  Grab [my python script](https://github.com/eArmada8/misc_kiseki/blob/main/name_table_decode.py) that decodes the names table from my misc_kiseki repo, and put it in *{CS3 / CS4 / Hajimari folder}*/data/text/dat_en (or /data/text/dat if using fan translation), and execute it.  It will spit out table.csv, which can be opened in excel or openoffice, etc.  Sorry, I do not have a CS1/CS2 compatible script for this step.

2. *Obtaining source and target models*

For CS3/CS4 models: Put extract_pka.py into *{CS3 / CS4 / Hajimari folder}*/data/asset/D3D11.  For CS3/CS4, run extract_pkg.py, press enter (first question asks for pka and defaults to assets.pka), then second question asks which files you need.  If you put in a search term, it will match and grab multiple files (typing in CHR087 is like \*CHR087\*).  For CS3, move the .pkg files you extracted to *{CS3 folder}*/data/asset/D3D11_us.

For Hajimari models: You don't need extract_pka for CLE Hajimari since it's not archived in the first place.

3. *Decompressing source models (Only for using CLE Hajimari assets in NISA CS3/CS4)*

To use Hajimari assets in CS3 / CS4, the zstandard compression must be removed first.  Use aa - decompresspkg.py:
`python3 "aa - decompresspkg.py" <PKG_NAME.pkg>`

4. *Replacing shaders in the source models (Only for moving an asset from one game to another)*

Put aa_replace_shaders.py, aa_inject_model.py and unpackpkg.py in *{CS3 / CS4 folder}*/data/asset/D3D11 (where you find the PKA for game you are intending to use the model in, *not* the one you obtained the model from).  Put the PKG file from another game into the same folder.  Run aa_replace_shaders.py, press enter (first question asks for pka and defaults to assets.pka), then second question asks which file want to patch.  Enter the name of the pkg file.  It will replace all the shaders for which there is a replacement shader, and it will leave behind a backup file.

If you are moving a model to Hajimari, type None when it asks for assets.pka, and it will search all the pkg files in the current directory instead.  It will skip over the file you are trying to fix, of course.  *It is not smart enough to exclude other files, so please replace shaders one file at a time!*

5. *Replacing a model with another model (injection)*

Put aa_inject_model.py and unpackpkg.py in *{CS3 folder}*/data/asset/D3D11_us or *{CS4 / Hajimari folder}*/data/asset/D3D11. Execute aa_inject_model.py.  It asks for the source .pkg, then it asks for the target .pkg.  It will make a backup of the target, and then push the source into the target.  If there is a backup of the source, it will always use the backup to inject.  This means: 1. As long as you only use my tool instead of editing your own files, your original files are safe, 2. You can do easy swaps (inject A->B and then B->A will result in a swap, because it will always use the backup original of B to inject), and 3. You can restore the original model by injecting into itself (inject A->B and then B->B will restore B to original, because again it will always use the backup original of B to inject).  It will never overwrite the first backup, so you can literally do A->B, C->B, D->B, and then B->B and you will still end up with B.

### Notes:
1. CS3 / CS4 / Hajimari assets can be used in each other's games, although shaders should be replaced for reliable loading.  Not all shaders are available in every game.  CS1 and CS2 assets can only be used within their own games.

2. The injector expects the target to already exist and will refuse to inject into a new file.  This is for two reasons: 1. so that it can make a backup, and you won't be confused on re-injections, and 2. to prevent confusing you if you make a spelling mistake (since it wouldn't otherwise cause an error).  So in CS3/CS4, extract BOTH source and target, not just source.

3. CS4 will read .pkg files preferentially over the .pka file without further fuss.  CS3 will do so as well, BUT you need to move the files to *{CS3 folder}*/data/asset/D3D11_us (or at least I did with mine - NIS America Steam release).  My suggestion for CS3 is to move everything over except the .pka file and extract_pka.py.  Keep your backups in D3D11_us as well, and you can inject back and forth.

4. To do whole model swaps, you will need to replace at a minimum columns B,D,E in the excel sheet from step 1.  Maybe other parts too, I haven't fully figured this out.  Be careful, the model parts in column E are often shared.  You may also want to swap the .inf files.

5. Any time you are porting a model into game that does not have that model (for example using a CS4 exclusive costume in CS3), you will want to copy the .inf file from the source game to the target game.  They are in *{CS3 / CS4 / Hajimari folder}*/data/chr/chr/*{character folder}*.  These should **not** be renamed, but copied as is.

## Nintendo Switch games

Run asset_xml_to_nx.py in the same folder with the Windows D3D11 .pkg file, and it will replace asset_D3D11.xml with asset_NX.xml (with all the internal structures changed to match NX entries).  Then run aa_replace_shaders.py as above step 4.  asset_xml_to_nx.py is dependent on aa_inject_model.py and unpackpkg.py being in the same folder to run.

## Tokyo Xanadu eX+
Use aa - txe inject model.py instead.  Automatically pulls the required files from the .bra archives for injection.  Requires txe_file_extract.py and my fork of unpackpkg.py (eArmada/unpackpkg).
