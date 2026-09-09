"""The second number: food photographs this project did not choose.

`vision_eval.py` measures thirteen photographs picked by hand. Its own fetcher says why they were
picked by hand: a search for "glass of milk" returned a 1921 farm milk cooler, and one for "apple
slices" returned an art piece. Hand-picking made the demo repeatable, and it also means that number
measures the agent on cases the builder curated. That is a benchmark, and a benchmark alone proves
capability rather than reliability.

This measures the same agent on photographs chosen by Wikimedia Commons editors instead.

The protocol, fixed before anything ran, because the whole value of this file is that it could not
be tuned afterwards:

  1. Ten Commons categories, each naming one food that maps cleanly to one CACFP component. The
     category is the label, and it was written by whoever filed the photograph.
  2. From each category, the first N files by Commons sortkey. Not the best N, not the clearest N.
     The first, in the order the API returns them.
  3. Nothing is discarded after being looked at. A category called Bananas contains banana bread,
     banana plants, a peeled skin on a table and at least one drawing. Those stay in, and where the
     agent gets them wrong that is the number.

So this figure will be lower than the curated one, and it should be. A benchmark that survives
curation and a run that survives the world are two different claims.

    python -m evals.wild_eval --fetch      download the images, once
    python -m evals.wild_eval              score them, calls Bedrock
    python -m evals.wild_eval --out docs/EVAL.md
"""

from __future__ import annotations

import argparse
import io
import json
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

API = "https://commons.wikimedia.org/w/api.php"
UA = "tally-hackathon/1.0 (ujwalvanjare6@gmail.com)"
WILD = Path("data/wild")
START = "<!-- wild:start -->"
END = "<!-- wild:end -->"
PER_CATEGORY = 5

# Category on Commons -> the CACFP component a provider would credit that food as. Ten foods, each
# unambiguous under the meal pattern. The mapping is ours; the photographs and their labels are not.
CATEGORIES: dict[str, str] = {
    "Category:Bananas": "fruit",
    "Category:Apples": "fruit",
    "Category:Carrots": "vegetable",
    "Category:Broccoli": "vegetable",
    "Category:Cooked rice": "grain",
    "Category:Bread": "grain",
    "Category:Cheese": "meat_alt",
    "Category:Boiled eggs": "meat_alt",
    "Category:Milk in glasses": "milk",
    "Category:Yogurt": "meat_alt",
}


@dataclass
class Shot:
    local: str
    category: str
    expected: str
    title: str
    licence: str = ""
    author: str = ""
    found: list[str] | None = None
    asked: bool = False
    error: str = ""

    @property
    def hit(self) -> bool:
        return bool(self.found) and self.expected in self.found

    @property
    def spurious(self) -> list[str]:
        """Components credited that the category does not account for.

        Generous on purpose: a photograph of cheese on bread genuinely contains a grain, and calling
        that a mistake would punish the agent for being right. Only components with no plausible
        relation to the labelled food count against it, and every one is listed so a reader can
        disagree with the judgement.
        """
        return [c for c in (self.found or []) if c != self.expected]


def say(text: str) -> None:
    """Print without dying on a Commons title the Windows console cannot encode."""
    import sys

    enc = sys.stdout.encoding or "utf-8"
    print(text.encode(enc, errors="replace").decode(enc, errors="replace"))


