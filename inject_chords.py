import argparse
import os
import re
import sqlite3
import shutil
import datetime
import logging
from chordpro_parser import parse_chordpro_text, parse_chordpro_into_verses
from songselect_downloader import create_browser, search_song, download_chordpro, read_chordpro_contents, get_latest_chordpro_file
import xml.etree.ElementTree as ET

OPENLP_DB_PATH = "C:/Users/admin/AppData/Roaming/openlp/data/songs/songs.sqlite"
LOG_FILE = "inject_chords.log"

# Setup logging
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")

def log(msg):
    print(msg)
    logging.info(msg)

def extract_title_artist_from_filename(filename):
    base = os.path.basename(filename).rsplit(".", 1)[0]
    if "-" in base:
        title, artist = base.split("-chordpro-", 1)
        print(title, artist)
        return title.strip(), artist.strip()
    return base.strip(), None

def backup_database():
    timestamp = datetime.datetime.now().isoformat(timespec='seconds').replace(":", "-")
    backup_path = f"openlp_backup_{timestamp}.db"
    shutil.copyfile(OPENLP_DB_PATH, backup_path)
    log(f"🛟 Backup created at {backup_path}")
    return backup_path

def inject_chords_into_lyrics_xml(xml_text, chordpro_verses):
    ET.register_namespace('', '')
    root = ET.fromstring(xml_text)

    # Step 1: Group verses by type+label
    from collections import defaultdict
    verse_groups = defaultdict(list)
    for verse in root.findall('.//verse'):
        key = f"{verse.attrib.get('type', '').lower()}{verse.attrib.get('label', '').lower()}"
        verse_groups[key].append(verse)

    # Step 2: Replace grouped verses
    for tag, xml_verses in verse_groups.items():
        if tag in chordpro_verses:
            chord_lines = chordpro_verses[tag].splitlines()
            n = len(xml_verses)
            lines_per_verse = max(1, len(chord_lines) // n)
            print(f"🎸 Injecting into {n} <verse> tags for section [{tag}] ({len(chord_lines)} lines total)")

            for i, verse in enumerate(xml_verses):
                start = i * lines_per_verse
                end = (i + 1) * lines_per_verse if i < n - 1 else len(chord_lines)
                slice_lines = chord_lines[start:end]
                verse.text = "\n".join(slice_lines)
        else:
            print(f"⏭️ No matching ChordPro section for [{tag}], skipping")

    return ET.tostring(root, encoding='unicode')

def find_best_song_match(cursor, title, author=None):
    cursor.execute("SELECT id, title, copyright, lyrics FROM songs WHERE title like ?", (title,))
    matches = cursor.fetchall()
    print(matches)
    if not matches:
        return None

    if len(matches) == 1:
        return matches[0]

    if author:
        for song in matches:
            db_copyright = (song[2] or "").lower()
            # Attempt to match just the name part
            if author.lower() in db_copyright:
                return song

    return matches[0]


    return matches[0]

def inject_chords_to_openlp(title, author, chord_sections, dry_run=False):
    conn = sqlite3.connect(OPENLP_DB_PATH)
    cursor = conn.cursor()

    match = find_best_song_match(cursor, title, author)
    if not match:
        log(f"❌ Could not find '{title}' by '{author}' in database.")
        return

    song_id, _, _, lyrics = match
    updated_lyrics = lyrics
    print(lyrics)

    updated_lyrics = inject_chords_into_lyrics_xml(lyrics, parse_chordpro_into_verses(read_chordpro_contents(get_latest_chordpro_file())))
    updated_lyrics = '<?xml version=\'1.0\' encoding=\'UTF-8\'?>' + updated_lyrics

    if dry_run:
        log(f"🧪 Dry-run for '{title}' by '{author}'")
        print("\n--- Injected Lyrics ---\n")
        print(updated_lyrics)
        print("\n------------------------\n")
    else:
        cursor.execute("UPDATE songs SET lyrics = ? WHERE id = ?", (updated_lyrics, song_id))
        conn.commit()
        log(f"✅ Injected chords into '{title}'")
    conn.close()

def extract_lyrics_xml(xml_text):
    root = ET.fromstring(xml_text)
    lyrics_element = root.find('.//lyrics')
    if lyrics_element is None:
        raise ValueError("No <lyrics> tag found")

    # Return inner XML of <lyrics> only
    return ''.join(ET.tostring(e, encoding='unicode') for e in lyrics_element)

def process_single_song(cho_file=None, dry_run=False):
    CCLI_COOKIES = [
    {
        "name": "CCLI_AUTH",
        "value": "",
        "domain": ".ccli.com"
    },
    {
        "name": "CCLI_JWT_AUTH",
        "value": "",
        "domain": ".ccli.com"
    },
    {
        "name": ".AspNetCore.Antiforgery.9fXoN5jHCXs",
        "value": "",
        "domain": "songselect.ccli.com"
    },
    {
        "name": "ARRAffinity",
        "value": "",
        "domain": ".songselect.ccli.com"
    },
    {
        "name": "ARRAffinitySameSite",
        "value": "",
        "domain": ".songselect.ccli.com"
    },
    {
        "name": "cf_clearance",
        "value": "",
        "domain": ".ccli.com"
    },
    {
        "name": "TiPMix",
        "value": "",
        "domain": ".songselect.ccli.com"
    },
    {
        "name": "x-ms-routing-name",
        "value": "",
        "domain": ".songselect.ccli.com"
    },
]

    if cho_file and os.path.exists(cho_file):
        title, author = extract_title_artist_from_filename(cho_file)
        with open(cho_file) as f:
            chordpro_text = f.read()
    else:
        print("🎤 Enter song title:")
        title = input("> ").strip()
        print("🎼 Enter artist (optional):")
        author = input("> ").strip() or None
        result = search_song(title, author, cookies=CCLI_COOKIES)
        if not result and author:
            print("🔄 Retrying search without artist...")
            result = search_song(title, cookies=CCLI_COOKIES)

        if not result:
            log(f"❌ No match found for '{title}'")
            return
        print(result["url"])
        download_chordpro(result["url"],cookies=CCLI_COOKIES)

        chordpro_text = read_chordpro_contents(get_latest_chordpro_file())

    if not chordpro_text:
        log(f"❌ Failed to download ChordPro for '{title}'")
        return

    _, chord_sections = parse_chordpro_text(chordpro_text)
    inject_chords_to_openlp(title, author, chord_sections, dry_run)

def process_all_songs(dry_run=False):
    if not dry_run:
        backup_database()

    conn = sqlite3.connect(OPENLP_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT title, author FROM songs")
    songs = cursor.fetchall()
    conn.close()

    for title, author in songs:
        log(f"\n🎵 Processing: {title} ({author})")
        url = search_song(title, author)
        if not url and author:
            url = search_song(title)
        if not url:
            log("⏭️  Skipping (not found)")
            continue

        chordpro_text = download_chordpro(url)
        if not chordpro_text:
            log("⏭️  Skipping (download failed)")
            continue

        _, chord_sections = parse_chordpro_text(chordpro_text)
        inject_chords_to_openlp(title, author, chord_sections, dry_run)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inject ChordPro chords into OpenLP songs")
    parser.add_argument("--file", help="Path to ChordPro file (.cho) for single song")
    parser.add_argument("--batch", action="store_true", help="Process all songs in OpenLP database")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without saving to DB")
    args = parser.parse_args()

    if args.batch:
        process_all_songs(dry_run=args.dry_run)
    else:
        process_single_song(args.file, dry_run=args.dry_run)
