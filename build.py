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
PHOTO_RATIO = 1.6   # own photos taller than this (w:h) are cropped to a centred band of this ratio

# The spreadsheets are German; the page is English. Rows and categories are
# translated through the tables below (missing entries fall back to German).
# The home page goes game -> sport -> pool. Every pool names its "sport" (a key of SPORTS below).
# The order of every sport list (home page, menu, game pages, site map); "All sports" always comes first
SPORTS = {
    "mixed": {"name": "All sports", "cover": "covers/sport-mixed.png"},
    "soccer": {"name": "Football", "cover": "covers/sport-soccer.png"},
    "football": {"name": "American football", "cover": "covers/sport-football.png"},
    "motorsport": {"name": "Motorsport", "cover": "covers/sport-motorsport.png"},
    "winter": {"name": "Winter sports", "cover": "covers/sport-winter.png"},
}

GAMES = {
    # "cover" is the picture on the home tile; games without one show their first item's photo
    "sports": {"file": "Mannschaftssportarten*.xlsx", "tab": "Team sports", "noun": "sport", "plural": "sports", "word": "SPORTS",
               "sport": "mixed", "cover": "covers/sports.png"},
    "f1": {"file": "F1-Strecken*.xlsx", "tab": "F1 circuits", "noun": "circuit", "plural": "circuits", "word": "F1",
           "sport": "motorsport", "cover": "covers/f1.png"},
    # Names are already English; "short" says what goes on the title board: the last word or all but the first.
    # "sub" names helper columns whose values go in brackets after the name (shown under the title board).
    "nfl": {"file": "NFL_Teams*.xlsx", "tab": "NFL teams", "noun": "team", "plural": "teams", "word": "NFL", "english": True, "short": "last",
            "sport": "football", "cover": {"file": "covers/nfl.png", "width": 0.75, "cy": 0.5}, "sub": ["HILFSSPALTE: Division 2026"]},
    "nflplayers": {"file": "NFL_Spieler*.xlsx", "tab": "NFL players", "noun": "player", "plural": "players", "word": "NFL", "english": True, "short": "surname",
                   "sport": "football", "cover": {"file": "covers/nflplayers.png", "width": 0.75, "cy": 0.5}, "sub": ["HILFSSPALTE: Team (Sept. 2026)", "HILFSSPALTE: Position"]},
    "nflhof": {"file": "NFL_HallOfFame*.xlsx", "tab": "NFL Hall of Fame", "noun": "legend", "plural": "legends", "word": "HOF", "english": True, "short": "surname",
               "sport": "football", "cover": {"file": "covers/nflhof.png", "width": 0.75, "cy": 0.5}, "sub": ["HILFSSPALTE: Position"]},
    "college": {"file": "CollegeFootball*.xlsx", "tab": "College football", "noun": "program", "plural": "programs", "word": "NCAA", "english": True,
                "sport": "football", "cover": {"file": "covers/college.png", "width": 0.75, "cy": 0.5}, "sub": ["HILFSSPALTE: Uni-Stadt"]},
    "ski": {"file": "Ski_Alpin*.xlsx", "tab": "Alpine skiers", "noun": "skier", "plural": "skiers", "word": "SKI", "english": True, "short": "surname",
            "sport": "winter", "cover": "covers/ski.png"},
    # "wide" format: one sheet, one row per player, value and rank columns side by side (ranks are recomputed).
    # "cats" maps the value columns to use -> (English name, unit, format, "Rank 1 =" direction);
    # "sub" columns go in brackets after the name and appear under the title; "filter" keeps matching rows only.
    "cl": {"file": "CL_Players*.xlsx", "tab": "Champions League players", "noun": "player", "plural": "players", "word": "CL",
           "english": True, "short": "surname", "sport": "soccer", "cover": {"file": "covers/cl.png", "width": 0.8, "cy": 0.46},
           "format": "wide", "name_col": "Player", "sub": ["Club", "Nationality"], "filter": ("Top 101 by MV", "yes"),
           "cats": {
               "Market value (€)": ("Market value", "M €", "mio", "highest"),
               "Highest market value (€)": ("Peak market value", "M €", "mio", "highest"),
               "Height (cm)": ("Height", "cm", "", "tallest"),
               "Age (1.9.2026)": ("Age", "years", "dec1", "oldest"),
               "Shirt number": ("Shirt number", "", "", "highest"),
               "Intl caps": ("International caps", "caps", "", "most"),
               "Intl goals": ("International goals", "goals", "", "most"),
               "Club apps": ("Club appearances since 2012/13", "games", "", "most"),
               "Club goals": ("Club goals since 2012/13", "goals", "", "most"),
               "Club assists": ("Club assists since 2012/13", "assists", "", "most"),
               "Club minutes": ("Club minutes since 2012/13", "min", "", "most"),
               "CL apps": ("Champions League appearances", "games", "", "most"),
               "CL goals": ("Champions League goals", "goals", "", "most"),
               "Highest transfer fee (€)": ("Record transfer fee", "M €", "mio", "highest"),
               "Total transfer fees (€)": ("Transfer fees, all careers", "M €", "mio", "highest"),
               "Senior clubs": ("Senior clubs", "clubs", "", "most"),
               "G+A 2025/26": ("Goals + assists 2025/26", "", "", "most"),
           }},
}
GAMES["athletes"] = {
    # The flagship: Rankle only ("kinds"), shown as the big card on top of the home page ("flagship")
    "file": "Sportrankle_Top150*.xlsx", "tab": "Top 150 athletes", "noun": "athlete", "plural": "athletes", "word": "TOP 150",
    "english": True, "short": "surname", "sport": "mixed", "kinds": ["rankle"], "flagship": True,
    "cover": {"file": "covers/athletes.png", "ratio": 1, "width": 1.0, "cy": 0.5, "bg": "#282c50"},   # whole square, shown on its own navy
    "format": "wide", "name_col": "Athlete", "sub": ["Sport", "Nationality"],
    "cats": {
        "Age (1.9.2026)": ("Age", "years", "dec1", "oldest"),
        "Height (cm)": ("Height", "cm", "", "tallest"),
        "Weight (kg)": ("Weight", "kg", "", "heaviest"),
        "Pro debut (year)": ("Pro debut", "", "year", "earliest"),
        "Age at pro debut": ("Age at pro debut", "years", "", "youngest"),
        "Years as pro": ("Years as a pro", "years", "", "most"),
        "Olympic Games participations": ("Olympic Games", "Games", "", "most"),
        "Olympic medals": ("Olympic medals", "medals", "", "most"),
        "Olympic golds": ("Olympic golds", "golds", "", "most"),
        "Top-tier titles": ("Top-tier titles", "titles", "", "most"),
        "First top-tier title (year)": ("First top-tier title", "", "year", "earliest"),
        "Age at first top-tier title": ("Age at first top-tier title", "years", "", "oldest"),
        "Career earnings (USD m)": ("Career earnings", "M USD", "", "highest"),
        "Net worth (USD m)": ("Net worth", "M USD", "", "highest"),
        "Instagram followers (m)": ("Instagram followers", "million", "", "most"),
        "Children": ("Children", "children", "", "most"),
        "Laureus awards": ("Laureus awards", "awards", "", "most"),
    }}
