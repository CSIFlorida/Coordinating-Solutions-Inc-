"""
City -> Area classification.

Areas (per the CSI Visit Tracking System spec):
  SOUTHERS  = Miami-Dade County + Florida Keys
  SOUTHEAST = Broward County + Palm Beach County
  CENTRAL   = Orlando + Central Florida

Matching is case-insensitive and tolerant of leading/trailing whitespace.
Any city not found in the table below returns "Unclassified" so it surfaces
for manual review instead of being silently mis-bucketed.
"""

SOUTHERS_CITIES = {
    # Miami-Dade County
    "miami", "miami beach", "miami gardens", "miami lakes", "miami shores",
    "miami springs", "hialeah", "hialeah gardens", "opa-locka", "homestead",
    "florida city", "cutler bay", "palmetto bay", "pinecrest", "south miami",
    "north miami", "north miami beach", "aventura", "doral", "coral gables",
    "north bay village", "naranja", "west miami", "wm", "sweetwater",
    "westchester", "kendall", "richmond heights",
    # Florida Keys
    "key largo", "big pine key", "big torch key", "marathon", "key west",
    "islamorada", "tavernier",
}

SOUTHEAST_CITIES = {
    # Broward County
    "fort lauderdale", "hollywood", "pembroke pines", "miramar", "sunrise",
    "coral springs", "plantation", "davie", "lauderhill", "deerfield beach",
    "pompano beach", "margate", "tamarac", "north lauderdale", "weston",
    "cooper city", "southwest ranches", "oakland park", "parkland",
    "coconut creek", "dania", "dania beach", "west park", "lauderdale lakes",
    "pembroke park", "hallandale beach", "wilton manors", "lighthouse point",
    # Palm Beach County
    "west palm beach", "boca raton", "delray beach", "lake worth",
    "greenacres", "belle glade", "boynton beach", "wellington",
    "royal palm beach", "jupiter", "palm beach gardens", "riviera beach",
}

CENTRAL_CITIES = {
    "orlando", "kissimmee", "sanford", "saint cloud", "cloud", "st cloud",
    "st. cloud", "longwood", "apopka", "oviedo", "ocoee", "leesburg",
    "kenansville", "port saint lucie", "port st lucie", "winter park",
    "winter garden", "winter springs", "altamonte springs", "clermont",
    "deland", "deltona", "lake mary", "casselberry",
}

AREA_LABELS = {
    "SOUTHERS": "Southers Area",
    "SOUTHEAST": "Southeast Area",
    "CENTRAL": "Central Area",
    "UNCLASSIFIED": "Unclassified",
}


def classify_city(city):
    if not city:
        return "UNCLASSIFIED"
    key = city.strip().lower()
    if key in SOUTHERS_CITIES:
        return "SOUTHERS"
    if key in SOUTHEAST_CITIES:
        return "SOUTHEAST"
    if key in CENTRAL_CITIES:
        return "CENTRAL"
    return "UNCLASSIFIED"


def area_label(area_code):
    return AREA_LABELS.get(area_code, "Unclassified")
