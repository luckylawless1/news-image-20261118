#!/usr/bin/env python3
"""Compose "THE WORLD IN ONE DAY": ONE 1024x1024 image summing up the
world's news of Wednesday 18 November 2026 as a dense broadsheet front
page — 56 numbered stories across 7 regions.

Layout, top to bottom: masthead with a red strapline; a DAY IN NUMBERS
band of six figures; a region band whose counts sum to the story total;
the lead story (the Gulf clash) with a drawn map of the Strait of
Hormuz; three hero cards; a dot-matrix "WHERE IT HAPPENED" world map
with numbered pins flanked by MARKETS and WEATHER WATCH boxes; a
one-line UTC timeline; a four-column grid of story cards and briefs;
SCIENCE & SPACE and THURSDAY PREVIEW boxes; and a red DATE CHECK
footer. The differentiator boxes (markets, weather, science, preview)
are highlight panels: their items are not part of the numbered 56.

Style: cream paper #F7F2E4, navy #21406A accents, black serif headlines,
red #B01E24 section labels, thin black rules. Headlines in Liberation
Serif Bold, body text in Liberation Sans.

The output is deterministic: the same inputs always produce
byte-identical bytes, saved as a true PNG named entry.png in this
directory.
"""

import hashlib
import io
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent

W = H = 1024
MARGIN = 24
CW = W - 2 * MARGIN  # content width

PAPER = (247, 242, 228)
INK = (17, 17, 17)
BODY_INK = (43, 43, 43)
RED = (176, 30, 36)
NAVY = (33, 64, 106)
RULE = (17, 17, 17)
HAIR = (150, 143, 122)
SEA = (33, 64, 106)
LAND = (216, 190, 140)
BLAST = (242, 121, 20)

SERIF = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
SERIF_FALLBACK = "DejaVuSerif-Bold.ttf"
SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
SANS_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
SANS_FALLBACK = "DejaVuSans.ttf"
SANS_BOLD_FALLBACK = "DejaVuSans-Bold.ttf"

MAX_BYTES = 1_000_000

_font_cache = {}


def _load(path, fallback, size):
    key = (path, size)
    if key not in _font_cache:
        try:
            _font_cache[key] = ImageFont.truetype(path, size)
        except OSError:
            _font_cache[key] = ImageFont.truetype(fallback, size)
    return _font_cache[key]


def serif(size):
    return _load(SERIF, SERIF_FALLBACK, size)


def sans(size):
    return _load(SANS, SANS_FALLBACK, size)


def sans_bold(size):
    return _load(SANS_BOLD, SANS_BOLD_FALLBACK, size)


def wrap_text(draw, text, font, max_width):
    """Greedy word wrap; returns the list of lines that fit max_width."""
    lines = []
    current = ""
    for word in text.split():
        trial = word if not current else current + " " + word
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def truncate_lines(draw, text, font, max_width, max_lines):
    """Wrap text and keep at most max_lines, ellipsising the last line."""
    lines = wrap_text(draw, text, font, max_width)
    if len(lines) <= max_lines:
        return lines
    lines = lines[:max_lines]
    last = lines[-1]
    while last and draw.textlength(last + "\u2026", font=font) > max_width:
        last = last[:-1].rstrip()
    lines[-1] = last + "\u2026"
    return lines


def wrap_variable(draw, text, font, widths):
    """Wrap text where line i may use widths[i] (the last width repeats)."""
    lines = []
    current = ""
    for word in text.split():
        limit = widths[min(len(lines), len(widths) - 1)]
        trial = word if not current else current + " " + word
        if draw.textlength(trial, font=font) <= limit:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def fit_font(draw, text, loader, start, minimum, max_width):
    """Largest font from loader (<= start, >= minimum) that fits max_width."""
    size = start
    while size > minimum:
        font = loader(size)
        if draw.textlength(text, font=font) <= max_width:
            return font, size
        size -= 1
    return loader(minimum), minimum


# ---------------------------------------------------------------- stories
# Region tags; the region band and the strapline count are computed from
# these tags, so every number printed on the page agrees by construction.

APAC = "ASIA-PACIFIC"
EU = "EUROPE"
AM = "THE AMERICAS"
ME = "MIDDLE EAST"
AF = "AFRICA"
OC = "OCEANIA"
GL = "GLOBAL"
REGION_ORDER = [APAC, EU, AM, ME, AF, OC, GL]