# Title-board names that the surname rule gets wrong
SHORT_NAMES = {"Vinicius Junior": "Vinicius", "Vinícius Júnior": "Vinícius", "Cristiano Ronaldo": "Cristiano", "Ronaldo Nazário": "Ronaldo",
               "Son Heung-min": "Son", "Yao Ming": "Yao Ming", "Magic Johnson": "Magic", "Canelo Álvarez": "Canelo"}
# "Rank 1 =" directions in the wide format where the smallest value wins
WIDE_LOW = {"lowest", "youngest", "fewest", "earliest", "shortest", "smallest", "lightest"}

# Supabase project for daily results (public "anon" key: it can only insert rows and read aggregates).
# Without a key the page runs without the online comparison.
SUPABASE = {"url": "https://ofvilwphyyqfverzqole.supabase.co", "key": (HERE / "supabase" / "anon.key").read_text().strip()
            if (HERE / "supabase" / "anon.key").exists() else None}

# Pictures on the two game-type cards of the home page (tall subjects: cropped 2:1 around them)
# Home page pictures per game type; a dict entry overrides the crop (see cover())
KIND_COVERS = {"rankle": "covers/rankle.png", "blind": "covers/blind.png", "sort": "covers/sort.png",
               "ringer": {"file": "covers/ringer.png", "width": 1.0, "cy": 0.45}}

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
    "Am heutigen Standort seit": ("In current city since", ""),
    "Jahre ohne Meistertitel": ("Years without a title", "years"),
    "Playoff-Siege all-time": ("Playoff wins, all time", "wins"),
    "Siegquote Regular Season all-time": ("Regular-season win rate", ""),
    "Stadion eröffnet": ("Stadium opened", ""),
    "Reisekilometer zu den Divisionsgegnern": ("Travel to division rivals", "km"),
    "Punkte erzielt Regular Season 2025": ("Points scored 2025", "pts"),
    "Besitzerfamilie seit": ("Owner family since", ""),
    "Erster Pick im Draft 2026": ("First pick, 2026 draft", "overall"),
    # NFL players and Hall of Fame
    "Geburtsdatum": ("Date of birth", ""),
    "Grösse": ("Height", "cm"),
    "Gewicht": ("Weight", "kg"),
    "Draft-Jahr": ("Draft year", ""),
    "Draft-Position": ("Draft position", "overall"),
    "Alter beim NFL-Debüt": ("Age at NFL debut", "years"),
    "Playoff-Spiele Karriere": ("Playoff games", "games"),
    "Saisons im aktuellen Team": ("Seasons with current team", "seasons"),
    "Pro-Bowl-Nominierungen": ("Pro Bowl selections", ""),
    "First-Team All-Pro": ("First-team All-Pro", ""),
    "Super-Bowl-Teilnahmen": ("Super Bowl appearances", ""),
    "Rückennummer": ("Jersey number", ""),
    "Ø Jahresgehalt aktueller Vertrag": ("Average salary, current deal", "M USD"),
    "Vertrag läuft bis": ("Contract runs until", ""),
    "Einwohner Geburtsort": ("Population of birthplace", "thousand"),
    "HOF-Aufnahmejahr": ("Hall of Fame induction", ""),
    "Spiele Regular Season": ("Regular-season games", "games"),
    "Anzahl NFL-Teams": ("NFL teams played for", "teams"),
    "Meistertitel (NFL/Super Bowl)": ("Championships", "titles"),
    "Alter bei HOF-Aufnahme": ("Age at induction", "years"),
    "Alter beim letzten Spiel": ("Age at last game", "years"),
    # College football
    "Universität gegründet": ("University founded", ""),
    "Siege all-time": ("Wins, all time", "wins"),
    "Siegquote all-time": ("Win rate, all time", ""),
    "Jahre seit letztem AP-Nationaltitel": ("Years since last AP title", "years"),
    "AP-Nationaltitel": ("AP national titles", "titles"),
    "Heisman-Sieger": ("Heisman winners", ""),
    "Bowl-Siege all-time": ("Bowl wins, all time", "wins"),
    "CFP-Teilnahmen": ("Playoff appearances", ""),
    "Siege Saison 2025": ("Wins in 2025", "wins"),
    "Studierende": ("Students", "thousand"),
    "Einwohner Uni-Stadt": ("Population of college town", "thousand"),
    "NFL-Draft-Picks 2026": ("2026 NFL draft picks", "players"),
    "Unentschieden all-time": ("Ties, all time", "ties"),
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
          "jüngste/r": "youngest", "jüngste/r Debütant/in": "youngest",
          # NFL and college sheets
          "am längsten (ältestes Jahr)": "longest", "längste Durststrecke": "longest", "höchster": "highest", "höchstes": "highest",
          "ältestes Stadion": "oldest", "grösstes": "largest", "teuerstes": "most expensive", "meiste Kilometer": "most",
          "frühester Pick": "earliest pick", "frühester Pick (Nr. 1)": "earliest pick", "ältester": "oldest", "grösster": "tallest",
          "schwerster": "heaviest", "frühestes (dienstältester)": "earliest", "jüngstes Debüt": "youngest", "kleinste Nummer": "lowest",
          "längste Bindung": "latest", "grösste Stadt": "largest", "neueste Aufnahme": "most recent", "meiste Teams": "most",
          "jüngste Aufnahme": "youngest", "ältester beim Rücktritt": "oldest", "älteste Uni": "oldest"}

