import re
from collections import defaultdict

def parse_chordpro_text(text):
    sections = defaultdict(list)
    current_section = "unknown"

    lines = text.splitlines()
    for line in lines:
        if line.strip().lower().startswith("chorus") or \
           line.strip().lower().startswith("verse") or \
           line.strip().lower().startswith("bridge") or \
           line.strip().lower().startswith("intro") or \
           line.strip().lower().startswith("interlude") or \
           line.strip().lower().startswith("tag") or \
           line.strip().lower().startswith("outro"):

            current_section = line.strip().split()[0].capitalize()
            match = re.search(r"(\d+)", line)
            if match:
                current_section += f":{match.group(1)}"
            continue

        # Skip empty lines
        if not line.strip():
            continue

        # Remove measure markings like [| D / / / |]
        if re.match(r"^\[\|.*\|\]$", line.strip()):
            continue

        # Normalize chord spacing
        line = re.sub(r'\s+', ' ', line.strip())
        sections[current_section].append(line)

    return list(sections.keys()), dict(sections)

def parse_chordpro_into_verses(chordpro_text):
    verses = {}
    current_label = None
    current_lines = []

    # Regex to detect section headings like {comment: Verse 1}
    section_pattern = re.compile(r'{comment:\s*(.*?)\s*}', re.IGNORECASE)

    # Mapping from section types to OpenLP verse types
    section_map = {
        'verse': 'v',
        'chorus': 'c',
        'pre-chorus': 'p',
        'bridge': 'b',
        'interlude': 'i',
        'intro': 'i',
        'instrumental': 'i',
        'ending': 'e',
        'tag': 't',
    }

    def flush_current():
        nonlocal current_label, current_lines
        if current_label and current_lines:
            verses[current_label] = '\n'.join(current_lines).strip()
        current_label = None
        current_lines = []

    for line in chordpro_text.splitlines():
        line = line.strip()

        # Skip empty or metadata lines
        if not line or line.startswith('{') and not line.startswith('{comment:'):
            continue

        # Detect section headers
        match = section_pattern.match(line)
        if match:
            flush_current()
            raw_section = match.group(1).lower()

            # Extract section type and optional number
            match_section = re.match(r'([a-z\- ]+)\s*(\d*)', raw_section)
            if match_section:
                base, num = match_section.groups()
                base = base.strip().replace('-', ' ')
                base_key = base.split()[0]  # e.g., "pre-chorus" → "pre"
                verse_type = section_map.get(base_key, 'x')
                suffix = num if num else str(len([k for k in verses if k.startswith(verse_type)]) + 1)
                current_label = f"{verse_type}{suffix}"
                current_lines = []
            continue

        # Add content line to current section
        current_lines.append(line)

    flush_current()
    return verses