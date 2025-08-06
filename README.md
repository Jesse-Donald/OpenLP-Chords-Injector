# OpenLP-Chords-Injector
A script to inject chords into any song in the OpenLP database without altering any custom song structures. Requires a CCLI SongSelect account

![logo](https://github.com/user-attachments/assets/3169b8a6-1655-46dd-8be3-c7cc7204eafb)

Required Configuration:
- Replace database path to your OpenLP songs.sqlite database file
- Add your CCLI Cookies to the relevant section

USEAGE:
python ./inject_chords.py

Arguments:
-  --file (Path to ChordPro file for single song)
-  --batch (Process all songs in OpenLP database)
- --dry-run (Preview changes without saving to DB)

Script will open a browser and authenticate with SongSelect using the provided cookies, then search and download the related chords file before parsing and injecting the chords into the OpenLP songs database while preserving the verse structure. Several browser windows may appear when running this script.

**Note at this stage it is advised not to provide an author as this is not yet fully implemented**