LEAD_LABEL = "LEAD STORY \u2014 THE GULF"
LEAD_HEADLINE = ("U.S. strikes Iran missile site; Iran answers at "
                 "Kuwait & Bahrain")
LEAD_BODY = (
    "American jets hit a Revolutionary Guards launch site on Qeshm Island "
    "at the mouth of the Strait of Hormuz. Iran replied with drones and "
    "missiles at bases hosting U.S. forces in Kuwait and Bahrain; tankers "
    "burned in the strait and oil climbed towards $93."
)
LEAD_REGION = ME

# (label, headline, body, region)
HEROES = [
    ("SHENZHEN \u2014 APEC SUMMIT",
     "Xi & Putin meet in Shenzhen ahead of trilateral summit",
     "The two leaders opened the APEC summit in Shenzhen; on Thursday "
     "they sit down with President Trump.", APAC),
    ("WASHINGTON \u2014 THE SENATE",
     "Alaska flips: Peltola beats Sullivan, Senate goes 56\u201344",
     "Democrat Mary Peltola unseated Republican Dan Sullivan, sealing a "
     "projected 56\u201344 Senate majority.", AM),
    ("TECHNOLOGY \u2014 CHIPMAKING",
     "Nvidia posts a record $115.8bn quarter, up 103%",
     "Revenue more than doubled on AI-chip demand; the board declined "
     "to reinstate Jensen Huang as CEO.", GL),
]

# Story cards: (section label, headline, body, region)
CARDS = [
    ("UKRAINE WAR", "Kerch Bridge hit for a second day; span partly down",
     "Kyiv struck the Crimea bridge again; part of the road span "
     "collapsed, Moscow said.", EU),
    ("SPACE", "Voyager 1 reaches one light-day from Earth",
     "NASA's 1977 probe is now a full day away by radio signal; no "
     "object has gone farther.", GL),
    ("HEALTH \u2014 CONGO", "Ebola cases pass 11,000 in DR Congo",
     "The outbreak keeps spreading in the east as response teams race "
     "to ring-fence hotspots.", AF),
    ("EUROPE", "EU proposes \u20ac45bn loan for Ukraine in 2027",
     "Brussels paired the loan plan with budget sign-off and a new "
     "Indonesia trade deal.", EU),
    ("TECHNOLOGY", "OpenAI launches GPT-6.2 Astra and Sol",
     "The new flagship models arrive with lower API prices, heating "
     "up the AI price war.", GL),
    ("INDIA \u2014 WEATHER", "Cyclone Akvan strengthens towards Andhra coast",
     "The severe storm is due to cross the coast on Friday; Odisha is "
     "evacuating villages.", APAC),
    ("GAZA", "Board of Peace faults Israel and Hamas alike",
     "Trump's board faulted both sides over the ceasefire as "
     "rebuilding stalled.", ME),
    ("GAZA \u2014 AID", "950,000 displaced Gazans on flood-prone ground",
     "The WHO warned the camps sit on ground prone to flooding as "
     "winter closes in.", ME),
    ("AFGHANISTAN", "Earthquake kills more than 600 in the east",
     "A powerful quake flattened villages in eastern Afghanistan; "
     "rescuers dug by hand.", APAC),
    ("CLIMATE", "COP31 splits over fossil-fuel draft text",
     "An 18-page draft urged a phase-out and net zero in wealthy "
     "nations by 2030.", EU),
    ("INDIA \u2014 ECONOMY", "India wholesale inflation hits 12.29%, a high",
     "October's wholesale prices rose 12.29%, the fastest pace in "
     "four years.", APAC),
    ("ASIA \u2014 QUAD", "Quad leaders unveil new plan in Manila",
     "The four-nation bloc set out a fresh Indo-Pacific plan as Trump "
     "arrived for talks.", APAC),
]

