# Sportrankle – Design

Design-Richtung **«Tischanzeige»**. Die Website sieht aus wie eine altmodische Klapp-Anzeigetafel zum Umblättern, wie sie am Spielfeldrand steht: graue Karten mit weissen Zeichen an Metallringen, im dunklen Modus. Diese Datei ist die verbindliche Designvorgabe für alle Screens.

---

## 1. Konzept

- **Die Startseite ist das Spiel.** Es gibt keine Marketing-Hero-Sektion, keinen Slogan und keine Feature-Liste. Wer die Seite öffnet, sieht sofort die aktuelle Runde.
- **Dunkler Modus ist Standard.** Die grauen Karten stehen auf einem dunklen Grund wie eine Tafel am Abendspiel unter Flutlicht.
- **Spielprinzip (Struktur):** Pro Spiel gibt es 8 Runden. In jeder Runde erscheint eine Sportart mit Foto. Der Spieler ordnet sie einer der 8 Kategorien zu, in der sie seiner Meinung nach den besten Rang holt. Jede Kategorie kann nur einmal belegt werden. Nach dem Auflösen zeigt die Kategorie Rang, Wert und Punkte.
- **Die Karte ist das eine auffällige Element.** Alles andere bleibt ruhig und zurückhaltend. Die Karten tragen die Persönlichkeit.
- **Das Vorbild ist ein echtes Objekt.** Farben, Formen und Bewegung orientieren sich an der physischen Umblätter-Tafel. Im Zweifel gilt die Frage: Würde es auf der echten Tafel so aussehen?
- **Beim Spielen muss alles auf einen Screen passen, auch auf dem Handy.** Alle fünf Auswahlen, die Frage und der Button sind ohne Scrollen sichtbar (siehe Abschnitt 5).

---

## 2. Farben

```css
:root {
  --bg:           #121210;  /* Seitenhintergrund (dunkel) */
  --surface:      #22282A;  /* Foto-Platzhalter / Flächen */
  --line:         #2A2A27;  /* Trennlinien */
  --line-strong:  #34332F;
  --text:         #EDEBE4;  /* Standardtext */
  --muted:        #9A968C;  /* Nebentext (Kontrast ok ab 12px) */

  --card:         #6B6667;  /* Karte, warmes Grau */
  --card-edge:    #4E4A4B;  /* Kante der Karte (Kartenstapel) */
  --card-stack:   #3A3738;  /* zweite Karte im Stapel dahinter */
  --card-mini:    #3A3839;  /* kleine Wert-Karten in Zeilen */
  --card-open:    #45443F;  /* gestrichelter Rahmen: Kategorie noch frei */
  --glyph:        #FAFAF7;  /* Zeichen auf der Karte */
  --ring:         #A9ADB2;  /* Metallring */

  --signal:       #F2C230;  /* Akzent: Button, Auswahl, Punkte */
  --signal-edge:  #C99A12;
  --selected-bg:  #1E1D17;  /* Hintergrund der gewählten Zeile */

  /* optional nach dem Auflösen */
  --correct:      #2F7D46;
  --wrong:        #B8412A;
}
```

**Regeln**

- Es gibt genau eine Akzentfarbe (`--signal`). Sie wird für den aktiven Button, die gewählte Zeile und die Punkte verwendet.
- `--correct` und `--wrong` sind optional und färben nach dem Auflösen höchstens die Rang-Karte selbst. Das Zeichen bleibt weiss.
- Keine Verläufe, keine Glows und keine weichen Schatten. Tiefe entsteht nur durch die harte Kartenkante (siehe Abschnitt 4).
- Der Text auf `--signal` ist immer `--bg` (dunkel).

---

## 3. Typografie

**Eine Familie: Archivo** (Google Fonts, variable mit Breiten-Achse `wdth` 62–125 und Gewicht 400–900). Fallback: `'Arial Narrow', sans-serif`.

```
https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..900&display=swap
```

