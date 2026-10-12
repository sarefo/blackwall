"""Merge description text, crops and WSC names into data/figures.csv (the Koch schema, so the shared review app reads it).

Usage: build_table.py
One row per crop in data/groups_*.json. The printed name comes from data/text/PPP.json, the current name from the
WSC "taxa included" lists in data/wsc (ref 302 = Part I, plates 1-12, 1861; ref 328 = Part II, plates 13-29, 1864),
matched on the printed name, with plate and figure number breaking ties. data/manual_names.json overrides a figure
("PLATE/FIG": {"modern_taxon", "modern_full", "family", "name_source", "name_note"}). Review columns (crop_ok,
names_checked, uploaded, commons_url, comments) survive rebuilds.
"""
import csv
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "data" / "figures.csv"
FIELDS = ["id", "band", "tafel", "figur", "page", "gender", "origin", "orig_taxon", "modern_taxon", "modern_full",
          "family", "name_source", "name_note", "author", "year", "citation", "crop_file", "commons_filename", "notes",
          "crop_ok", "names_checked", "uploaded", "commons_url", "comments"]
KEEP = ["crop_ok", "names_checked", "uploaded", "commons_url", "comments"]
PARTS = {302: (1, 12), 328: (13, 29)}  # WSC ref -> plates
YEAR = lambda plate: 1861 if plate <= 12 else 1864
FIGREF = re.compile(r"pl\. (\d+), f[.,] (\w+)")


def norm(name):
    """Printed and WSC spellings compared: no accents or ligatures, lowercase, genus + species only."""
    name = name.replace("œ", "oe").replace("Œ", "Oe").replace("æ", "ae").replace("Æ", "Ae")
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^A-Za-z ]", " ", name).lower().split()[:2])


def same_name(a, b):
    """Spelling variants count as the same name: Clerckii/clercki, livida/lividus, Walckenäera/Walckenaeria."""
    (ga, *sa), (gb, *sb) = norm(a).split(), norm(b).split()
    return ga[:6] == gb[:6] and sa[:1] and sb[:1] and sa[0][:4] == sb[0][:4]


def load_wsc():
    entries, cites = [], {}
    for ref in PARTS:
        lines = (ROOT / "data" / "wsc" / f"ref_{ref}.txt").read_text(encoding="utf-8").split("\n")
        start = next(i for i, l in enumerate(lines) if l.startswith("Taxa included"))
        cites[ref] = next(l for l in lines[start + 1:] if l.strip()).strip()
        for line in lines:
            if "\t" not in line or line.startswith("Taxon"):
                continue
            current, rest = line.split("\t", 1)
            m = re.fullmatch(r"(.+) \((\w+idae)\)", current.strip())
            rest = rest.replace(" Original description", "").strip()
            if not m or rest.split(", ")[1:2] and rest.split(", ")[1].startswith("type "):
                continue
            orig = rest.rsplit(", ", 1)[-1]
            if "type " in orig or not re.fullmatch(r"[A-Z][\w\-]+ [\w\-]+", orig):
                continue
            full = m.group(1)
            note = re.search(r"\(([^)]*)\)", rest.rsplit(", ", 1)[0])
            entries.append({"ref": ref, "full": full, "taxon": " ".join(full.split()[:2]), "family": m.group(2),
                            "orig": orig, "page": rest.split(",")[0].strip(),
                            "figs": [(int(p), f) for p, f in FIGREF.findall(rest)],
                            "note": note.group(1) if note else ""})
    return entries, cites


def match(entries, plate, fig, printed):
    """The WSC entry for a printed figure: same original name, preferring one that cites this plate and figure."""
    ref = next(r for r, (a, b) in PARTS.items() if a <= plate <= b)
    cands = [e for e in entries if norm(e["orig"]) == norm(printed)]
    here = [e for e in cands if any(p == plate and re.match(rf"{re.escape(str(fig))}([a-z\-]|$)", f) for p, f in e["figs"])]
    for group in (here, [e for e in cands if e["ref"] == ref], cands):
        if group:
            return group[0], len(group) > 1
    # spelling differs: fall back on the figure number, on this plate first (figure numbers are unique in the
    # work; a few species return on a later plate with more drawings, e.g. 102 on plates 10 and 12)
    for same_plate in (True, False):
        by_fig = [e for e in entries if any((p == plate or not same_plate) and f == str(fig) for p, f in e["figs"])]
        if by_fig:
            return by_fig[0], len(by_fig) > 1
    return None, False


