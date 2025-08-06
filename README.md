# OpenLP-Chords-Injector
A script to inject chords into any song in the OpenLP database without altering any custom song structures. Requires a CCLI SongSelect account

Required Configuration:
- Replace database path to your OpenLP songs.sqlite database file
- Add your CCLI Cookies to the relevant section

  USEAGE:
  python ./inject_chords.py

  Arguments:
  -  --file (Path to ChordPro file for single song)
  -  --batch (Process all songs in OpenLP database)
  - --dry-run (Preview changes without saving to DB)
