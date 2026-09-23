"""Builds sportrankle.html from the spreadsheets in this folder.

Run again after editing a spreadsheet: python build.py
"""
import base64
import hashlib
import io
import json
import re
import shutil
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

import openpyxl

HERE = Path(__file__).parent
TEMPLATE = HERE / "template.html"
OUT = HERE / "sportrankle.html"
DIST = HERE / "dist" / "index.html"  # standalone page for Netlify
IMG_CACHE = HERE / "img-cache"  # downloaded + shrunk photos, so each URL is fetched once
IMG_WIDTH = 400
# Your own photos: photos/<game>/<item name>.jpg (see photos/README.txt). They are resized into img/<game>/
# and served as files next to the page, which keeps the page small and the photos sharp.
PHOTOS = HERE / "photos"
IMG_OUT = HERE / "img"
IMG_LONG = 1200

# The spreadsheets are German; the page is English. Rows and categories are
# translated through the tables below (missing entries fall back to German).
GAMES = {
    # "cover" is the picture on the home tile; games without one show their first item's photo
    "sports": {"file": "Mannschaftssportarten*.xlsx", "tab": "Team sports", "noun": "sport", "plural": "sports", "word": "SPORTS",
               "cover": "covers/sports.png"},
    "f1": {"file": "F1-Strecken*.xlsx", "tab": "F1 circuits", "noun": "circuit", "plural": "circuits", "word": "F1",
           "cover": "covers/f1.png"},
    # Names are already English; "short" says what goes on the title cards: the last word or all but the first
    "nfl": {"file": "NFL_Teams*.xlsx", "tab": "NFL teams", "noun": "team", "plural": "teams", "word": "NFL", "english": True, "short": "last",
            "cover": "covers/nfl.png"},
    "ski": {"file": "Ski_Alpin*.xlsx", "tab": "Alpine skiers", "noun": "skier", "plural": "skiers", "word": "SKI", "english": True, "short": "surname",
            "cover": "covers/ski.png"},
}

# Supabase project for daily results (public "anon" key: it can only insert rows and read aggregates).
# Without a key the page runs without the online comparison.
SUPABASE = {"url": "https://ofvilwphyyqfverzqole.supabase.co", "key": (HERE / "supabase" / "anon.key").read_text().strip()
            if (HERE / "supabase" / "anon.key").exists() else None}

# Pictures on the two game-type cards of the home page (tall subjects: cropped 2:1 around them)
KIND_COVERS = {"rankle": "covers/rankle.png", "blind": "covers/blind.png", "sort": "covers/sort.png", "ringer": "covers/ringer.png"}

NAMES_EN = {
    # Team sports
    "Fussball": "Football", "Basketball": "Basketball", "Handball": "Handball", "Volleyball": "Volleyball",
    "Beachvolleyball": "Beach volleyball", "Eishockey": "Ice hockey", "Feldhockey": "Field hockey",
    "Rugby Union": "Rugby union", "Rugby League": "Rugby league", "American Football": "American football",
    "Cricket": "Cricket", "Baseball": "Baseball", "Softball": "Softball", "Wasserball": "Water polo",
    "Unihockey": "Floorball", "Lacrosse": "Lacrosse", "Futsal": "Futsal", "Netball": "Netball",
    "Curling": "Curling", "Rollhockey": "Roller hockey",
    # F1 circuits: "Short name (Country)"; " / " marks the part shown on the title cards
    "Monza (Italien)": "Monza (Italy)", "Silverstone (Grossbritannien)": "Silverstone (Great Britain)",
    "Spa-Francorchamps (Belgien)": "Spa-Francorchamps (Belgium)", "Monaco (Monaco)": "Monaco (Monaco)",
    "Suzuka (Japan)": "Suzuka (Japan)", "Interlagos (Brasilien)": "Interlagos (Brazil)",
    "Montreal (Kanada)": "Montreal (Canada)", "Melbourne / Albert Park (Australien)": "Melbourne / Albert Park (Australia)",
    "Barcelona-Catalunya (Spanien)": "Barcelona-Catalunya (Spain)", "Hungaroring (Ungarn)": "Hungaroring (Hungary)",
    "Zandvoort (Niederlande)": "Zandvoort (Netherlands)", "Red Bull Ring (Österreich)": "Red Bull Ring (Austria)",
    "Bahrain (Bahrain)": "Bahrain (Bahrain)", "Jeddah (Saudi-Arabien)": "Jeddah (Saudi Arabia)",
    "Baku (Aserbaidschan)": "Baku (Azerbaijan)", "Singapur / Marina Bay (Singapur)": "Singapore / Marina Bay (Singapore)",
    "Austin / COTA (USA)": "Austin / COTA (USA)", "Mexiko-Stadt (Mexiko)": "Mexico City (Mexico)",
    "Las Vegas (USA)": "Las Vegas (USA)", "Abu Dhabi / Yas Marina (VAE)": "Abu Dhabi / Yas Marina (UAE)",
}

