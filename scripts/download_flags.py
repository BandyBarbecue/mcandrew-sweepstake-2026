"""Dev-only: download flag SVGs (site) and 40px PNGs (email) from flagcdn.com.
Not part of the scheduled chain. Validates coverage against participants.json.
"""
import json
import os
import sys
import requests

ROOT = os.path.join(os.path.dirname(__file__), "..")

def main():
    with open(os.path.join(ROOT, "flag-codes.json"), encoding="utf-8") as f:
        codes = json.load(f)
    with open(os.path.join(ROOT, "participants.json"), encoding="utf-8") as f:
        owners = json.load(f)["countryToOwner"]

    missing = sorted(set(owners) - set(codes))
    if missing:
        sys.exit(f"flag-codes.json is missing: {missing}")

    svg_dir = os.path.join(ROOT, "flags")
    png_dir = os.path.join(ROOT, "flags", "png")
    os.makedirs(png_dir, exist_ok=True)

    for country, code in sorted(codes.items()):
        svg = requests.get(f"https://flagcdn.com/{code}.svg", timeout=30)
        svg.raise_for_status()
        with open(os.path.join(svg_dir, f"{code}.svg"), "wb") as f:
            f.write(svg.content)
        png = requests.get(f"https://flagcdn.com/w40/{code}.png", timeout=30)
        png.raise_for_status()
        with open(os.path.join(png_dir, f"{code}.png"), "wb") as f:
            f.write(png.content)
        print(f"  {country} -> {code}")

    fallback = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 4 3">'
                '<rect width="4" height="3" fill="#5a6b5e"/>'
                '<path d="M0 0h4L0 3z" fill="#6b7a6e"/></svg>')
    with open(os.path.join(svg_dir, "_fallback.svg"), "w", encoding="utf-8") as f:
        f.write(fallback)

    print(f"OK: {len(codes)}/48 flags downloaded")

if __name__ == "__main__":
    main()
