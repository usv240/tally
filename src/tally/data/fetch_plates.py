"""Fetch openly licensed food photographs from Wikimedia Commons for the demo.

Tally's vision step has to be tested against real photographs or the test proves nothing. These are
real photographs of real food under open licences, downloaded by this script and credited in
data/plates/ATTRIBUTION.md with their licence and author.

The files are named by hand rather than found by search. Search returned a 1921 photograph of a farm
milk cooler for "glass of milk", and an art piece for "apple slices", which would have made the
vision results meaningless. Naming the files keeps the demo honest and repeatable.

Run: python -m tally.data.fetch_plates
"""

from __future__ import annotations

import argparse
import io
import json
import re
import time
from pathlib import Path

import httpx
from PIL import Image

API = "https://commons.wikimedia.org/w/api.php"
UA = "tally-hackathon/1.0 (ujwalvanjare6@gmail.com)"
OK_LICENCES = ("cc0", "public domain", "cc by", "cc by-sa", "pd")

# Local name -> exact Commons file title. Every one of these was checked by eye.
PLATES: dict[str, str] = {
    # Multi-component meals, which is what a provider actually photographs.
    "lunch_tray": "File:School lunch tray MyPlate 20210810-FNS-UNC-0015.jpg",
    "chicken_rice_veg": "File:Liat Portal for Foodie Disorder - Grilled chicken with rice and vegetables.jpg",
    "school_lunch_fi": "File:School lunch in ylästö school.jpg",
    # Single foods, for the fix step and for component-level testing.
    "milk": "File:Glass of Milk (33657535532).jpg",
    "yogurt": "File:Yoghurt in bowl 011715.jpg",
    "banana": "File:Banana on whitebackground.jpg",
    "oatmeal": "File:Oatmeal porridge 1-minute with additional ingredients.jpg",
    "crackers": "File:Whole wheat Ritz Cracker (7571386026).jpg",
    "orange_slices": "File:Blood orange slice.jpg",
    "pear": "File:Pears whole and in different stages of eating.jpg",
    "green_beans": "File:Liat Portal for Foodie Disorder - Sautéed Green Beans with Onions.jpg",
}


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def write_jpeg(data: bytes, dest: Path, max_width: int = 1024) -> None:
    """Save any downloaded image as a plain RGB JPEG of a sensible size.

    Commons serves both PNG and JPEG. Writing PNG bytes into a file called .jpg produces a file
    whose name lies about its format, which the vision API rejects.
    """
    im = Image.open(io.BytesIO(data))
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    if im.width > max_width:
        im = im.resize((max_width, round(im.height * max_width / im.width)), Image.LANCZOS)
    im.save(dest, "JPEG", quality=88, optimize=True)


def fetch_info(client: httpx.Client, title: str) -> dict | None:
    r = client.get(API, params={
        "action": "query", "titles": title, "prop": "imageinfo",
        "iiprop": "url|extmetadata|mime", "iiurlwidth": 1024, "format": "json",
    })
    r.raise_for_status()
    pages = r.json().get("query", {}).get("pages", {})
    for p in pages.values():
        info = (p.get("imageinfo") or [{}])[0]
        if not info.get("thumburl"):
            continue
        md = info.get("extmetadata", {})
        licence = strip_html(md.get("LicenseShortName", {}).get("value", ""))
        if not any(tag in licence.lower() for tag in OK_LICENCES):
            print(f"  skipping {title}: licence is {licence!r}")
            return None
        return {
            "title": p["title"],
            "url": info["thumburl"],
            "descriptionurl": info.get("descriptionurl", ""),
            "licence": licence,
            "author": strip_html(md.get("Artist", {}).get("value", "")) or "unknown",
        }
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/plates")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    chosen: list[dict] = []
    with httpx.Client(timeout=40, headers={"User-Agent": UA}, follow_redirects=True) as client:
        for name, title in PLATES.items():
            info = fetch_info(client, title)
            if info is None:
                print(f"  MISSING {name}: {title}")
                continue
            dest = out / f"{name}.jpg"
            img = client.get(info["url"])
            img.raise_for_status()
            write_jpeg(img.content, dest)
            info["file"] = dest.name
            info["food"] = name
            chosen.append(info)
            print(f"  {name:18s} {info['licence']:16s} {dest.stat().st_size // 1024:4d} KB")
            time.sleep(0.4)

    (out / "sources.json").write_text(json.dumps(chosen, indent=1), encoding="utf-8")

    lines = [
        "# Photograph credits",
        "",
        "Every photograph here came from Wikimedia Commons under an open licence, downloaded by",
        "`src/tally/data/fetch_plates.py`. They stand in for the photographs a provider would take in",
        "her own kitchen, so that Tally's vision step is tested against real food rather than drawings.",
        "",
        "| File | Source | Licence | Author |",
        "|---|---|---|---|",
    ]
    for c in chosen:
        title = c["title"].replace("File:", "")
        lines.append(f"| `{c['file']}` | [{title}]({c['descriptionurl']}) | {c['licence']} | {c['author']} |")
    (out / "ATTRIBUTION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nwrote {len(chosen)} photographs and ATTRIBUTION.md to {out}")


if __name__ == "__main__":
    main()
