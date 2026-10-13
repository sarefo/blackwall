# Blackwall, *A History of the Spiders of Great Britain and Ireland* (1861–64)

Cut every lettered drawing out of the 29 hand-colored plates, as was done for
*Die Arachniden* in `C:\dev\koch`. Nobody had cut individual figures before (Commons has
only the whole plates, uploaded by Notafly, plus the 2025 crop `Oonops pulcher Blackwall.jpg`).

## Source

Internet Archive `historyspidersg00blac` (Harvard MCZ, 300 ppi, clean paper). The plates are
bound together at the back: plate P is leaf n(398+2P) and its "Description of Plate" page is
leaf n(397+2P). Plates I–XII belong to vol. 1 (1861), XIII–XXIX to vol. 2 (1864).

## Figure scheme

Blackwall gives one number per species (1–272, running through both volumes) and a letter per
drawing: usually a = ♀, b = ♂, then c, d, … for palps, eyes, mouthparts, spinners. One crop
per lettered drawing; crop id = plate + figure + letter, e.g. `work/crops/001_1a.jpg`.
Unlettered figures have no letter (`003_10`); a second drawing under one label gets `-2`
(`021_226e-2`). Fig. 270 (*Segestria senoculata*) runs over plates XXVIII and XXIX with its own
a–e on each, so names on Commons must carry the plate number.

## Layout

```
plates/PPP.jpg          plate scans                                   [not in git]
work/desc/PPP.jpg       description pages                             [not in git]
data/text/PPP.json      figures, printed names, and what each letter shows, read from the description page
data/groups_PPP.json    components per drawing (_split, _box, _drop as in the Koch README)
data/segment.json       segmentation settings (less dilation than Koch: figures nearly touch)
data/crop.json          crop settings (edge shading only from the crop edge)
data/tight/             tight-crop masks (white = erase)
work/crops, work/tight  wide and tight crops                          [not in git]
```

## Pipeline

The image scripts are shared with the Koch project and pointed here with an environment variable:

```
export PLATE_PROJECT='C:\dev\blackwall'
PY=/c/dev/koch/.venv/Scripts/python.exe
$PY -I /c/dev/koch/scripts/segment.py 1 2 ...     # work/seg/PPP_overlay.jpg
$PY -I scripts/zoom.py P X0 Y0 X1 Y1              # full-res region with component ids (overlay px)
$PY -I /c/dev/koch/scripts/crop.py 1 2 ...        # work/crops
$PY -I scripts/sheet.py P                         # work/sheets/PPP.jpg contact sheet
$PY -I /c/dev/koch/scripts/tight.py auto 1 2 ...  # work/tight + data/tight masks
$PY -I /c/dev/koch/scripts/tight.py sketches 4 5 ...  # uncolored drawings into data/gallery_skip.json
$PY -I /c/dev/koch/scripts/wsc_included.py 302 328   # data/wsc: WSC "taxa included" for Part I and Part II
$PY -I scripts/build_table.py                     # data/figures.csv
```

`build_table.py` writes `data/figures.csv` in the Koch schema: one row per crop, the printed name from
the description page, the current name from WSC (ref 302 = Part I, plates 1-12, 1861; ref 328 = Part II,
plates 13-29, 1864). It matches on the printed name, then on the figure number when the spelling differs
(the `notes` column says so where WSC prints a different name). `data/manual_names.json` holds the names
WSC does not list (from GBIF) and the three insects on plate XII. Review columns survive rebuilds.

## Review

`review.cmd` starts the shared review app (`C:\dev\koch\scripts\review_app.py`) on
http://localhost:8778 with `PLATE_PROJECT` set to this folder; `data/project.json` sets its labels.
Ticks and comments go into `data/figures.csv`; the wide and tight editors write `data/wide`,
`data/tight` and `data/crop_fixes.json` here, as in the Koch project.

Pale line drawings (palps, eyes) are cut with `_box`, because they fall apart into many small
components and partly stay below the ink threshold. A box paints out nothing, so faint
neighbor lines, leader dashes and printed labels can remain; the tight masks remove some,
the rest needs hand cleanup.

## Status (2026-10-13)

All 29 plates cut: 1094 wide crops and tight crops, every figure named (WSC, or GBIF for four names WSC does
not list). The 497 gallery crops are reviewed, plus 16 ticked line drawings; names are checked.
513 tight crops are on Commons (uploaded 2026-10-13 with `scripts/commons.py`), and each plate page links its
crops with `{{Image extracted}}`. The other 581 crops (mostly uncolored palps, eyes and mouthparts, left out of
the gallery) are not reviewed and not uploaded.