# Briefs: (headline, one-line body, region)
BRIEFS = [
    ("Knesset elects Matan Kahana as speaker",
     "An early win for prime minister-elect Eisenkot.", ME),
    ("Australia and UK sanction settlement firms",
     "Coordinated moves over West Bank settlement growth.", ME),
    ("Iran army helicopter crashes in Isfahan",
     "Four dead as the aircraft came down in the province.", ME),
    ("Oman and Qatar keep Gulf mediation open",
     "Envoys shuttled as both sides traded strikes.", ME),
    ("Tanker traffic slows through Hormuz",
     "Crews await escorts after two tankers caught fire.", ME),
    ("Odisha evacuates coast, shuts schools",
     "Villages empty ahead of Cyclone Akvan's landfall.", APAC),
    ("Myanmar junta to review ties with ASEAN",
     "The generals signal a rethink of bloc relations.", APAC),
    ("India and Japan hold 2+2 talks in Tokyo",
     "Fourth defence and foreign ministers' dialogue.", APAC),
    ("Seoul courts Beijing at APEC gathering",
     "President Lee used the summit to warm China ties.", APAC),
    ("Pakistan building explosion toll hits 16",
     "Rescuers searched the rubble for survivors.", APAC),
    ("Dhoni retires from the Indian Premier League",
     "India's former captain ends his IPL career.", APAC),
    ("APEC leaders vow to fight protectionism",
     "The bloc opened in Shenzhen with a trade pledge.", APAC),
    ("UK inflation climbs to 3.6%",
     "Energy price cap forecast to jump 26% in January.", EU),
    ("Burnham: Brexit has not worked",
     "The PM spoke ahead of a reset summit with the EU.", EU),
    ("Russia accuses France over Ukraine mission",
     "Paris rejected claims of direct involvement.", EU),
    ("Le Pen proposes cutting retirement age",
     "The French right pressed its pension pledge.", EU),
    ("Russia to fit hypersonic missiles on new subs",
     "Nuclear submarines to get the new weapons.", EU),
    ("Steinmeier to visit Beirut blast site",
     "Germany's president will tour the port area.", EU),
    ("Moscow says 1,400 drones downed overnight",
     "The claim came as the Kerch Bridge burned.", EU),
    ("EU signs off Indonesia trade deal",
     "The pact was approved alongside the budget.", EU),
    ("House Democrats nominate Jeffries for speaker",
     "Hakeem Jeffries won the nod 251 votes to 11.", AM),
    ("Jesse Jackson dies at 84",
     "Civil rights leader, two-time presidential hopeful.", AM),
    ("Outages 'not an attack', Congress told",
     "Officials warned Iran probes US water and banks.", AM),
    ("FAA chief takes blame for ground stop",
     "The stoppage had snarled US flights this week.", AM),
    ("Florida floods; Carolina told to boil water",
     "15 inches of rain fell on South Florida.", AM),
    ("US signs military pact with Venezuela",
     "Part of the 'Donroe Doctrine' for the hemisphere.", AM),
    ("Mexico urges calm after cartel chief's death",
     "Violence erupted across several states.", AM),
    ("Journalist Camilo Rodr\u00edguez shot dead",
     "First such killing in Costa Rica in 25 years.", AM),
    ("Pope Leo XIV ends 12-day Peru tour",
     "'Hasta luego' to his second homeland.", AM),
    ("New York orders travel ban as storm hits",
     "A major storm struck the US East Coast.", AM),
    ("GTA VI launches at midnight worldwide",
     "The game rolls out region by region tonight.", AM),
    ("Trump in Manila en route to Shenzhen",
     "Talks with Quad leaders before the summit.", AM),
    ("Chad closes its border with Sudan",
     "The frontier shut as regional tensions rose.", AF),
    ("Sudan and Ethiopia trade accusations",
     "Each side accused the other of arming groups.", AF),
    ("Nigeria Senate targets sponsors of violence",
     "Candidates who fund violence face disqualification.", AF),
    ("US loses measles-free status after 26 years",
     "Elimination status lapsed amid rising cases.", GL),
    ("Oil jumps, shares slide on Gulf escalation",
     "Asian markets fell as crude climbed to ~$93.", GL),
    ("Nvidia board declines to reinstate Huang",
     "Jensen Huang stays off the CEO chair he founded.", GL),
    ("Australia pledges Pacific coast-guard funds",
     "Canberra made the pledge on APEC's sidelines.", OC),
    ("New Zealand joins Pacific relief pact",
     "Wellington signed the disaster-relief deal.", OC),
]

NUMBERED_REGIONS = ([LEAD_REGION] + [h[3] for h in HEROES]
                    + [c[3] for c in CARDS] + [b[2] for b in BRIEFS])