# German category -> (English name, unit shown)
CATS_EN = {
    "Aktive pro Team auf dem Feld": ("Players on the field", "players"),
    "Spielfeldfläche": ("Playing area", "m²"),
    "Spielfeldlänge": ("Field length", "m"),
    "Spielabschnitte": ("Game periods", "periods"),
    "Schiedsrichter im Spiel": ("Referees on the field", "officials"),
    "Punkte für den höchsten Einzeltreffer": ("Highest single score", "pts"),
    "Gewicht Spielgerät": ("Ball / puck / stone weight", "g"),
    "Durchmesser / Länge Spielgerät": ("Ball size", "cm"),
    "Höhe Tor / Korb / Netz": ("Goal / hoop / net height", "cm"),
    "Entstehungsjahr (moderne Regeln)": ("Modern rules codified", ""),
    "Gründungsjahr Weltverband": ("World federation founded", ""),
    "Mitgliedsverbände Weltverband": ("Member federations", "nations"),
    "Erste Herren-WM": ("First men's World Cup", ""),
    "Erste Frauen-WM": ("First women's World Cup", ""),
    "Teams an der letzten WM (Herren)": ("Teams at last men's World Cup", "teams"),
    "Streckenlänge": ("Track length", "km"),
    "Kurven": ("Corners", "corners"),
    "Rennrunden": ("Race laps", "laps"),
    "Renndistanz": ("Race distance", "km"),
    "Kurven pro km": ("Corners per km", "per km"),
    "Erster F1-Grand-Prix": ("First F1 Grand Prix", ""),
    "Ausgetragene F1-GPs": ("F1 Grands Prix held", "races"),
    "Rundenrekord": ("Race lap record", ""),
    "Eröffnungsjahr der Strecke": ("Circuit opened", ""),
    "Höhe über Meer": ("Altitude", "m"),
    "Höhenunterschied": ("Elevation change", "m"),
    "Zuschauer Rennwochenende": ("Race weekend attendance", "fans"),
    "Längste Gerade": ("Longest straight", "m"),
    "DRS-Zonen (Stand 2025)": ("DRS zones (2025)", "zones"),
    "Breitengrad": ("Latitude", ""),
    # NFL teams
    "Siege (Regular Season, all-time)": ("Regular-season wins, all time", "wins"),
    "Niederlagen (Regular Season, all-time)": ("Regular-season losses, all time", "losses"),
    "Unentschieden (all-time)": ("Ties, all time", "ties"),
    "Siegquote (Regular Season, all-time)": ("Regular-season win rate", ""),
    "Playoff-Siege (all-time)": ("Playoff wins, all time", "wins"),
    "Hall-of-Famers": ("Hall of Famers", "people"),
    "In der heutigen Stadt seit": ("In current city since", ""),
    "Stadionkapazität": ("Stadium capacity", "seats"),
    "Stadion-Baukosten": ("Stadium construction cost", "M USD"),
    "Breitengrad Stadion": ("Stadium latitude", ""),
    "Längengrad Stadion": ("Stadium longitude", ""),
    "Einwohner Metropolregion": ("Metro area population", "million"),
    "Social-Media-Follower": ("Social media followers", "million"),
    "YouTube-Abonnenten": ("YouTube subscribers", "thousand"),
    "Betriebsgewinn Saison 2025": ("Operating profit 2025", "M USD"),
    # Alpine skiers
    "Geburtsdatum (Alter)": ("Date of birth", ""),
    "Weltcup-Debüt": ("World Cup debut", ""),
    "Alter beim Weltcup-Debüt": ("Age at World Cup debut", "years"),
    "Weltcup-Saisons": ("World Cup seasons", "seasons"),
    "Weltcup-Siege Karriere": ("World Cup wins", "wins"),
    "Weltcup-Podestplätze Karriere": ("World Cup podiums", "podiums"),
    "Podeste ohne Sieg (2. + 3. Plätze)": ("Podiums without a win", "podiums"),
    "Siegquote auf dem Podest": ("Wins per podium", ""),
    "Podeste pro Saison": ("Podiums per season", "podiums"),
    "Weltcup-Siege Saison 2025/26": ("World Cup wins 2025/26", "wins"),
    "Siege pro Saison": ("Wins per season", "wins"),
    "Olympia-Medaillen Karriere": ("Olympic medals", "medals"),
    "Medaillen Olympia + WM gesamt": ("Olympic + World Champs medals", "medals"),
    "Olympia-Teilnahmen": ("Olympic Games", "Games"),
    "WM-Medaillen Karriere": ("World Championship medals", "medals"),
}