# "Rang 1 =" directions where the smallest value wins. "am längsten (dabei)" ranks a year or date, so the
# earliest wins; "jüngste/r" on a birth date means the latest date wins, on an age the smallest number.
LOW_FIRST = {"ältestes", "älteste", "frühestes", "früheste", "schnellste", "kürzeste", "kleinste", "leichteste", "südlichste", "tiefste", "wenigste",
             "am längsten", "am längsten dabei", "jüngste/r Debütant/in",
             "am längsten (ältestes Jahr)", "ältestes Stadion", "frühester Pick", "frühester Pick (Nr. 1)", "ältester",
             "frühestes (dienstältester)", "jüngstes Debüt", "kleinste Nummer", "jüngste Aufnahme", "älteste Uni"}

# Spreadsheet unit -> (unit shown, value format)
UNIT_FMT = {"Anzahl": ("", ""), "Jahr": ("", "year"), "Sekunden": ("", "laptime"), "Grad": ("", "lat"),
            "° Nord": ("", "lat"), "° West": ("", "lon"), "%": ("", "pct"), "Datum": ("", "date"),
            "Jahre": ("years", ""), "Saison": ("", "year"), "Ø Podeste": ("podiums", "dec1"), "Ø Siege": ("wins", "dec1")}


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
    """Tile picture from a local file, as a file under img/covers/: the middle `width` share of the image,
    cropped to `ratio` (w:h) around the vertical centre `cy`, shrunk to `size` px. Returns its page path."""
    from PIL import Image

    path = next(HERE.glob(pattern))
    out_dir = IMG_OUT / "covers"
    out_dir.mkdir(parents=True, exist_ok=True)
    tag = hashlib.sha1(f"{path.stat().st_mtime_ns}-{ratio}-{width}-{cy}-{size}".encode()).hexdigest()[:8]
    target = out_dir / f"{path.stem}-{tag}.jpg"
    if not target.exists():
        for stale in out_dir.glob(f"{path.stem}-*.jpg"):
            stale.unlink()
        img = Image.open(path).convert("RGB")
        w, h = img.size
        cw = round(w * width); ch = min(h, round(cw / ratio))
        x0, y0 = (w - cw) // 2, max(0, min(h - ch, round(h * cy - ch / 2)))
        img = img.crop((x0, y0, x0 + cw, y0 + ch))
        img.thumbnail((size, size))
        img.save(target, "JPEG", quality=80, optimize=True, progressive=True)
    return f"img/covers/{target.name}"