TOTAL_STORIES = len(NUMBERED_REGIONS)
REGION_COUNTS = {r: NUMBERED_REGIONS.count(r) for r in REGION_ORDER}

# The six figures of the day: (figure, caption)
NUMBERS = [
    ("$115.8bn", "Nvidia record quarterly revenue, +103%"),
    ("~$93", "oil after the Gulf strikes"),
    ("1,400+", "drones Russia says it downed over Ukraine"),
    ("600+", "killed in the Afghan earthquake"),
    ("11,000+", "Ebola cases in DR Congo"),
    ("56\u201344", "projected Senate majority after Alaska flips"),
]

TIMELINE = [
    ("Morning", "APEC opens in Shenzhen"),
    ("Midday", "Kerch Bridge struck for a second day"),
    ("Evening", "Nvidia posts its record quarter"),
    ("Night", "Akvan strengthens over the Bay of Bengal"),
]

MARKETS_LINES = [
    "Nvidia: $115.8bn record quarter",
    "revenue +103% year on year",
    "Oil: ~$93 after the Gulf strikes",
    "tankers burning in the strait",
    "India wholesale inflation: 12.29%",
    "a four-year high, October data",
    "UK inflation: 3.6%",
    "energy cap seen +26% in January",
]

WEATHER_TEXT = (
    "Cyclone Akvan is strengthening over the Bay of Bengal and tracking "
    "for the Andhra Pradesh\u2013Odisha coast. Landfall is expected Friday; "
    "Odisha has begun evacuations and shut schools along the coast. "
    "Elsewhere: heavy rain floods South Florida, and a major storm "
    "brings a travel ban to New York."
)

SCIENCE_LINES = [
    "Voyager 1 reaches one light-day from Earth \u2014 a full day for its "
    "signal to come home.",
    "GPT-6.2 Astra & Sol: OpenAI's new flagships land with lower API "
    "prices.",
    "The farthest human-made object has now travelled some 16 billion "
    "miles.",
]

PREVIEW_LINES = [
    "First Trump\u2013Xi\u2013Putin trilateral summit convenes in Shenzhen.",
    "Akvan landfall watch: the Andhra\u2013Odisha coast braces for Friday.",
    "COP31 fossil-fuel draft fight resumes in Antalya.",
]

DATE_CHECK = ("DATE CHECK \u2014 EVERY STORY FIRST REPORTED ON WEDNESDAY "
              "18 NOVEMBER 2026 \u00b7 LATER STORIES DELIBERATELY EXCLUDED")

# World-map pins: (story number, longitude, latitude)
PINS = [
    (1, 56.5, 26.5),      # the Gulf / Hormuz
    (2, 114.1, 22.5),     # Shenzhen
    (3, -152.0, 64.0),    # Alaska
    (4, -122.0, 37.4),    # Silicon Valley
    (5, 36.6, 45.3),      # Kerch Bridge
    (7, 23.5, -0.5),      # DR Congo
    (8, 4.35, 50.85),     # Brussels
    (10, 80.3, 15.9),     # Andhra coast
    (11, 34.3, 31.4),     # Gaza
    (13, 70.5, 34.5),     # eastern Afghanistan
    (15, 77.2, 28.6),     # Delhi
    (16, 121.0, 14.6),    # Manila
]