## Commons

`scripts/commons.py` (run with the Koch venv; the bot password lives in `C:\dev\koch`):

```
commons.py lookup          taxon categories and Wikidata items into data/commons_cache.json
commons.py names           commons_filename in data/figures.csv
commons.py pages           description pages into work/pages
commons.py upload [--go]   dry run unless --go; needs crop_ok and names_checked; uploads the tight crop
commons.py plates [--go]   {{Image extracted}} lines on the plate pages
```

File name: `Blackwall 1861 A history of the spiders of Great Britain and Ireland pl. I fig. 1a Atypus sulzeri.jpg`
(year of the volume, plate in Roman numerals, epithets lowercase). License `{{PD-old-100-expired}}`; structured
data: depicts, creator (Q661407), inception, copyright status.

## Gallery

https://blackwall.kimbaro.com shows the gallery crops (colored drawings, 497) arranged by family, with a key and
a card per figure. It is built by the shared `C:\dev\koch\scripts\poster.py` (`build-site.cmd`; settings in
`data/site.json`, text in `data/about.html`, Commons plate files in `data/plate_files.json`) into `site/` (not in git)
and deployed with `npx wrangler deploy` (`wrangler.jsonc`). Subfamilies come from `data/genus_ranks.json`
(`C:\dev\koch\scripts\subfamilies.py` with `PLATE_PROJECT` set). Gallery membership is `data/gallery_skip.json`
(the review app's "Sketches only" view, key `s`, lists what is left out).

## Plate and description disagree (check in review)

- Pl. III: figs 2–17 are palps only (the spiders are on plates I–II); ids "2".."17", plus 10a.
- Pl. VI fig. 70: plate labels the spider "a" and the palp "b"; description "♂; a, palpal organs". Cut as `70` and `70a`.
- Pl. IX fig. 88: plate a–h, description a–i (g palp in profile has no drawing). Hind leg `88h`, calamistrum `88i`, no `88g`.
- Pl. X fig. 99: plate a–d, description a–e. Cut `99c` (palp) and `99e` (drawing printed d); no `99d`. Fig. 104 palp printed "c", cut as `104a`.
- Pl. XI: two hairs near label 24, `24k` and `24k-2`, possibly swapped.
- Pl. XII: plate prints "102e" on two cocoons not in the description; right one cut as `102e`, left one is inside `102d`. Insects AA/BB/CC; caption says "Hemiteles", description "Hemeteles".
- Pl. XIII: `111` and `111-2` (two unlettered drawings); `111l-2` is a pale leaf outline that may not be a figure.
- Pl. XV: the drawing printed "e" with a leader to 137 is filed as `137d`; 138e (falx of ♂) not found.
- Pl. XVIII: unlettered fig. A cut as `A` and `A-2`. Palps printed "d"/"e" near 182 assigned to 184.
- Pl. XX: extra drawings `207c-2` (front view) and `208b-2` (profile, no label).
- Pl. XXI: `223b-2` (unlettered front view), `226e-2` (two drawings printed "e"); leaders of 216/217 and 224/225 cross.
- Pl. XXII: unnumbered figures A–E cut as `Aa`..`Ec`; 231 lower drawings as `231e`, `231f`.
- Pl. XXIII: `236l-2`; `237g-2` is an extra palp printed "g", `237g` the natural-size spider.
- Pl. XXIV fig. 243: natural-size spiders marked A/b and B/c cut as `243b`, `243c`.
- Pl. XXV: `249e` is an unlettered natural-size spider.
- Pl. XXVI fig. 254: described as one figure, plate has five drawings, cut as `254a`–`254f` (text JSON rewritten).
- Pl. XXVIII: 268d/e swapped between plate and description (crops follow the plate); extra `266h` and `269e`.
- Pl. XXIX: a natural-size spider next to 271a has no letter and is not cut.

## Known crop defects

- Pl. VI `63d` (stone with cocoons) is truncated: `strip_edges` takes the blue-gray stone for scan surround.
- Leg tips of neighbors: `89a`, `109d`, `133c`, `124a`, `25_246b`, `250a`; `18d` has foot tips of fig. 20.
- Caption or title text at crop edges: `1a`, `8b`, `105a`, `107b`, `140b`, `143b`, `145b`, `195b`, `235a/b`, `238b`, `251b`, `262d`.