def icon(pattern, size=96):
    """Small transparent picture for the menu, as a file under img/covers/: trimmed to its visible part, centred on a
    square and shrunk to `size` px (shown at a third of that, sharp on high-density screens). Returns its page path."""
    from PIL import Image

    path = next(HERE.glob(pattern))
    out_dir = IMG_OUT / "covers"
    out_dir.mkdir(parents=True, exist_ok=True)
    tag = hashlib.sha1(f"{path.stat().st_mtime_ns}-{size}".encode()).hexdigest()[:8]
    target = out_dir / f"{path.stem}-{tag}.png"
    if not target.exists():
        for stale in out_dir.glob(f"{path.stem}-*.png"):
            stale.unlink()
        img = Image.open(path).convert("RGBA")
        img = img.crop(img.getchannel("A").getbbox())
        side = max(img.size)
        square = Image.new("RGBA", (side, side))
        square.paste(img, ((side - img.width) // 2, (side - img.height) // 2))
        square.resize((size, size), Image.LANCZOS).save(target, "PNG", optimize=True)
    return f"img/covers/{target.name}"


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
            # The strip is wide: a square or portrait picture keeps only a centred band of PHOTO_RATIO,
            # so the subject fills it instead of shrinking with the empty top and bottom
            w, h = img.size
            if h > w / PHOTO_RATIO:
                band = round(w / PHOTO_RATIO)
                img = img.crop((0, (h - band) // 2, w, (h - band) // 2 + band))
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

    sub_cols = [header.index(h) for h in cfg.get("sub", []) if h in header]

    values, images, subs = {}, {}, {}
    for row in values_ws.iter_rows(min_row=2, values_only=True):
        # a row is an item when it has a name and at least half its values (notes and helper rows have 0 or 1)
        if row[0] and sum(isinstance(v, (int, float, datetime)) for v in row[1 : 1 + n_cat]) * 2 >= n_cat:
            values[row[0]] = list(row[1 : 1 + n_cat])
            subs[row[0]] = " · ".join(str(row[i]) for i in sub_cols if row[i])
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
    items = [{"name": NAMES_EN.get(n, n) + (f" ({subs[n]})" if subs.get(n) else ""), "ranks": ranks[n], "values": values[n],
              **images.get(n, {})} for n in names]
    if cfg.get("short"):
        for it in items:
            words = it["name"].split(" (")[0].split()
            it["short"] = words[-1] if cfg["short"] == "last" else " ".join(words[1:]) or words[0]

    attach_photos(key, cfg, names, items)
    return game(key, cfg, path, items, cats)


def attach_photos(key, cfg, names, items):
    """Own photos beat spreadsheet URLs. A file matches the German or English name, the name without
    its bracket, any " / " part of it, or the short name: Monaco.jpg fits "Monaco (Monaco)"."""
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


def game(key, cfg, path, items, cats):
    # "cover" is a file, or a dict with the file and crop options; "bg" shows the whole picture on that colour
    c = cfg.get("cover")
    opts = c if isinstance(c, dict) else {"file": c}
    out = {**{k: v for k, v in cfg.items() if k in ("tab", "noun", "plural", "word", "kinds", "flagship", "sport")}, "source": path.name,
           "items": items, "cats": cats}
    if c and next(HERE.glob(opts["file"]), None):
        out["cover"] = cover(opts["file"], ratio=opts.get("ratio", 1.5), width=opts.get("width", 0.6), cy=opts.get("cy", 0.53))
        if opts.get("bg"):
            out["cover_bg"] = opts["bg"]
    return out


def load_wide(key, cfg):
    """One sheet, one row per item, the stats in named columns (rank columns are ignored and recomputed)."""
    path = next(HERE.glob(cfg["file"]))
    ws = openpyxl.load_workbook(path, data_only=True).worksheets[0]
    col = {h: i for i, h in enumerate(c.value for c in ws[1]) if h}
    missing = [h for h in cfg["cats"] if h not in col]
    if missing:
        raise SystemExit(f"{path.name}: columns not found: {missing}")
    rows = [r for r in ws.iter_rows(min_row=2, values_only=True) if r[col[cfg["name_col"]]]]
    if cfg.get("filter"):
        fcol, fval = cfg["filter"]
        rows = [r for r in rows if r[col[fcol]] == fval]

    cats = [{"name": en, "unit": unit, "fmt": fmt, "dir": d} for en, unit, fmt, d in cfg["cats"].values()]
    items = []
    for r in rows:
        name = str(r[col[cfg["name_col"]]]).strip()
        sub = " · ".join(str(r[col[c]]) for c in cfg.get("sub", []) if r[col[c]])
        vals = [r[col[h]] if isinstance(r[col[h]], (int, float)) else None for h in cfg["cats"]]
        words = name.split()
        short = SHORT_NAMES.get(name) or (" ".join(words[1:]) if cfg.get("short") == "surname" and len(words) > 1 else name)
        items.append({"name": f"{name} ({sub})" if sub else name, "short": short, "values": vals, "ranks": [None] * len(cats)})
    for i, cat in enumerate(cats):
        low = cat["dir"] in WIDE_LOW
        vals = [it["values"][i] for it in items if it["values"][i] is not None]
        for it in items:
            v = it["values"][i]
            if v is not None:
                it["ranks"][i] = 1 + sum(1 for w in vals if (w < v if low else w > v))
    attach_photos(key, cfg, [it["name"].split(" (")[0] for it in items], items)
    return game(key, cfg, path, items, cats)


SITE = "https://sport-minigames.com"
OLD_HOSTS = ["https://sportrankle.netlify.app"]   # old addresses: everything there redirects to SITE
GAME_PAGES = {
    "rankle": ("Rankle", "Eight categories, eight items arriving one by one: put each one where it ranks highest among the whole pool. Each category can be used once. The perfect board is revealed at the end."),
    "blind-ranking": ("Blind ranking", "One attribute, eight items arriving one by one: place each on spot 1 to 8 without knowing what comes next. Spots are final."),
    "sort-it": ("Sort it", "One attribute, all eight items in view: swap them into the right order, then reveal."),
    "ringer": ("Ringer", "The sports party game on one phone for 3 to 12 players: everyone gets the same secret except the ringer, who has to bluff along. Find out who it is."),
}
GAME_ROUTE = {"rankle": "#rankle", "blind-ranking": "#blind", "sort-it": "#sort", "ringer": "#ringer"}


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;")


def pages(data, sports):
    """Every crawlable page: (path, title, description, route hash, static intro html)."""
    cats = lambda g: ", ".join(c["name"].lower() for c in g["cats"][:5])
    topic_slug = {k: slug(g["tab"]) for k, g in data.items()}
    out = []
    for k, g in data.items():
        kinds = g.get("kinds") or ["rankle", "blind", "sort"]
        games = "Rankle, Blind ranking and Sort it" if len(kinds) == 3 else "Rankle"
        desc = (f"{g['tab']} quiz: rank {len(g['items'])} {g['plural']} by {len(g['cats'])} real categories such as {cats(g)}. "
                f"Play {games}, new cards every day, one attempt each, compare your score with everyone else's.")
        intro = (f"<h1>{esc(g['tab'])} quiz</h1><p>{esc(desc)}</p><h2>Categories</h2><ul>"
                 + "".join(f"<li>{esc(c['name'])} (rank 1 = {esc(c['dir'])})</li>" for c in g["cats"]) + "</ul>")
        out.append((topic_slug[k], f"{g['tab']} quiz - daily ranking puzzle | Sportrankle", desc, f"#t/{k}", intro))
    for sk, sp in sports.items():
        topics = [g for g in data.values() if g["sport"] == sk]
        if not topics:
            continue
        names = ", ".join(t["tab"] for t in topics)
        desc = f"{sp['name']} quizzes: {names}. Daily ranking puzzles on real stats, three games per topic, one attempt a day."
        intro = f"<h1>{esc(sp['name'])} quizzes</h1><p>{esc(desc)}</p><ul>" + "".join(
            f'<li><a href="/{topic_slug[k]}">{esc(g["tab"])}</a></li>' for k, g in data.items() if g["sport"] == sk) + "</ul>"
        out.append((slug(sp["name"]), f"{sp['name']} quizzes - {names} | Sportrankle", desc, f"#s/{sk}", intro))
    for gs, (name, blurb) in GAME_PAGES.items():
        desc = f"{name}: {blurb}" + ("" if gs == "ringer" else f" Play it on {len(data)} topics, from NFL teams to F1 circuits.")
        intro = f"<h1>{esc(name)}</h1><p>{esc(desc)}</p>"
        out.append((gs, f"{name} - daily sports ranking game | Sportrankle", desc, GAME_ROUTE[gs], intro))
    return out


def site_map(data, sports):
    """Real links to every page, shown under the home page and crawled from there."""
    lines = []
    for sk, sp in sports.items():
        topics = [(slug(g["tab"]), g["tab"]) for g in data.values() if g["sport"] == sk]
        if topics:
            lines.append(f'<p><b><a href="/{slug(sp["name"])}">{esc(sp["name"])}</a></b>: '
                         + ", ".join(f'<a href="/{s}">{esc(t)}</a>' for s, t in topics) + "</p>")
    lines.append('<p><b>Games</b>: ' + ", ".join(f'<a href="/{gs}">{esc(n)}</a>' for gs, (n, _) in GAME_PAGES.items()) + "</p>")
    return '<p class="sec">All puzzles</p>' + "".join(lines)


def ld_json(title, desc, url):
    return json.dumps([
        {"@context": "https://schema.org", "@type": "WebSite", "name": "Sportrankle", "url": SITE + "/"},
        {"@context": "https://schema.org", "@type": "WebApplication", "name": title.split(" | ")[0], "url": url, "description": desc,
         "applicationCategory": "GameApplication", "operatingSystem": "Any", "browserRequirements": "Requires JavaScript",
         "isAccessibleForFree": True, "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
         "publisher": {"@type": "Organization", "name": "Sportrankle", "url": SITE + "/"}},
    ], ensure_ascii=False)


def social_images():
    """og.jpg (1200x630) and the icons, from the team-sports cover."""
    from PIL import Image

    src = Image.open(HERE / "covers" / "sports.png").convert("RGB")
    w, h = src.size
    band = round(w / 1.905)
    y0 = max(0, round(h * 0.5 - band / 2))
    src.crop((0, y0, w, y0 + band)).resize((1200, 630), Image.LANCZOS).save(DIST.parent / "og.jpg", "JPEG", quality=85, optimize=True)
    side = round(w * 0.62)
    x0, y0 = (w - side) // 2, round(h * 0.5 - side / 2)
    icon = src.crop((x0, y0, x0 + side, y0 + side))
    for name, px in (("icon-512.png", 512), ("apple-touch-icon.png", 180), ("favicon.png", 64)):
        icon.resize((px, px), Image.LANCZOS).save(DIST.parent / name, "PNG", optimize=True)


def main():
    data = {key: (load_wide if cfg.get("format") == "wide" else load_game)(key, cfg) for key, cfg in GAMES.items()}
    for key, g in data.items():
        if len(g["items"]) < 8 or any(all(it["ranks"][i] is None for it in g["items"]) for i in range(len(g["cats"]))):
            raise SystemExit(f"{g['source']}: fewer than 8 rows or a category without values, build stopped.")
    # A game without a picture yet gets its name as cards on the home page
    kinds = {}
    for k, f in KIND_COVERS.items():
        opts = f if isinstance(f, dict) else {"file": f}
        if next(HERE.glob(opts["file"]), None):
            kinds[k] = cover(opts["file"], ratio=2, width=opts.get("width", 0.8), cy=opts.get("cy", 0.52), size=1000)
    # Sport groups: a picture of their own if covers/sport-<key>.png exists, otherwise the page uses a pool's;
    # a menu icon if covers/icon-<key>.png exists (a transparent PNG)
    sports = {k: {"name": s["name"], **({"cover": cover(s["cover"], width=0.75, cy=0.5)} if next(HERE.glob(s["cover"]), None) else {}),
                  **({"icon": icon(f"covers/icon-{k}.png")} if (HERE / "covers" / f"icon-{k}.png").exists() else {})}
              for k, s in SPORTS.items()}
    for key, g in data.items():
        if g.get("sport") not in SPORTS:
            raise SystemExit(f"{key}: unknown sport '{g.get('sport')}'")
    for g in data.values():   # the page each topic's share text links to
        g["url"] = f"{SITE}/{slug(g['tab'])}"
    base = (TEMPLATE.read_text(encoding="utf-8")
            .replace("__DATA__", json.dumps(data, ensure_ascii=False))
            .replace("__SPORTS__", json.dumps(sports, ensure_ascii=False))
            .replace("__KINDS__", json.dumps(kinds))
            .replace("__SUPABASE__", json.dumps(SUPABASE if SUPABASE["key"] else None))
            .replace("__SITEMAP__", site_map(data, sports)))

    def page(title, desc, url, route, intro):
        return (base.replace("__TITLE__", esc(title)).replace("__DESC__", esc(desc)).replace("__CANON__", url)
                .replace("__ROUTE__", json.dumps(route)).replace("__STATIC__", intro)
                .replace("__LDJSON__", ld_json(title, desc, url)))

    home_title = "Sportrankle - daily sports ranking puzzles: NFL, F1, Champions League, skiing"
    home_desc = ("Free daily sports quiz games. Rank NFL teams, Champions League players, F1 circuits, alpine skiers and the "
                 "world's top athletes by their real stats. New puzzles every day, one attempt each, compare with everyone.")
    home = page(home_title, home_desc, SITE + "/", "", "<h1>Daily sports ranking puzzles</h1><p>" + esc(home_desc) + "</p>")
    OUT.write_text(home, encoding="utf-8")
    DIST.parent.mkdir(exist_ok=True)
    head = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n')
    DIST.write_text(f"{head}{home}\n</html>\n", encoding="utf-8")
    # One real URL per topic, sport and game: the same app, opened on that view, with its own title and description
    urls = [SITE + "/"]
    redirects = []
    for path, title, desc, route, intro in pages(data, sports):
        (DIST.parent / f"{path}.html").write_text(f"{head}{page(title, desc, f'{SITE}/{path}', route, intro)}\n</html>\n", encoding="utf-8")
        urls.append(f"{SITE}/{path}")
        redirects.append(f"/{path}  /{path}.html  200")
    redirects = [f"{h}/* {SITE}/:splat 301!" for h in OLD_HOSTS] + redirects
    (DIST.parent / "_redirects").write_text("\n".join(redirects) + "\n", encoding="utf-8")
    (DIST.parent / "_headers").write_text("/img/*\n  Cache-Control: public, max-age=31536000, immutable\n", encoding="utf-8")
    (DIST.parent / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8")
    (DIST.parent / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{u}</loc><changefreq>daily</changefreq></url>\n" for u in urls) + "</urlset>\n", encoding="utf-8")
    (DIST.parent / "site.webmanifest").write_text(json.dumps({
        "name": "Sportrankle", "short_name": "Sportrankle", "start_url": "/", "display": "standalone",
        "background_color": "#121210", "theme_color": "#121210",
        "icons": [{"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"}]}), encoding="utf-8")
    social_images()
    if IMG_OUT.is_dir():
        shutil.copytree(IMG_OUT, DIST.parent / "img", dirs_exist_ok=True)
    for key, g in data.items():
        own = sum(1 for it in g["items"] if it.get("img", "").startswith("img/"))
        pics = sum(1 for it in g["items"] if "img" in it)
        print(f"{key}: {len(g['items'])} items, {len(g['cats'])} categories, {pics} images ({own} own photos) from {g['source']}")
    print(f"{len(urls)} pages, sitemap, robots, og.jpg, icons")


if __name__ == "__main__":
    main()