| Token | Desktop | Mobile | Einstellung | Verwendung |
|---|---|---|---|---|
| `card-xl` | 56px | 29px | 800, normale Breite | Titelkarten (Name der Sportart) |
| `card-m` | 30px | 24px | 800, tabular | Rang-Karte |
| `card-s` | 14px | 11px | 800 | Mini-Karten für Werte |
| `question` | 32px / lh 1.1 | 21px / lh 1.15 | 700, `font-stretch: 85%` | Frage |
| `category` | 18px | 15px | 700 | Kategoriename |
| `hint` | 14px | 12px | 400 | «Rang 1 = …», Sportart in belegten Zeilen |
| `points` | 18px | 15px | 800, tabular, `--signal` | Punkte |
| `counter` | 18px | 17px | 800, tabular | Runde / Punkte in der Kopfzeile |
| `button` | 22px | 20px | 800 | Haupt-Button |

**Regeln**

- Grossbuchstaben stehen nur auf den Karten. Alles andere ist in normaler Schreibweise (auch Kategorien, Labels und Buttons).
- Keine Labels über jeder Sektion. Spaltenköpfe sind klein und in normaler Schreibweise.
- Zahlen immer mit `font-variant-numeric: tabular-nums`.
- Einzelne Wörter in Überschriften werden nicht farbig oder kursiv hervorgehoben.

---

## 4. Die Karte (Kernkomponente)

Die Karte ist eine graue Fläche mit abgerundeten Ecken und einem grossen weissen Zeichen. Sie hat **keine Trennlinie in der Mitte**, weil es sich um Umblätter-Karten handelt und nicht um ein Fallblatt.

```
    ◯          ← Metallring (nur Titelkarten)
┌────────┐
│        │     Hintergrund --card
│   S    │     Radius ≈ 10 % der Breite
│        │
└────────┘
 ▔▔▔▔▔▔▔▔     harte Kante: box-shadow 0 2px 0 --card-edge,
              dahinter 0 4px 0 --card-stack (Kartenstapel)
```

**Grössen**

| Variante | Desktop B × H | Mobile B × H | Radius | Einsatz |
|---|---|---|---|---|
| `xl` | 58 × 78 | 32 × 44 | 8 / 5px | Titelkarten (Sportart), mit Ring |
| `m` | 44 × 52 | 36 × 42 | 6 / 5px | Rang in der Kategorie-Zeile |
| `s` | 18 × 24 | 13 × 17 | 3 / 2px | Werte (Jahr, Anzahl, Länge) |

- **Ring:** ein kleines Oval (Desktop 12 × 18px, Mobile 8 × 11px), das mit 3px bzw. 2px Rahmen in `--ring` mittig über der Karte sitzt. Ringe gibt es nur an den Titelkarten.
- **Freie Karte:** kein Hintergrund, 1.5px gestrichelter Rahmen in `--card-open`, ohne Zeichen.
- **Abstand** zwischen Karten: 4–6px.

**Animation (das eine Bewegungs-Highlight)**

- Beim Auflösen wird die Karte **über den oberen Rand umgeblättert**, wie am Ring. Dabei gilt `transform-origin: top`, `rotateX` 0 → −180°, ca. 280 ms, `ease-in-out`. Darunter erscheint die neue Karte.
- Werte mit mehreren Stellen blättern von links nach rechts gestaffelt um (ca. 60 ms Versatz). Die Zeilen folgen von oben nach unten.
- Optional gibt es einen leisen Papier-Umblätter-Sound, standardmässig aus.
- Bei `prefers-reduced-motion: reduce` gibt es kein Umblättern, der Wert erscheint direkt.
- **Sonst gibt es keine Animationen**: kein Fade-in von Sektionen und keine Hover-Effekte auf Zeilen.

---

## 5. Foto

