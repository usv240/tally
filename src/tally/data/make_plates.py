"""Compose the two "after the fix" photographs from the individual food photographs.

When a provider adds the missing component and photographs the plate again, the second photograph
shows the same meal plus one more food. There is no openly licensed photograph of exactly that, so
these two images are composed from the real photographs already in this folder, laid out side by
side on a plain surface.

They are composites of real food photographs, not renderings, and ATTRIBUTION.md says so. Every
credit for the source photographs still applies.

Run: python -m tally.data.make_plates
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

# name -> (source files, caption for the attribution table)
COMPOSITES: dict[str, tuple[list[str], str]] = {
    "oatmeal_with_milk": (
        ["oatmeal.jpg", "milk.jpg"],
        "Breakfast after the missing milk was added.",
    ),
    "chicken_rice_veg_fixed": (
        ["chicken_rice_veg.jpg", "milk.jpg", "orange_slices.jpg"],
        "Lunch after the missing milk and fruit were added.",
    ),
}

BACKGROUND = (238, 234, 226)  # a plain, slightly warm surface
PAD = 26


def compose(paths: list[Path], dest: Path, cell: int = 460) -> None:
    """Lay the foods out in a row on a plain surface, each scaled to the same square cell."""
    tiles = []
    for p in paths:
        im = Image.open(p).convert("RGB")
        side = min(im.size)
        left = (im.width - side) // 2
        top = (im.height - side) // 2
        tiles.append(im.crop((left, top, left + side, top + side)).resize((cell, cell), Image.LANCZOS))

    width = PAD + len(tiles) * (cell + PAD)
    canvas = Image.new("RGB", (width, cell + 2 * PAD), BACKGROUND)
    for i, tile in enumerate(tiles):
        canvas.paste(tile, (PAD + i * (cell + PAD), PAD))
    if canvas.width > 1400:
        canvas = canvas.resize((1400, round(canvas.height * 1400 / canvas.width)), Image.LANCZOS)
    canvas.save(dest, "JPEG", quality=88, optimize=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="data/plates")
    args = ap.parse_args()
    d = Path(args.dir)

    made = []
    for name, (sources, caption) in COMPOSITES.items():
        paths = [d / s for s in sources]
        missing = [p.name for p in paths if not p.exists()]
        if missing:
            print(f"  skipping {name}: missing {missing}. Run fetch_plates first.")
            continue
        dest = d / f"{name}.jpg"
        compose(paths, dest)
        made.append((dest.name, sources, caption))
        print(f"  {name:26s} from {', '.join(sources)}  {dest.stat().st_size // 1024} KB")

    if made:
        note = ["", "## Composed images", "",
                "These two are composites of the photographs above, laid out side by side on a plain",
                "surface by `src/tally/data/make_plates.py`. They stand in for the second photograph a",
                "provider takes after adding a missing component. The credits above still apply.", "",
                "| File | Composed from | Stands for |", "|---|---|---|"]
        for name, sources, caption in made:
            note.append(f"| `{name}` | {', '.join('`' + s + '`' for s in sources)} | {caption} |")
        att = d / "ATTRIBUTION.md"
        text = att.read_text(encoding="utf-8") if att.exists() else "# Photograph credits\n"
        marker = "## Composed images"
        if marker in text:
            text = text[: text.index(marker)].rstrip() + "\n"
        att.write_text(text + "\n".join(note) + "\n", encoding="utf-8")
        print(f"\nupdated {att}")


if __name__ == "__main__":
    main()