# German "Rang 1 =" direction -> English
DIR_EN = {"meiste": "most", "grösste": "largest", "grösster": "largest", "längste": "longest", "schwerste": "heaviest",
          "höchste": "highest", "ältestes": "oldest", "älteste": "oldest", "frühestes": "earliest", "früheste": "earliest",
          "schnellste": "fastest", "nördlichste": "northernmost", "nördlichstes": "northernmost", "westlichstes": "westernmost",
          "kürzeste": "shortest", "kleinste": "smallest", "leichteste": "lightest", "südlichste": "southernmost",
          "tiefste": "lowest", "wenigste": "fewest", "am längsten": "earliest", "am längsten dabei": "earliest",
          "jüngste/r": "youngest", "jüngste/r Debütant/in": "youngest"}

# "Rang 1 =" directions where the smallest value wins. "am längsten (dabei)" ranks a year or date, so the
# earliest wins; "jüngste/r" on a birth date means the latest date wins, on an age the smallest number.
LOW_FIRST = {"ältestes", "älteste", "frühestes", "früheste", "schnellste", "kürzeste", "kleinste", "leichteste", "südlichste", "tiefste", "wenigste",
             "am längsten", "am längsten dabei", "jüngste/r Debütant/in"}

# Spreadsheet unit -> (unit shown, value format)
UNIT_FMT = {"Anzahl": ("", ""), "Jahr": ("", "year"), "Sekunden": ("", "laptime"), "Grad": ("", "lat"),
            "° Nord": ("", "lat"), "° West": ("", "lon"), "%": ("", "pct"), "Datum": ("", "date"),
            "Jahre": ("years", "dec1"), "Ø Podeste": ("podiums", "dec1"), "Ø Siege": ("wins", "dec1")}


def photo(url):
    """Download an image once, shrink it and return it as a data URI (works offline and in previews)."""
    from PIL import Image

    IMG_CACHE.mkdir(exist_ok=True)
    cached = IMG_CACHE / (hashlib.sha1(url.encode()).hexdigest()[:16] + ".jpg")
    if not cached.exists():
        # Wikimedia asks for an identifying user agent and throttles bursts, so go slowly and retry.
        req = urllib.request.Request(url, headers={"User-Agent": "SportrankleBuild/1.0 (https://sportrankle.netlify.app) python-urllib"})
        for attempt in range(5):
            time.sleep(2 + attempt * 8)
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = resp.read()
                break
            except urllib.error.HTTPError as e:
                if e.code != 429 or attempt == 4:
                    raise
        img = Image.open(io.BytesIO(data)).convert("RGB")
        img.thumbnail((IMG_WIDTH, IMG_WIDTH))
        img.save(cached, "JPEG", quality=76, optimize=True, progressive=True)
    return "data:image/jpeg;base64," + base64.b64encode(cached.read_bytes()).decode()