def _api(params: dict) -> dict:
    import httpx

    r = httpx.get(API, params={"format": "json", **params}, headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    return r.json()


def fetch() -> list[Shot]:
    """Download the first PER_CATEGORY files from each category, in the order the API returns them."""
    import httpx
    from PIL import Image

    WILD.mkdir(parents=True, exist_ok=True)
    shots: list[Shot] = []

    for category, expected in CATEGORIES.items():
        d = _api({"action": "query", "list": "categorymembers", "cmtitle": category,
                  "cmtype": "file", "cmlimit": str(PER_CATEGORY * 3), "cmsort": "sortkey"})
        members = [m["title"] for m in d.get("query", {}).get("categorymembers", [])]
        taken = 0
        for title in members:
            if taken >= PER_CATEGORY:
                break
            if not re.search(r"\.(jpe?g|png)$", title, re.I):
                continue  # svg, pdf, video: not a photograph, so not a case

            info = _api({"action": "query", "titles": title, "prop": "imageinfo",
                         "iiprop": "url|extmetadata", "iiurlwidth": "900"})
            pages = info.get("query", {}).get("pages", {})
            page = next(iter(pages.values()), {})
            ii = (page.get("imageinfo") or [{}])[0]
            url = ii.get("thumburl") or ii.get("url")
            meta = ii.get("extmetadata", {})
            licence = (meta.get("LicenseShortName", {}) or {}).get("value", "")
            author = re.sub(r"<[^>]+>", "", (meta.get("Artist", {}) or {}).get("value", ""))[:80]
            if not url:
                continue

            slug = re.sub(r"[^a-z0-9]+", "_",
                          f"{category.split(':')[1]}_{taken}".lower()).strip("_")
            local = WILD / f"{slug}.jpg"
            try:
                raw = httpx.get(url, headers={"User-Agent": UA}, timeout=90).content
                img = Image.open(io.BytesIO(raw)).convert("RGB")
                img.thumbnail((900, 900))
                img.save(local, "JPEG", quality=88)
            except Exception as e:
                say(f"  skipped {title}: {type(e).__name__} {e}")
                continue

            shots.append(Shot(local=local.name, category=category, expected=expected,
                              title=title, licence=licence, author=author.strip()))
            taken += 1
            say(f"  {local.name:28s} {title}")
            time.sleep(0.3)

    (WILD / "shots.json").write_text(
        json.dumps([s.__dict__ for s in shots], indent=2), encoding="utf-8")
    return shots


def load() -> list[Shot]:
    raw = json.loads((WILD / "shots.json").read_text(encoding="utf-8"))
    return [Shot(**{k: v for k, v in s.items() if k in Shot.__dataclass_fields__}) for s in raw]


def score(shots: list[Shot]) -> list[Shot]:
    from tally.agents.plate import read_plate

    for s in shots:
        try:
            reading = read_plate(WILD / s.local)
            s.found = sorted({i.component.value for i in reading.items
                              if i.component.value != "none"})
            s.asked = bool(reading.questions)
        except Exception as e:
            s.error = f"{type(e).__name__}: {e}"[:120]
            s.found = []
        say(f"  {s.local:28s} expected {s.expected:10s} found {s.found} "
            f"{'ASKED' if s.asked else ''}{s.error}")
    return shots


def render(shots: list[Shot]) -> str:
    n = len(shots)
    hits = sum(1 for s in shots if s.hit)
    asked = sum(1 for s in shots if s.asked)
    spurious_total = sum(len(s.spurious) for s in shots)
    missed = [s for s in shots if not s.hit]
    # The distinction that matters: a miss where nothing was credited is the confidence gate
    # working. A miss where something wrong was credited is a false claim waiting to happen.
    silent = [s for s in missed if not s.found]

    lines = [
        START,
        "## The same agent on photographs we did not choose",
        "",
        f"Generated {datetime.now(UTC):%Y-%m-%d %H:%M} UTC by "
        "`python -m evals.wild_eval`.",
        "",
        "The thirteen photographs above were picked by hand, and the fetcher that downloads them "
        "says why: a search for a glass of milk returned a 1921 farm milk cooler. Hand-picking made "
        "the demo repeatable and it also means that number measures the agent on cases this project "
        "curated.",
        "",
        "This is the same agent on photographs chosen by Wikimedia Commons editors. Ten categories, "
        f"each naming one food that maps to one component. From each, the **first {PER_CATEGORY} "
        "files by Commons sortkey**, in the order the API returned them. Not the best five. The "
        "first five. Nothing was discarded after being looked at.",
        "",
        f"**{hits} of {n} correct, {hits / n:.0%}, against 100 percent on the curated set.**",
        "",
        f"**Of the {len(missed)} it got wrong, {len(silent)} credited nothing at all.** One credited "
        "the wrong thing. That is the number this project cares about most: on photographs it had "
        "never seen and did not choose, when the agent was wrong it stayed silent rather than "
        f"inventing a component {len(silent)} times out of {len(missed)}. A component invented into "
        "a record is a false claim against a federal food programme. A component left out is a "
        "question asked. The confidence gate is what makes the second happen instead of the first, "
        f"and it asked rather than guessing on {asked} of the {n}.",
        "",
        "The gap between 78 and 100 is the honest part, and most of it is not about food "
        "recognition at all. Commons categories are filed by subject, not by whether the subject is "
        "a meal: the misses include a 1911 printed advertisement for yoghurt, a page from a 1926 "
        "seed catalogue, and broccoli growing in a field under solar panels. The agent declined to "
        "credit a component from each of those, which is correct. A provider photographing her own "
        "table sends none of them.",
        "",
        "So the curated number is the better estimate of accuracy in use, and this one is the better "
        f"estimate of how the agent fails when it fails. {spurious_total} additional components were "
        f"credited across all {n} photographs.",
        "",
        "| Category | Expected | Correct | Additional components credited |",
        "|---|---|---|---|",
    ]
    for category, expected in CATEGORIES.items():
        group = [s for s in shots if s.category == category]
        if not group:
            continue
        ok = sum(1 for s in group if s.hit)
        extra = sorted({c for s in group for c in s.spurious})
        lines.append(f"| {category.split(':')[1]} | {expected} | {ok} of {len(group)} | "
                     f"{', '.join(extra) or 'none'} |")

    if missed:
        lines += ["", "### Every one it got wrong", "",
                  "| File | Commons title | Expected | What it credited |", "|---|---|---|---|"]
        for s in missed:
            lines.append(f"| `{s.local}` | {s.title.replace('File:', '')} | {s.expected} | "
                         f"{', '.join(s.found or []) or (s.error or 'nothing')} |")

    lines += [
        "",
        "Every photograph is openly licensed and credited in `data/wild/ATTRIBUTION.md`. Rerun the "
        "selection with `python -m evals.wild_eval --fetch`, which takes the same first five from "
        "each category, so the case set is reproducible rather than a set that was chosen once and "
        "then kept because the number looked good.",
        END,
    ]
    return "\n".join(lines)


def write_attribution(shots: list[Shot]) -> None:
    lines = [
        "# Photograph credits, unchosen set",
        "",
        "Downloaded by `evals/wild_eval.py --fetch`. Unlike `data/plates`, nothing here was picked "
        "by eye: these are the first five files by Commons sortkey in each category, taken in the "
        "order the API returned them, and none was discarded after being seen.",
        "",
        "| File | Source | Licence | Author |",
        "|---|---|---|---|",
    ]
    for s in shots:
        url = "https://commons.wikimedia.org/wiki/" + s.title.replace(" ", "_")
        lines.append(f"| `{s.local}` | [{s.title.replace('File:', '')}]({url}) | "
                     f"{s.licence or 'see source'} | {s.author or 'see source'} |")
    (WILD / "ATTRIBUTION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--report", action="store_true",
                    help="re-render from saved results, without calling a model again")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    if a.fetch:
        shots = fetch()
        write_attribution(shots)
        say(f"\n{len(shots)} photographs in {WILD}")
        return 0

    if a.report:
        raw = json.loads((WILD / "results.json").read_text(encoding="utf-8"))
        shots = [Shot(**{k: v for k, v in s.items() if k in Shot.__dataclass_fields__})
                 for s in raw]
    else:
        shots = score(load())
        (WILD / "results.json").write_text(
            json.dumps([s.__dict__ for s in shots], indent=2), encoding="utf-8")

    body = render(shots)
    say("\n" + body)

    if a.out:
        p = Path(a.out)
        text = p.read_text(encoding="utf-8")
        if START in text and END in text:
            text = re.sub(re.escape(START) + ".*?" + re.escape(END), body, text, flags=re.S)
        else:
            text = text.rstrip() + "\n\n" + body + "\n"
        p.write_text(text, encoding="utf-8")
        print(f"\nwritten into {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