# Land as unions of (lon0, lon1, lat0, lat1) rectangles: crude shapes
# are fine at dot-matrix scale.
LAND_RECTS = [
    # North America
    (-168, -140, 58, 70), (-140, -115, 48, 72), (-115, -95, 42, 72),
    (-95, -80, 42, 70), (-125, -105, 32, 49), (-105, -90, 30, 49),
    (-90, -75, 25, 47), (-80, -73, 32, 42), (-85, -80, 25, 31),
    (-102, -97, 26, 33), (-118, -105, 23, 32), (-105, -90, 14, 24),
    (-90, -78, 7, 15),
    # South America
    (-79, -66, 0, 11), (-75, -60, -10, 5), (-66, -50, -20, 0),
    (-60, -48, -33, -15), (-73, -62, -35, -20), (-70, -65, -45, -35),
    (-73, -68, -54, -45), (-77, -70, -18, -5), (-81, -75, -5, 1),
    # Africa
    (-17, 35, 16, 32), (20, 35, 12, 28), (35, 43, 12, 20),
    (-17, -10, 4, 16), (-10, 10, -5, 5), (10, 30, -12, 3),
    (40, 51, 5, 12), (35, 42, -15, -2), (25, 36, -27, -15),
    (17, 33, -35, -27), (12, 20, -18, -10), (43, 50, -25, -12),
    # Europe
    (-10, 0, 43, 50), (0, 10, 46, 54), (-6, -1, 50, 58),
    (5, 18, 54, 60), (5, 15, 58, 65), (15, 31, 64, 71),
    (18, 32, 54, 60), (10, 20, 40, 47), (20, 30, 38, 48),
    (28, 45, 45, 55),
    # Asia
    (30, 60, 55, 68), (60, 100, 50, 70), (100, 140, 55, 72),
    (140, 180, 60, 70), (160, 180, 52, 60), (140, 160, 45, 55),
    (120, 142, 35, 50), (105, 122, 22, 35), (122, 132, 30, 42),
    (126, 130, 34, 40), (100, 108, 5, 20), (95, 105, 15, 28),
    (68, 80, 8, 22), (68, 89, 20, 28), (88, 97, 21, 29),
    (35, 55, 12, 30), (48, 63, 25, 35), (50, 80, 35, 48),
    (26, 45, 36, 42),
    # Japan
    (130, 137, 31, 34), (137, 141, 34, 37), (140, 142, 36, 40),
    (141, 143, 40, 44),
    # Indonesia
    (95, 105, -4, 6), (109, 119, -3, 7), (105, 114, -8, -6),
    (119, 125, -5, 1), (131, 147, -8, -1),
    # Australia & New Zealand
    (113, 124, -22, -14), (124, 136, -26, -12), (136, 147, -20, -12),
    (113, 118, -35, -26), (118, 130, -35, -30), (130, 140, -38, -30),
    (140, 150, -39, -28), (145, 148, -43, -40),
    (167, 174, -45, -41), (174, 178, -41, -37),
]


# ------------------------------------------------------- Hormuz inset map

def _star(cx, cy, r_out, r_in, spikes=12):
    pts = []
    for i in range(2 * spikes):
        r = r_out if i % 2 == 0 else r_in
        a = math.pi * i / spikes - math.pi / 2
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def draw_map(draw, x, y, w, h):
    """A simple stylised map of the Strait of Hormuz, drawn with shapes."""
    draw.rectangle([x, y, x + w, y + h], fill=SEA)
    # Iran: the northern shore, across the top and down the right side.
    iran = [
        (x + w * 0.30, y), (x + w, y), (x + w, y + h * 0.40),
        (x + w * 0.86, y + h * 0.44), (x + w * 0.74, y + h * 0.34),
        (x + w * 0.60, y + h * 0.40), (x + w * 0.47, y + h * 0.28),
        (x + w * 0.34, y + h * 0.20),
    ]
    draw.polygon(iran, fill=LAND)
    # Arabia: the southern shore, bottom-left.
    arabia = [
        (x, y + h), (x, y + h * 0.58), (x + w * 0.13, y + h * 0.52),
        (x + w * 0.24, y + h * 0.62), (x + w * 0.33, y + h * 0.76),
        (x + w * 0.38, y + h),
    ]
    draw.polygon(arabia, fill=LAND)
    # Qeshm Island, in the strait at the right.
    qx, qy = x + w * 0.76, y + h * 0.52
    island = [
        (qx - w * 0.075, qy - h * 0.045), (qx + w * 0.055, qy - h * 0.06),
        (qx + w * 0.085, qy + h * 0.01), (qx + w * 0.01, qy + h * 0.055),
        (qx - w * 0.06, qy + h * 0.04),
    ]
    draw.polygon(island, fill=LAND)
    # The explosion at the island's launch site.
    draw.polygon(_star(qx, qy, 13, 5), fill=BLAST, outline=(120, 40, 0))
    # Labels.
    lab = sans_bold(11)
    small = sans_bold(9)
    draw.text((x + w * 0.60, y + h * 0.08), "IRAN", font=lab, fill=INK)
    draw.text((x + w * 0.07, y + h * 0.28), "GULF", font=lab,
              fill=(255, 255, 255))
    draw.text((qx - w * 0.17, qy + h * 0.14), "QESHM ISLAND", font=small,
              fill=(255, 255, 255))
    draw.text((x + w * 0.44, y + h * 0.84), "STRAIT OF HORMUZ", font=small,
              fill=(255, 255, 255))
    draw.rectangle([x, y, x + w, y + h], outline=INK, width=2)