- Jede Sportart hat ein Foto, eine echte Spielszene (kein Logo, keine Illustration).
- Format: volle Breite, Höhe 140px auf dem Handy bzw. 220px auf dem Desktop, Radius 8px, `object-fit: cover`.
- Die Titelkarten mit dem Namen der Sportart **überlappen die Unterkante des Fotos** um die halbe Kartenhöhe. So hängen die Karten wie an einer Tafel vor dem Bild.
- Ohne Foto (oder während des Ladens) zeigt die Fläche `--surface` und einen dezenten Hinweis. Das Layout springt dabei nicht.
- Das Foto bekommt einen `alt`-Text wie «Wasserball, Spielszene».
- Bildrechte klären: Wikimedia Commons (Lizenz und Urheber angeben) oder lizenzierte Fotos.

---

## 6. Layout

### Grundregel: Spielen ohne Scrollen

Der Spiel-Screen (Kopfzeile, Foto, Titel, Frage, **alle 8 Kategorien**, Button) muss ohne Scrollen in den Viewport passen:

- auf dem Handy ab **360 × 640** (sichtbare Fläche nach Browser-Leisten),
- auf dem Desktop ab **1280 × 720**.

**Platzbudget Handy (390 × 844):**

| Element | Höhe |
|---|---|
| Kopfzeile | 52px |
| Foto | 140px |
| Titelkarten (überlappen Foto) | + 22px |
| Frage | ca. 60px |
| 8 Kategorien à 52px | 416px |
| Button | 52px |
| Abstände | ca. 40px |
| **Total** | **ca. 780px** |

Umsetzung:

- Den Spiel-Screen mit `height: 100dvh` als Flex-Spalte bauen.
- Die Zeilenhöhe skaliert: `height: clamp(44px, 6.2dvh, 56px)`.
- Das Foto schrumpft zuerst: `height: clamp(72px, 17dvh, 160px)`.
- Wird es trotzdem zu eng, fällt die Hinweiszeile («Rang 1 = …») weg. **Scrollen ist der allerletzte Ausweg.**
- Bei langen Sportnamen (mehr als 10 Buchstaben) werden die Titelkarten schmaler (min. 26px). Reicht das nicht, bricht der Name auf zwei Kartenreihen um.

### Mobile (< 640px), Innenabstand 16px

```
┌──────────────────────────┐
│ ═      5/8 │ 48 Pkt    ▥ │  Kopfzeile 52px
│ ┌──────────────────────┐ │
│ │        Foto          │ │  140px
│ │                      │ │
│ └[W][A][S][S][E][R]...─┘ │  Karten 32×44 überlappen
│ Wo holt Wasserball den   │
│ besten Rang?             │
├──────────────────────────┤
│ [10] Teams an der letz…  +11 │  belegt
│      Rollhockey [1][6]   │
│ [4 ] Entstehungsjahr     +17 │
│ [  ] Gewicht Spielgerät  │  frei (gestrichelte Karte)
│      Rang 1 = schwerstes │
│ ...                      │  8 Zeilen à 52px
│ [      Auflösen        ] │  52px
└──────────────────────────┘
```

### Desktop (≥ 1024px)

- Zwei Spalten: links Foto (volle Spaltenhöhe) mit Titelkarten und Frage, rechts die 8 Kategorien als Liste.
- Kopfzeile wie auf dem Handy, die Navigation steht zusätzlich als Text rechts.
- Max. Breite 1280px, Innenabstand 48px.

---

## 7. Interaktion