def cover(pattern, ratio=1.5, width=0.6, cy=0.53, size=800):
    """Tile picture from a local file, as a data URI: the middle `width` share of the image, cropped to
    `ratio` (w:h) around the vertical centre `cy`, shrunk to `size` px."""
    from PIL import Image

    path = next(HERE.glob(pattern))
    IMG_CACHE.mkdir(exist_ok=True)
    cached = IMG_CACHE / f"cover-{path.stem}-{path.stat().st_mtime_ns}-{ratio}-{width}-{cy}-{size}.jpg"
    if not cached.exists():
        img = Image.open(path).convert("RGB")
        w, h = img.size
        cw = round(w * width); ch = min(h, round(cw / ratio))
        x0, y0 = (w - cw) // 2, max(0, min(h - ch, round(h * cy - ch / 2)))
        img = img.crop((x0, y0, x0 + cw, y0 + ch))
        img.thumbnail((size, size))
        img.save(cached, "JPEG", quality=80, optimize=True, progressive=True)
    return "data:image/jpeg;base64," + base64.b64encode(cached.read_bytes()).decode()


def norm(s):
    """Lower-case letters and digits only, accents stripped: 'Loïc Meillard' -> 'loicmeillard'."""
    return re.sub(r"[^a-z0-9]+", "", unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower())