# --------------------------------------------------------- world dot map

def _is_land(lon, lat):
    for lon0, lon1, lat0, lat1 in LAND_RECTS:
        if lon0 <= lon <= lon1 and lat0 <= lat <= lat1:
            return True
    return False


def draw_world_map(draw, x, y, w, h):
    """Dot-matrix world map: a grid of dots where land rectangles fall,
    with numbered red pins for the top stories."""
    lon_lo, lon_hi = -170.0, 185.0
    lat_hi, lat_lo = 82.0, -62.0
    pitch = 4
    cols = int(w // pitch)
    rows = int(h // pitch)
    for r in range(rows):
        lat = lat_hi - (r + 0.5) * (lat_hi - lat_lo) / rows
        for c in range(cols):
            lon = lon_lo + (c + 0.5) * (lon_hi - lon_lo) / cols
            if _is_land(lon, lat):
                cx = x + (c + 0.5) * pitch
                cy = y + (r + 0.5) * pitch
                draw.ellipse([cx - 1.3, cy - 1.3, cx + 1.3, cy + 1.3],
                             fill=NAVY)
    draw.rectangle([x, y, x + w, y + h], outline=INK, width=1)
    num_font = sans_bold(7)
    for num, lon, lat in PINS:
        px = x + (lon - lon_lo) / (lon_hi - lon_lo) * w
        py = y + (lat_hi - lat) / (lat_hi - lat_lo) * h
        draw.ellipse([px - 5, py - 5, px + 5, py + 5], fill=RED,
                     outline=(255, 255, 255), width=1)
        label = str(num)
        tw = draw.textlength(label, font=num_font)
        draw.text((px - tw / 2, py - 4), label, font=num_font,
                  fill=(255, 255, 255))


# ------------------------------------------------------------------ page

def build_page():
    assert TOTAL_STORIES == 56, TOTAL_STORIES
    assert sum(REGION_COUNTS.values()) == TOTAL_STORIES
    canvas = Image.new("RGB", (W, H), PAPER)
    draw = ImageDraw.Draw(canvas)
    x0 = MARGIN
    x1 = W - MARGIN
    y = 14

    # 1. Masthead: title left, date right, red strapline under.
    draw.text((x0, y), "THE WORLD IN ONE DAY", font=serif(26), fill=INK)
    date = "WEDNESDAY \u00b7 18 NOVEMBER 2026"
    date_font = sans_bold(12)
    dw = draw.textlength(date, font=date_font)
    draw.text((x1 - dw, y + 10), date, font=date_font, fill=INK)
    y += 30
    strap = (f"{TOTAL_STORIES} STORIES \u00b7 7 REGIONS \u00b7 EVERY STORY "
             f"FIRST REPORTED ON WEDNESDAY \u00b7 DATE-CHECKED")
    draw.text((x0, y), strap, font=sans_bold(11), fill=RED)
    y += 15
    draw.line([x0, y, x1, y], fill=RULE, width=2)
    y += 5

    # 2. DAY IN NUMBERS band.
    draw.text((x0, y), "THE DAY IN NUMBERS", font=sans_bold(9), fill=RED)
    y += 11
    box_w = (CW - 5 * 8) // 6
    box_h = 44
    num_font = serif(15)
    cap_font = sans(8)
    for i, (figure, caption) in enumerate(NUMBERS):
        bx = x0 + i * (box_w + 8)
        draw.rectangle([bx, y, bx + box_w, y + box_h], outline=INK, width=1)
        draw.text((bx + 6, y + 3), figure, font=num_font, fill=INK)
        cap_lines = truncate_lines(draw, caption, cap_font, box_w - 12, 2)
        for j, line in enumerate(cap_lines):
            draw.text((bx + 6, y + 22 + j * 10), line, font=cap_font,
                      fill=BODY_INK)
    y += box_h + 6

    # 3. Region band (navy strip; counts computed from the story data).
    band = " \u00b7 ".join(f"{r} {REGION_COUNTS[r]}" for r in REGION_ORDER)
    draw.rectangle([x0, y, x1, y + 17], fill=NAVY)
    band_font = sans_bold(10)
    bw = draw.textlength(band, font=band_font)
    draw.text(((W - bw) / 2, y + 3), band, font=band_font,
              fill=(255, 255, 255))
    y += 17 + 5

    # 4. Lead story: text left, Hormuz map right.
    lead_top = y
    map_w, map_h = 340, 98
    map_x = x1 - map_w
    text_w = CW - map_w - 14
    draw.text((x0, y), f"1 \u00b7 {LEAD_LABEL}", font=sans_bold(10), fill=RED)
    y += 12
    head_lines = truncate_lines(draw, LEAD_HEADLINE, serif(20), text_w, 2)
    for line in head_lines:
        draw.text((x0, y), line, font=serif(20), fill=INK)
        y += 22
    body_font = sans(10)
    cap_font_lead = serif(40)
    cap_w = int(draw.textlength(LEAD_BODY[0], font=cap_font_lead)) + 7
    draw.text((x0, y - 4), LEAD_BODY[0], font=cap_font_lead, fill=RED)
    widths = [text_w - cap_w] * 3 + [text_w]
    body_lines = wrap_variable(draw, LEAD_BODY[1:], body_font, widths)
    for i, line in enumerate(body_lines):
        lx = x0 + cap_w if i < 3 else x0
        draw.text((lx, y), line, font=body_font, fill=BODY_INK)
        y += 12
    draw_map(draw, map_x, lead_top, map_w, map_h)
    y = lead_top + map_h + 5
    draw.line([x0, y, x1, y], fill=RULE, width=3)
    y += 5

    # 5. Hero cards (stories 2-4).
    hero_w = (CW - 2 * 14) // 3
    for i, (label, headline, body, _region) in enumerate(HEROES):
        hx = x0 + i * (hero_w + 14)
        draw.text((hx, y), f"{i + 2} \u00b7 {label}", font=sans_bold(8),
                  fill=RED)
        head_lines = truncate_lines(draw, headline, serif(12), hero_w, 2)
        for j, line in enumerate(head_lines):
            draw.text((hx, y + 10 + j * 13), line, font=serif(12), fill=INK)
        body_lines = truncate_lines(draw, body, sans(8), hero_w, 2)
        for j, line in enumerate(body_lines):
            draw.text((hx, y + 37 + j * 10), line, font=sans(8),
                      fill=BODY_INK)
    y += 58
    draw.line([x0, y, x1, y], fill=RULE, width=1)
    y += 5

    # 6. World map + MARKETS + WEATHER WATCH row.
    row_top = y
    draw.text((x0, y), "WHERE IT HAPPENED", font=sans_bold(9), fill=RED)
    draw_world_map(draw, x0, y + 11, 470, 96)
    for bx, bw_, title, lines, is_text in (
        (506, 234, "MARKETS", MARKETS_LINES, False),
        (752, 248, "WEATHER WATCH", None, True),
    ):
        draw.rectangle([bx, row_top, bx + bw_, row_top + 107],
                       outline=INK, width=1)
        draw.text((bx + 7, row_top + 5), title, font=sans_bold(10),
                  fill=RED)
        if is_text:
            wlines = wrap_text(draw, WEATHER_TEXT, sans(8), bw_ - 14)
            for j, line in enumerate(wlines):
                draw.text((bx + 7, row_top + 19 + j * 10), line,
                          font=sans(8), fill=BODY_INK)
        else:
            for j, line in enumerate(lines):
                draw.text((bx + 7, row_top + 19 + j * 10), line,
                          font=sans(8), fill=BODY_INK)
    y = row_top + 107 + 5

    # 7. Timeline: one line, label then four segments.
    draw.line([x0, y, x1, y], fill=RULE, width=1)
    y += 4
    tl_label = "THE DAY BY THE CLOCK \u2014 UTC"
    tl_font = sans_bold(9)
    draw.text((x0, y), tl_label, font=tl_font, fill=RED)
    seg_x = x0 + int(draw.textlength(tl_label, font=tl_font)) + 14
    seg_w = (x1 - seg_x) // 4
    for i, (period, item) in enumerate(TIMELINE):
        sx = seg_x + i * seg_w
        pw = draw.textlength(period, font=serif(10))
        draw.text((sx, y), period, font=serif(10), fill=INK)
        seg_text = truncate_lines(draw, "\u00b7 " + item, sans(8),
                                  seg_w - pw - 6, 1)[0]
        draw.text((sx + pw + 4, y + 1), seg_text, font=sans(8),
                  fill=BODY_INK)
    y += 14
    draw.line([x0, y, x1, y], fill=RULE, width=2)
    y += 5

    # 8. Story grid: 12 cards (rows of 4, taller) then 40 briefs.
    grid_top = y
    gutter = 12
    col_w = (CW - 3 * gutter) // 4
    col_xs = [x0 + i * (col_w + gutter) for i in range(4)]

    def draw_grid_card(idx, story, cx, cy):
        label, headline, body, _region = story
        draw.text((cx, cy), f"{idx} \u00b7 {label}", font=sans_bold(8),
                  fill=RED)
        head_lines = truncate_lines(draw, headline, serif(12), col_w, 2)
        for j, line in enumerate(head_lines):
            draw.text((cx, cy + 10 + j * 13), line, font=serif(12),
                      fill=INK)
        body_lines = truncate_lines(draw, body, sans(8), col_w, 2)
        for j, line in enumerate(body_lines):
            draw.text((cx, cy + 37 + j * 10), line, font=sans(8),
                      fill=BODY_INK)

    def draw_brief(idx, brief, cx, cy):
        headline, body, _region = brief
        head_lines = truncate_lines(draw, f"{idx}. {headline}",
                                    sans_bold(9), col_w, 2)
        for j, line in enumerate(head_lines):
            draw.text((cx, cy + j * 11), line, font=sans_bold(9), fill=INK)
        body_line = truncate_lines(draw, body, sans(8), col_w, 1)[0]
        draw.text((cx, cy + 21), body_line, font=sans(8), fill=BODY_INK)

    card_row_h = 57
    for row in range(3):
        for col in range(4):
            k = row * 4 + col
            draw_grid_card(5 + k, CARDS[k], col_xs[col], y)
        y += card_row_h
        draw.line([x0, y - 3, x1, y - 3], fill=HAIR, width=1)
    brief_row_h = 31
    for row in range(10):
        for col in range(4):
            k = row * 4 + col
            draw_brief(17 + k, BRIEFS[k], col_xs[col], y)
        y += brief_row_h
        if row < 9:
            draw.line([x0, y - 2, x1, y - 2], fill=HAIR, width=1)
    # Light vertical rules between the grid columns, so the dense
    # four-column grid scans column by column like a broadsheet.
    for i in range(1, 4):
        vx = col_xs[i] - gutter // 2
        draw.line([vx, grid_top, vx, y - 2], fill=HAIR, width=1)
    draw.line([x0, y, x1, y], fill=RULE, width=2)
    y += 5

    # 9. SCIENCE & SPACE + THURSDAY PREVIEW boxes.
    box_w2 = (CW - 12) // 2
    for bx, title, lines in (
        (x0, "SCIENCE & SPACE", SCIENCE_LINES),
        (x0 + box_w2 + 12, "THURSDAY PREVIEW", PREVIEW_LINES),
    ):
        draw.rectangle([bx, y, bx + box_w2, y + 48], outline=INK, width=1)
        draw.text((bx + 7, y + 4), title, font=sans_bold(10), fill=RED)
        for j, line in enumerate(lines):
            draw.text((bx + 7, y + 18 + j * 10), line, font=sans(8),
                      fill=BODY_INK)
    y += 48 + 5

    # 10. DATE CHECK footer: red band, white text.
    draw.rectangle([x0, y, x1, y + 24], fill=RED)
    foot_font = sans_bold(9)
    fw = draw.textlength(DATE_CHECK, font=foot_font)
    draw.text(((W - fw) / 2, y + 7), DATE_CHECK, font=foot_font,
              fill=(255, 255, 255))
    y += 24

    print(f"layout: content ends at y={y} of {H}")
    return canvas


def main():
    page = build_page()
    buf = io.BytesIO()
    page.save(buf, format="PNG", optimize=True)
    data = buf.getvalue()
    if len(data) > MAX_BYTES:
        raise SystemExit(f"entry.png would be {len(data)} bytes "
                         f"(> {MAX_BYTES})")
    out = ROOT / "entry.png"
    out.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    print(f"entry.png: {len(data)} bytes, format PNG, sha256 {digest}")


if __name__ == "__main__":
    main()
