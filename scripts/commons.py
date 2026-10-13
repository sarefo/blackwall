"""Wikimedia Commons: lookup, description pages and upload for the Blackwall figures.

  commons.py lookup                 cache taxon categories and Wikidata items (data/commons_cache.json)
  commons.py names                  write commons_filename into data/figures.csv
  commons.py pages                  write work/pages/<id>.wiki for every row
  commons.py upload [--go] [--limit N] [--ids ID ...] [--plate N]
                                    dry run unless --go; uploads rows with crop_ok and names_checked ticked
                                    and uploaded empty, tight crop (work/tight) as the file
  commons.py plates [--go]          add {{Image extracted}} lines for the uploaded crops to the plate pages

Login: pywikibot with the bot password kept in C:\\dev\\koch (user-config.py, user-password.py; both gitignored).
Run with the Koch venv: PYWIKIBOT_DIR is set below.
"""
import argparse
import csv
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
TABLE = ROOT / "data" / "figures.csv"
CACHE = ROOT / "data" / "commons_cache.json"
API = "https://commons.wikimedia.org/w/api.php"
UA = "blackwall-figures/0.1 (sarefo@gmail.com)"
YES = {"true", "x", "yes", "1", "ok"}
PAUSE = 12  # seconds between files; the account has no bot flag
IA = "historyspidersg00blac"
WORK = "A History of the Spiders of Great Britain and Ireland"
WORK_CAT = "John Blackwall A history of the Spiders of Great Britain and Ireland"
BLACKWALL_Q = "Q661407"
TITLE_SHORT = "A history of the spiders of Great Britain and Ireland"
RETOUCH = ("Figure cut out of the plate scan along a mask (made semi-automatically, checked by hand); stains, "
           "show-through text, leader lines and neighboring figures removed, background set to white. "
           "The figure itself is not redrawn.")