def local_photos(key):
    """Resize photos/<key>/*.jpg|png|webp into img/<key>/ and return {normalised file stem: {img, credit?}}."""
    from PIL import Image

    folder = PHOTOS / key
    if not folder.is_dir():
        return {}
    credits = {}
    if (folder / "credits.txt").exists():
        for line in (folder / "credits.txt").read_text(encoding="utf-8").splitlines():
            if "=" in line:
                name, url = line.split("=", 1)
                credits[norm(Path(name.strip()).stem)] = url.strip()
    out = {}
    for f in sorted(folder.iterdir()):
        if f.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
            continue
        stem = norm(f.stem)
        target = IMG_OUT / key / f"{stem}.jpg"
        if not target.exists() or target.stat().st_mtime < f.stat().st_mtime:
            target.parent.mkdir(parents=True, exist_ok=True)
            img = Image.open(f).convert("RGB")
            img.thumbnail((IMG_LONG, IMG_LONG))
            img.save(target, "JPEG", quality=82, optimize=True, progressive=True)
        # Own pictures are shown whole, on a background in the picture's own edge colour
        img = Image.open(target).convert("RGB")
        w, h = img.size
        edge = [img.getpixel((x, y)) for x in range(0, w, 8) for y in (0, h - 1)] + [img.getpixel((x, y)) for y in range(0, h, 8) for x in (0, w - 1)]
        bg = "#%02x%02x%02x" % tuple(sum(c[i] for c in edge) // len(edge) for i in range(3))
        out[stem] = {"img": f"img/{key}/{target.name}", "fit": "contain", "bg": bg,
                     **({"credit": credits[stem]} if stem in credits else {})}
    return out


def load_game(key, cfg):
    path = next(HERE.glob(cfg["file"]))
    wb = openpyxl.load_workbook(path, data_only=True)
    values_ws, _, cats_ws = wb.worksheets[:3]

    cats = []
    for row in cats_ws.iter_rows(min_row=2, values_only=True):
        if isinstance(row[0], int):
            unit, fmt = UNIT_FMT.get(row[2], (row[2], ""))
            name, unit = CATS_EN.get(row[1], (row[1], unit))
            if row[1] not in CATS_EN:
                print(f"  No English name for category '{row[1]}', using German")
            cats.append({"name": name, "unit": unit, "fmt": fmt, "dir": row[3]})
    n_cat = len(cats)

    header = [c.value for c in values_ws[1]]
    img_col = header.index("Bild-URL") if "Bild-URL" in header else None
    src_col = next((i for i, h in enumerate(header) if h and str(h).startswith("Bildquelle")), None)

    values, images = {}, {}
    for row in values_ws.iter_rows(min_row=2, values_only=True):
        if row[0]:
            values[row[0]] = list(row[1 : 1 + n_cat])
            if img_col is not None and row[img_col]:
                try:
                    images[row[0]] = {"img": photo(row[img_col]),
                                      "credit": row[src_col] if src_col is not None else row[img_col]}
                except Exception as e:  # a broken link should not stop the build
                    print(f"  No image for {row[0]}: {e}")

    # Ranks are computed from the values (the formula sheet may be saved without
    # cached results). Tied values share a rank, empty cells get none.
    names = list(values)
    ranks = {n: [None] * n_cat for n in names}
    for i, cat in enumerate(cats):
        low_first = cat["dir"] in LOW_FIRST
        vals = [values[n][i] for n in names if isinstance(values[n][i], (int, float, datetime))]
        for n in names:
            v = values[n][i]
            if isinstance(v, (int, float, datetime)):
                ranks[n][i] = 1 + sum(1 for w in vals if (w < v if low_first else w > v))
    # Dates go to the page as ISO strings
    for n in names:
        values[n] = [v.strftime("%Y-%m-%d") if isinstance(v, datetime) else v for v in values[n]]

    for n in names:
        if n not in NAMES_EN and not cfg.get("english"):
            print(f"  No English name for '{n}', using German")
    for cat in cats:
        cat["dir"] = DIR_EN.get(cat["dir"], cat["dir"])
    items = [{"name": NAMES_EN.get(n, n), "ranks": ranks[n], "values": values[n], **images.get(n, {})} for n in names]
    if cfg.get("short"):
        for it in items:
            words = it["name"].split()
            it["short"] = words[-1] if cfg["short"] == "last" else " ".join(words[1:])

    # Own photos beat spreadsheet URLs. A file matches the German or English name, the name without
    # its bracket, any " / " part of it, or the short name: Monaco.jpg fits "Monaco (Monaco)".
    own = local_photos(key)
    used = set()
    for n, it in zip(names, items):
        title = it["name"].split(" (")[0]
        for cand in [n, it["name"], title, *title.split(" / "), it.get("short", "")]:
            if cand and norm(cand) in own:
                it.update(own[norm(cand)])
                used.add(norm(cand))
                break
    for stem in own:
        if stem not in used:
            print(f"  photos/{key}: '{stem}' matches no {cfg['noun']}")
    return {**{k: v for k, v in cfg.items() if k not in ("file", "english", "short", "cover")}, "source": path.name,
            **({"cover": cover(cfg["cover"])} if cfg.get("cover") else {}),
            "items": items, "cats": cats}


def main():
    data = {key: load_game(key, cfg) for key, cfg in GAMES.items()}
    for key, g in data.items():
        if len(g["items"]) < 8 or any(all(it["ranks"][i] is None for it in g["items"]) for i in range(len(g["cats"]))):
            raise SystemExit(f"{g['source']}: fewer than 8 rows or a category without values, build stopped.")
    # A game without a picture yet gets its name as cards on the home page
    kinds = {k: cover(f, ratio=2, width=0.8, cy=0.52, size=1000) for k, f in KIND_COVERS.items() if next(HERE.glob(f), None)}
    html = (TEMPLATE.read_text(encoding="utf-8")
            .replace("__DATA__", json.dumps(data, ensure_ascii=False))
            .replace("__KINDS__", json.dumps(kinds))
            .replace("__SUPABASE__", json.dumps(SUPABASE if SUPABASE["key"] else None)))
    OUT.write_text(html, encoding="utf-8")
    DIST.parent.mkdir(exist_ok=True)
    DIST.write_text(
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        f"{html}\n</html>\n", encoding="utf-8")
    if IMG_OUT.is_dir():
        shutil.copytree(IMG_OUT, DIST.parent / "img", dirs_exist_ok=True)
    for key, g in data.items():
        own = sum(1 for it in g["items"] if it.get("img", "").startswith("img/"))
        pics = sum(1 for it in g["items"] if "img" in it)
        print(f"{key}: {len(g['items'])} items, {len(g['cats'])} categories, {pics} images ({own} own photos) from {g['source']}")


if __name__ == "__main__":
    main()