- **Kategorie wählen:** Man tippt auf eine freie Zeile. Sie wird ausgewählt (2px-Rahmen innen in `--signal`, Hintergrund `--selected-bg`), und der Button «Auflösen» wird aktiv (vorher `--line` mit gedämpftem Text). Ein zweiter Tipp auf eine andere Zeile wechselt die Auswahl.
- **Auflösen:** Die gestrichelte Karte der gewählten Zeile blättert auf den Rang um. Darunter erscheinen die Sportart und der Wert als kleine Karten, rechts die Punkte (`+11`) in `--signal`. Danach erscheint die nächste Sportart: Das Foto wechselt, und die Titelkarten blättern auf den neuen Namen um.
- **Belegte Zeilen** sind nicht mehr antippbar (`disabled`), bleiben aber voll lesbar.
- **Kopfzeile:** Rundenzähler `5/8` und Punktestand. Der Punktestand zählt beim Auflösen kurz hoch.
- **Tastatur:** Die Zeilen sind echte `<button>`. Tab bzw. Pfeiltasten navigieren, Enter wählt, und eine Live-Region meldet das Resultat, zum Beispiel «Wasserball: Rang 4 in Entstehungsjahr, plus 17 Punkte».

---

## 8. Komponenten

**Kopfzeile (Spiel):** Menü-Button links, in der Mitte Runde `5/8` und Punkte, getrennt durch eine 1px-Linie, rechts ein Statistik-Button. Es gibt keinen Rahmen und keine Pill um den Zähler.

**Kategorie-Zeile:** Das Raster ist `36px | 1fr | auto`, die Höhe 52px, und es gibt eine Trennlinie in `--line`.
- *Frei:* gestrichelte leere Karte (36 × 42px, 1.5px dashed `--card-open`), der Kategoriename (15px, 700) und darunter der Hinweis «Rang 1 = …» (12px, `--muted`).
- *Belegt:* Rang-Karte (`--card`, Zahl 24px 800), der Kategoriename, darunter die Sportart und der Wert als Mini-Karten (13 × 17px, `--card-mini`), optional eine Einheit («m») und rechts die Punkte.
- *Gewählt:* wie frei, aber mit Auswahlrahmen.

**Haupt-Button:** aktiv mit Fläche `--signal`, Text `--bg`, Radius 7px und harter Kante `0 3px 0 --signal-edge`, inaktiv mit Fläche `--line` und Text `--muted`. Er ist mindestens 52px hoch. Pro Screen gibt es nur einen. Der Text sagt, was passiert: «Auflösen», «Nächstes Spiel».

**Sekundäre Links:** normale Schrift, unterstrichen, kein Button-Look.

---

## 9. Texte und Ton

- Die Sprache ist Deutsch (Schweiz), also «ss» statt «ß».
- Die Texte sind kurz und klingen nach Sport statt nach Software: «Anpfiff», «Auflösen», «Neue Karten um Mitternacht».
- Es gibt keine Werbesätze («Entdecke…», «Die ultimative…»).
- Leere und Fehlerzustände sagen, was los ist und was man tun kann. Zum Beispiel: «Heute schon gespielt. Die nächste Runde kommt um Mitternacht.»

---

## 10. Nicht tun

- Trennlinien in der Kartenmitte (das wäre ein Fallblatt, kein Umblätter-Brett)
- Hero-Sektion mit Slogan links und Karte rechts, dazu zwei Buttons nebeneinander
- abgerundete Content-Karten mit weichen Schatten, Glassmorphism, Verläufe
- Emojis und Sparkle-Icons (auch nicht als Kategorie-Icons)
- Inter, Roboto, Arial und System-Fonts als Gestaltungsschrift
- Metazeilen mit Mittelpunkten («A · B · C»), Labels im Stil «WORT — Text» und Versal-Labels
- Pfeile (→) an Button-Texten
- Fade-/Slide-Animationen beim Scrollen und Hover-Effekte auf jedem Element
- ein Spiel-Screen, auf dem man scrollen muss

---

## 11. Barrierefreiheit

- Kontrast mindestens 4.5:1 für Text. Weiss auf `--card` und `--muted` auf `--bg` erfüllen das.
- Kartenreihen haben ein `aria-label` mit dem vollen Wort bzw. Wert. Die einzelnen Karten sind `aria-hidden`.
- Sichtbarer Fokus: 2px-Outline in `--text` mit 2px Abstand.
- Klickflächen sind mindestens 44 × 44px.
