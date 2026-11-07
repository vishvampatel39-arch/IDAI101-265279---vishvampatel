"""
Rebuilds the Screenshots section of README.md from the pictures in the 'screenshots' folder,
using the real file names (spaces and brackets are fine: they are encoded so GitHub shows them).

Run it from the project folder:   py update_screenshots.py
Run it again whenever you add or replace a screenshot.
"""
import os
import re
from urllib.parse import quote

START, END = "<!-- SCREENSHOTS:START -->", "<!-- SCREENSHOTS:END -->"
PICTURES = (".png", ".jpg", ".jpeg", ".gif", ".webp")

# Captions for the first screenshots, matched by the number in the file name, e.g. "Screenshot (112).png".
# Edit these, or edit the captions directly in README.md afterwards.
CAPTIONS = {
    "112": "Dashboard: add a medicine and today's checklist",
    "113": "Medji answering a question about paracetamol",
    "114": "Anticholinergic check and the ACB scale",
    "115": "Compare two medicines",
    "116": "Learn page: why people forget",
    "117": "Find a nearby pharmacy",
    "118": "SOS page with one-tap call buttons",
}


def natural_key(name):
    """Sort 'Screenshot (9)' before 'Screenshot (10)'."""
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", name)]


def build_lines(files):
    """One markdown image line per file."""
    lines = []
    for f in sorted(files, key=natural_key):
        number = re.search(r"\d+", f)
        caption = CAPTIONS.get(number.group(0)) if number else None
        caption = caption or os.path.splitext(f)[0].replace("_", " ")
        lines.append(f"![{caption}](screenshots/{quote(f)})")
    return lines


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    folder = os.path.join(here, "screenshots")
    if not os.path.isdir(folder):
        raise SystemExit("There is no 'screenshots' folder next to this script.")
    files = [f for f in os.listdir(folder) if f.lower().endswith(PICTURES)]
    if not files:
        raise SystemExit("The screenshots folder has no pictures yet.")
    readme_path = os.path.join(here, "README.md")
    readme = open(readme_path, encoding="utf-8").read()
    if START not in readme or END not in readme:
        raise SystemExit(f"README.md must contain {START} and {END}.")
    block = START + "\n" + "\n".join(build_lines(files)) + "\n" + END
    before, rest = readme.split(START, 1)
    after = rest.split(END, 1)[1]
    open(readme_path, "w", encoding="utf-8").write(before + block + after)
    print(f"README.md updated with {len(files)} screenshots:")
    for f in sorted(files, key=natural_key):
        print("  ", f)


if __name__ == "__main__":
    main()
