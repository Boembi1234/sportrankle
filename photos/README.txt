Own photos for the game screens
================================

Drop a picture into the folder of its game, named like the item:

  photos/sports/Football.jpg          (English or German sheet name: Fussball.jpg works too)
  photos/f1/Monaco.jpg                (the part before the bracket is enough)
  photos/nfl/Dallas Cowboys.jpg
  photos/ski/Odermatt.jpg             (surname is enough)

jpg, jpeg, png and webp are fine, any size (landscape works best, it is shown wide).
Capitals, spaces, accents and hyphens do not matter: "loic meillard.png" = "Loïc Meillard".

Then run:  python build.py
It shrinks each photo to 1200 px into img/<game>/ and copies that folder to dist/,
so deploy dist as usual. A photo here replaces a spreadsheet Bild-URL for the same item.
Files that match nothing are listed at the end of the build.

Source link (optional): put a credits.txt into the game folder, one line per photo:

  Monaco.jpg = https://commons.wikimedia.org/wiki/File:Monaco_....jpg

Photos with a credit become a link to that page.