def split_id(fid, figs):
    """Crop id -> (figure, letter): "1a" -> (1, "a"), "Aa" -> ("A", "a"), "111-2" -> (111, ""), "AA" -> ("AA", "")."""
    base = re.sub(r"-\d+$", "", fid)
    keys = sorted(figs, key=lambda k: -len(str(k)))
    for k in keys:
        if base == str(k):
            return k, ""
    for k in keys:
        if base.startswith(str(k)):
            return k, base[len(str(k)):]
    raise KeyError(fid)


def sex(text):
    m = re.search(r"[♀♂]|\b(fe)?male\b", text)
    return "" if not m else "f" if m.group(0) in ("♀", "female") else "m"


def order(row):
    """Plate, then figure number, then letter: 2 before 10, A before B."""
    m = re.match(r"(\d*)(.*)", row["figur"])
    return int(row["tafel"]), int(m.group(1)) if m.group(1) else 10 ** 6, m.group(2)


def main():
    entries, cites = load_wsc()
    manual = json.loads((ROOT / "data" / "manual_names.json").read_text(encoding="utf-8")) \
        if (ROOT / "data" / "manual_names.json").exists() else {}
    old = {}
    if CSV.exists():
        with CSV.open(encoding="utf-8", newline="") as f:
            old = {r["id"]: r for r in csv.DictReader(f)}
    rows, unmatched, unsure = [], set(), set()
    for gfile in sorted((ROOT / "data").glob("groups_*.json")):
        for p, groups in json.loads(gfile.read_text(encoding="utf-8")).items():
            plate = int(p)
            text = json.loads((ROOT / "data" / "text" / f"{plate:03d}.json").read_text(encoding="utf-8"))
            figs = {f["fig"]: f for f in text["figures"]}
            ids = [k for k in groups if not k.startswith("_")]
            for fid in ids:
                fig, letter = split_id(fid, figs)
                t = figs[fig]
                shows = t["drawings"].get(letter, "")
                printed = re.sub(r"\.\s.*$|\.$", "", t["name"]).strip()  # "Pompilus sepicola. F. Smith." -> name only
                ref = next(r for r, (a, b) in PARTS.items() if a <= plate <= b)
                row = {k: "" for k in FIELDS}
                stem = f"{plate:03d}_{fid}"
                row.update(id=stem, band=1 if plate <= 12 else 2, tafel=plate, figur=fid, gender=sex(shows),
                           origin=shows, orig_taxon=printed, author="Blackwall", year=YEAR(plate),
                           citation=cites[ref], crop_file=f"work/crops/{stem}.jpg",
                           commons_filename=f"Blackwall {YEAR(plate)} Spiders of Great Britain pl. {plate} fig. {fid} {printed}.jpg")
                key = f"{plate}/{fig}"
                if key in manual:
                    row.update(manual[key])
                else:
                    e, several = match(entries, plate, fig, printed)
                    if e:
                        row.update(page=e["page"], modern_taxon=e["taxon"], modern_full=e["full"], family=e["family"],
                                   name_source=f"WSC ref {e['ref']}", name_note=f"WSC: {e['note']}" if e["note"] else "")
                        if several:
                            unsure.add(key)
                            row["notes"] = "several WSC entries share this printed name; check"
                        if not same_name(e["orig"], printed):
                            row["notes"] = f"matched by figure number; WSC prints {e['orig']}"
                    else:
                        unmatched.add(f"{key} {printed}")
                for k in KEEP:
                    if stem in old:
                        row[k] = old[stem][k]
                rows.append(row)
    rows.sort(key=order)
    with CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(len(rows), "rows;", len(unmatched), "figures without a WSC name;", len(unsure), "ambiguous")
    for u in sorted(unmatched):
        print("  no WSC:", u)
    for u in sorted(unsure):
        print("  ambiguous:", u)


if __name__ == "__main__":
    main()