ROMAN = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
         (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
S = requests.Session()
S.headers["User-Agent"] = UA


def roman(n):
    out = ""
    for v, s in ROMAN:
        while n >= v:
            out, n = out + s, n - v
    return out


def rows_load():
    return list(csv.DictReader(TABLE.open(encoding="utf-8")))


def rows_save(rows):
    with TABLE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def plate_page(tafel):
    """Commons file of the whole plate (plate 1 is spelled with an Arabic numeral there)."""
    n = int(tafel)
    return "File:BlackwallSpidersPlate1.jpg" if n == 1 else f"File:BlackwallSpidersPlate{roman(n)}.jpg"


def lower_epithets(name):
    """Genus capitalized, epithets lowercase (ICZN); the spelling stays as printed."""
    w = name.split()
    return " ".join([w[0]] + [x.lower() for x in w[1:]])


def figure_label(r):
    """'1a', '226e-2' -> 'fig. 1a', 'fig. 226e (2)' ; ids look like 021_226e-2."""
    f = r["figur"]
    m = re.fullmatch(r"(.+)-(\d+)", f)
    return f"fig. {m.group(1)} ({m.group(2)})" if m else f"fig. {f}"


def filename(r):
    return (f"Blackwall {r['year']} {TITLE_SHORT} pl. {roman(int(r['tafel']))} {figure_label(r)} "
            f"{lower_epithets(r['orig_taxon'])}.jpg")


def shows_text(r):
    return r["origin"].replace("♀", "female").replace("♂", "male").strip()


def image_file(r):
    return ROOT / "work" / "tight" / Path(r["crop_file"]).name


def categories(r, cache):
    ex = cache.get("exists", {})
    t = r["modern_taxon"]
    sort = f"{int(r['tafel']):02d} {r['figur']}"
    cats = [f"{WORK_CAT}|{sort}"]
    if t and ex.get(f"Category:{t}"):
        cats.append(t)
    elif t and ex.get(f"Category:{t.split()[0]}"):
        cats.append(t.split()[0])
    elif r["family"] and ex.get(f"Category:{r['family']}"):
        cats.append(r["family"])
    return cats


def page_text(r, cache):
    tab, fig = int(r["tafel"]), r["figur"]
    orig, modern = r["orig_taxon"], r["modern_taxon"]
    vol = f"vol. {r['band']}"
    if modern and modern != orig:
        name = f"''{orig}'' (current name: ''{modern}''{', ' + r['family'] if r['family'] else ''})"
    elif modern:
        name = f"''{orig}''{' (' + r['family'] + ')' if r['family'] else ''}"
    else:
        name = f"''{orig}''"
    where = f", p. {r['page']}" if r["page"] else ""
    shows = shows_text(r)
    en = (f"{name}. Figure {fig.replace('-', ' ')} from John Blackwall, ''{WORK}'', {vol} ({r['year']}), "
          f"plate {roman(tab)}{where}. " + (f"Shows: {shows}. " if shows else "") + "Hand-colored engraving.")
    if r["name_note"] and "WSC:" not in r["name_note"]:
        en += f" Note on the name: {r['name_note']}."
    source = (f"{r['citation'].split(' doi:')[0].strip()} Scan: "
              f"[https://archive.org/details/{IA} Internet Archive {IA}] (Harvard MCZ copy), plate {roman(tab)}.")
    plate = plate_page(tab)
    lines = [
        "=={{int:filedesc}}==",
        "{{Information",
        f"|description={{{{en|1={en}}}}}",
        f"|date={r['year']}",
        f"|source={source}",
        "|author=John Blackwall",
        "|permission=",
        f"|other versions=whole plate: [[:{plate}]]",
        "}}",
        f"{{{{Retouched picture|{RETOUCH}|editor=Sarefo}}}}",
        "",
        "=={{int:license-header}}==",
        "{{PD-old-100-expired}}",
        "",
    ]
    lines += [f"[[Category:{c}]]" for c in categories(r, cache)]
    return "\n".join(lines) + "\n"


def claims(r, cache):
    """Structured data: depicts, creator, inception, copyright status."""
    def item(prop, q, quals=None):
        c = {"mainsnak": {"snaktype": "value", "property": prop,
                          "datavalue": {"type": "wikibase-entityid", "value": {"entity-type": "item", "id": q}}},
             "type": "statement", "rank": "normal"}
        if quals:
            c["qualifiers"] = {p: [{"snaktype": "value", "property": p,
                                    "datavalue": {"type": "wikibase-entityid", "value": {"entity-type": "item", "id": v}}}]
                               for p, v in quals.items()}
        return c
    out = [item("P170", BLACKWALL_Q),
           item("P6216", "Q19652", {"P1001": "Q13780930", "P459": "Q29940705"}),
           {"mainsnak": {"snaktype": "value", "property": "P571",
                         "datavalue": {"type": "time", "value": {"time": f"+{r['year']}-00-00T00:00:00Z", "timezone": 0,
                                                                 "before": 0, "after": 0, "precision": 9,
                                                                 "calendarmodel": "http://www.wikidata.org/entity/Q1985727"}}},
            "type": "statement", "rank": "normal"}]
    q = cache.get("wikidata", {}).get(r["modern_taxon"])
    if isinstance(q, str) and q:
        out.insert(0, item("P180", q))
    return out


# ---- lookup -----------------------------------------------------------------

def existing(titles):
    out = {}
    for i in range(0, len(titles), 50):
        r = S.get(API, params={"action": "query", "titles": "|".join(titles[i:i + 50]), "format": "json"}).json()
        norm = {n["to"]: n["from"] for n in r["query"].get("normalized", [])}
        for p in r["query"]["pages"].values():
            out[norm.get(p["title"], p["title"])] = "missing" not in p
    return out


def wikidata_taxa(names):
    values = " ".join(json.dumps(n) for n in names)
    q = f"SELECT ?n ?item WHERE {{ VALUES ?n {{ {values} }} ?item wdt:P225 ?n. }}"
    r = S.post("https://query.wikidata.org/sparql", data={"query": q, "format": "json"},
               headers={"Accept": "application/sparql-results+json"}, timeout=120).json()
    hits = {}
    for b in r["results"]["bindings"]:
        hits.setdefault(b["n"]["value"], set()).add(b["item"]["value"].rsplit("/", 1)[1])
    return {n: (sorted(hits[n])[0] if len(hits.get(n, ())) == 1 else sorted(hits.get(n, []))) for n in names}


def lookup():
    rows = [r for r in rows_load() if r["crop_ok"].strip().lower() in YES]
    taxa = sorted({r["modern_taxon"] for r in rows if r["modern_taxon"]})
    genera = sorted({t.split()[0] for t in taxa})
    families = sorted({r["family"] for r in rows if r["family"]})
    cache = {"exists": existing([f"Category:{t}" for t in taxa + genera + families] + [f"Category:{WORK_CAT}"] +
                                [plate_page(p) for p in range(1, 30)])}
    cache["wikidata"] = wikidata_taxa(taxa)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print("taxa", len(taxa), "| categories missing:", [t for t in taxa if not cache["exists"].get(f"Category:{t}")][:40])
    print("plates missing:", [k for k, v in cache["exists"].items() if k.startswith("File:") and not v])
    print("wikidata unresolved:", [t for t, q in cache["wikidata"].items() if not isinstance(q, str) or not q])


# ---- upload -------------------------------------------------------------------

def approved(r):
    return (r["crop_ok"].strip().lower() in YES and r["names_checked"].strip().lower() in YES
            and r["uploaded"].strip().lower() not in YES)


def taken(names):
    out = set()
    for i in range(0, len(names), 50):
        r = S.get(API, params={"action": "query", "format": "json",
                               "titles": "|".join("File:" + n for n in names[i:i + 50])}).json()
        out |= {p["title"][5:] for p in r["query"]["pages"].values() if "missing" not in p}
    return out


def login():
    os.environ.setdefault("PYWIKIBOT_DIR", r"C:\dev\koch")
    import pywikibot
    site = pywikibot.Site("commons", "commons")
    site.login()
    if "upload" not in site.userinfo.get("rights", []):
        sys.exit("This account has no upload right on Commons.")
    return pywikibot, site


def add_sdc(site, pageid, r, cache):
    site.simple_request(action="wbeditentity", id=f"M{pageid}", data=json.dumps({"claims": claims(r, cache)}),
                        summary="Structured data: depicts, creator, inception, copyright status",
                        token=site.tokens["csrf"], bot=1).submit()
    site.simple_request(action="purge", pageids=str(pageid), forcelinkupdate=1).submit()


def upload(a):
    rows = rows_load()
    cache = json.loads(CACHE.read_text(encoding="utf-8"))
    todo = [r for r in rows if approved(r) and (not a.ids or r["id"] in a.ids)
            and (a.plate is None or int(r["tafel"]) == a.plate)]
    todo = todo[:a.limit] if a.limit else todo
    missing = [r["id"] for r in todo if not image_file(r).exists()]
    if missing:
        sys.exit(f"no tight crop for: {missing[:10]}")
    names = [filename(r) for r in todo]
    dup = {n for n in names if names.count(n) > 1}
    if dup:
        sys.exit(f"duplicate target names: {sorted(dup)[:5]}")
    clash = taken(names)
    print(f"{len(todo)} approved rows; {len(clash)} target names already exist on Commons")
    for r, n in zip(todo, names):
        print(f"  [{'EXISTS' if n in clash else 'ok'}] {r['id']:>9}  {n}")
    if not a.go or not todo:
        print("Dry run. Pass --go to upload.")
        return
    pywikibot, site = login()
    for r, n in zip(todo, names):
        if n in clash:
            continue
        page = pywikibot.FilePage(site, "File:" + n)
        try:
            ok = page.upload(str(image_file(r)), comment=f"Figure {r['figur']} from {WORK} (Blackwall {r['year']})",
                             text=page_text(r, cache), ignore_warnings=False)
        except Exception as e:  # a warning (duplicate, bad name) or a server error: log it and go on
            ok = False
            print("ERROR", n, str(e).splitlines()[0][:200], flush=True)
        if ok:
            page = pywikibot.FilePage(site, "File:" + n)
            r["commons_filename"], r["uploaded"], r["commons_url"] = n, "TRUE", page.full_url().replace("File%3A", "File:")
            rows_save(rows)  # after every file, so an interrupted run loses nothing
            try:
                add_sdc(site, page.pageid, r, cache)
            except Exception as e:
                print("SDC FAILED", n, str(e).splitlines()[0][:200], flush=True)
            print("uploaded", n, flush=True)
        else:
            print("FAILED", n, flush=True)
        time.sleep(PAUSE)


def plates(a):
    """One {{Image extracted}} line per uploaded crop on its plate page."""
    by_plate = {}
    for r in rows_load():
        if r["uploaded"].strip().lower() in YES and r["commons_url"]:
            by_plate.setdefault(plate_page(r["tafel"]), []).append(r["commons_filename"])
    print(len(by_plate), "plate pages to update")
    if not a.go:
        print("Dry run. Pass --go to edit.")
        return
    pywikibot, site = login()
    for p, files in by_plate.items():
        page = pywikibot.FilePage(site, p)
        text = page.text
        new = [f for f in files if f not in text]
        if not new:
            continue
        lines = "\n".join(f"{{{{Image extracted|{f}}}}}" for f in new)
        i = text.find("[[Category:")
        page.text = text[:i] + lines + "\n" + text[i:] if i >= 0 else text + "\n" + lines
        page.save(summary=f"Link {len(new)} figure crop(s) extracted from this plate")
        time.sleep(3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["lookup", "names", "pages", "upload", "plates"])
    ap.add_argument("--go", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--ids", nargs="+")
    ap.add_argument("--plate", type=int)
    a = ap.parse_args()
    if a.cmd == "lookup":
        lookup()
    elif a.cmd == "names":
        rows = rows_load()
        for r in rows:
            r["commons_filename"] = filename(r)
        rows_save(rows)
        print(len({r["commons_filename"] for r in rows}), "unique names for", len(rows), "rows")
    elif a.cmd == "pages":
        cache = json.loads(CACHE.read_text(encoding="utf-8"))
        out = ROOT / "work" / "pages"
        out.mkdir(parents=True, exist_ok=True)
        rows = rows_load()
        for r in rows:
            (out / f"{r['id']}.wiki").write_text(page_text(r, cache), encoding="utf-8", newline="\n")
        print(len(rows), "pages ->", out)
    elif a.cmd == "upload":
        upload(a)
    else:
        plates(a)


if __name__ == "__main__":
    main()
