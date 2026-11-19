#!/usr/bin/env python3
"""Compose "THE WORLD IN ONE DAY": ONE 1024x1024 image summing up the
world's news of Wednesday 18 November 2026 as a dense broadsheet front
page — masthead, a lead story with a drawn map of the Strait of Hormuz,
36 compact story cards in three columns, a timeline strip, an ALSO TODAY
band and a footer line.

Style: cream paper #F7F2E4, black serif headlines, red #B01E24 section
labels, thin black rules. Headlines in Liberation Serif Bold, body text
in Liberation Sans.

The output is deterministic: the same inputs always produce byte-identical
bytes. It is saved as PNG, or as JPEG (quality 90) if the PNG would exceed
1,000,000 bytes; either way the file is named entry.png in this directory.
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
RULE = (17, 17, 17)
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

LEAD_LABEL = "LEAD STORY \u2014 THE GULF"
LEAD_HEADLINE = "U.S. strikes Iran missile site; Iran answers at Kuwait & Bahrain"
LEAD_BODY = (
    "American jets hit a Revolutionary Guards launch site on Qeshm Island "
    "at the mouth of the Strait of Hormuz. Iran replied with drones and "
    "missiles at bases hosting U.S. forces in Kuwait and Bahrain, tankers "
    "burned in the strait and oil climbed towards $93 as mediators Oman "
    "and Qatar kept talking."
)

# (section label, headline, body)
STORIES = [
    ("SHENZHEN \u2014 APEC", "Xi & Putin open APEC, vow to fight protectionism",
     "China's and Russia's leaders met in Shenzhen and opened the APEC "
     "summit, a day before their first trilateral talks with President Trump."),
    ("UKRAINE WAR", "Kerch Bridge hit for a second day",
     "Part of the road span collapsed as Kyiv struck the Crimea bridge "
     "again; Moscow said its air defences downed over 1,400 Ukrainian "
     "drones overnight."),
    ("WASHINGTON", "Peltola flips Alaska: Senate 56\u201344",
     "Democrat Mary Peltola beat Republican incumbent Dan Sullivan, "
     "sealing a projected 56\u201344 Democratic majority in the incoming Senate."),
    ("SPACE", "Voyager 1 reaches one light-day",
     "NASA's 1977 probe crossed one light-day from Earth \u2014 some 16 billion "
     "miles \u2014 a full day for its signal to come home. No human-made object "
     "has gone farther."),
    ("HEALTH", "Ebola tops 11,000; U.S. loses measles status",
     "Congo's Ebola outbreak passed 11,000 cases, and the United States "
     "lost its measles-elimination status after 26 years."),
    ("EUROPE", "EU proposes \u20ac45bn loan for Ukraine",
     "Brussels proposed a \u20ac45 billion loan for Kyiv in 2027, with the "
     "budget signed off alongside an EU\u2013Indonesia trade deal."),
    ("TECHNOLOGY", "Nvidia doubles revenue to $115.8bn",
     "A record quarter, up 103% on the year, as the board declined to "
     "reinstate Jensen Huang as chief executive."),
    ("TECHNOLOGY", "OpenAI launches GPT-6.2 Astra and Sol",
     "New flagship models arrived with lower API prices, intensifying the "
     "price war among AI labs."),
    ("INDIA \u2014 WEATHER", "Cyclone Akvan strengthens towards Andhra",
     "The severe storm is due to cross the Andhra Pradesh coast on Friday; "
     "Odisha has begun large-scale evacuations and shut schools."),
    ("GAZA", "Board of Peace faults both sides",
     "Trump's Board of Peace faulted Israel and Hamas over the ceasefire "
     "as reconstruction stalled and winter approached."),
    ("ISRAEL", "Knesset elects Kahana as speaker",
     "Matan Kahana's election was read as an early win for prime "
     "minister-elect Eisenkot's incoming government."),
    ("GAZA \u2014 AID", "950,000 displaced on flood-prone ground",
     "The WHO warned that 950,000 displaced Gazans are camped on ground "
     "prone to flooding as winter comes."),
    ("MYANMAR", "Junta to review ties with ASEAN",
     "Myanmar's military government said it would review its ties with "
     "the ASEAN bloc."),
    ("WASHINGTON", "Democrats nominate Jeffries for speaker",
     "House Democrats picked Hakeem Jeffries as their nominee for "
     "speaker, 251 votes to 11."),
    ("UNITED STATES", "Jesse Jackson dies at 84",
     "The civil rights leader and two-time presidential candidate died "
     "aged 84."),
    ("UNITED STATES", "Outages 'not an attack', Congress told",
     "Security officials said the week's outages were no attack, but "
     "warned Iran keeps probing U.S. water, energy and banking systems; "
     "the FAA chief took blame for the ground stop."),
    ("UNITED STATES", "Floods in Florida, boil-water in Carolina",
     "Up to 15 inches of rain flooded South Florida while 240,000 people "
     "in South Carolina were told to boil their water."),
    ("AMERICAS", "U.S. signs military pact with Venezuela",
     "Washington signed a military pact with Caracas as the administration "
     "touted its 'Donroe Doctrine' for the hemisphere."),
    ("MEXICO", "President calls for calm after cartel leader's death",
     "Cartel violence erupted across several states after the death of "
     "the leader known as El Mencho."),
    ("AFRICA", "Chad closes its border with Sudan",
     "Chad shut the frontier as tensions between Sudan and Ethiopia "
     "escalated, each accusing the other of backing armed groups."),
    ("AFGHANISTAN", "Earthquake kills more than 600",
     "A powerful quake struck eastern Afghanistan, killing over 600 "
     "people and flattening villages."),
    ("PAKISTAN", "Building explosion toll rises to 16",
     "The death toll from a building explosion climbed to 16 as rescuers "
     "searched the rubble."),
    ("IRAN", "Army helicopter crashes in Isfahan",
     "Four people died when an Iranian army helicopter crashed in Isfahan "
     "province."),
    ("CLIMATE", "COP31 splits over fossil-fuel draft",
     "Talks in T\u00fcrkiye turned contentious after an 18-page draft called "
     "for a fossil-fuel phase-out and net zero in wealthy countries by 2030."),
    ("BRITAIN", "Inflation rises to 3.6%",
     "UK inflation climbed to 3.6% as forecasts pointed to a 26% jump in "
     "the January energy price cap."),
    ("BRITAIN", "Burnham: Brexit has not worked",
     "Prime Minister Andy Burnham said Brexit had not delivered, ahead of "
     "a reset summit with the EU."),
    ("FRANCE", "Russia accuses Paris over Ukraine mission",
     "Moscow accused France of direct involvement in the war after "
     "reports of French personnel in Ukraine; Paris rejected the claims, "
     "and Marine Le Pen proposed cutting the retirement age."),
    ("MIDDLE EAST", "Australia and UK sanction settlement firms",
     "Canberra and London announced coordinated sanctions on people and "
     "companies behind Israeli settlement expansion in the West Bank."),
    ("ASIA", "India and Japan hold 2+2 in Tokyo",
     "Defence and foreign ministers met in Tokyo for the fourth "
     "India\u2013Japan 2+2 dialogue."),
    ("INDIA \u2014 ECONOMY", "Wholesale inflation at a four-year high",
     "India's wholesale price inflation rose to 12.29% in October, the "
     "highest in four years."),
    ("ASIA \u2014 QUAD", "Quad leaders unveil plan in Manila",
     "Quad leaders announced a new plan in Manila as President Trump "
     "arrived for talks before flying on to Shenzhen."),
    ("KOREA", "Lee uses APEC to court Beijing",
     "South Korea's President Lee Jae Myung used the APEC gathering to "
     "strengthen relations with China."),
    ("VATICAN", "Pope ends 12-day South America tour",
     "Pope Leo XIV bid 'hasta luego' to Peru, his second homeland, after "
     "a marathon tour that followed his lung-cancer surgery."),
    ("COSTA RICA", "Journalist shot dead in San Jos\u00e9",
     "Camilo Rodr\u00edguez, known for reporting on traffickers and "
     "politicians, was shot dead \u2014 the first such killing in 25 years."),
    ("NIGERIA", "Senate moves against sponsors of violence",
     "Nigeria's Senate pushed to disqualify candidates who sponsor "
     "political violence, as the government froze hiring across federal "
     "agencies."),
    ("SPORT", "Dhoni retires from the IPL",
     "India's former captain MS Dhoni announced his retirement from the "
     "Indian Premier League."),
]

TIMELINE = [
    ("Morning", "APEC opens in Shenzhen; Xi\u2013Putin talks begin"),
    ("Midday", "Second day of strikes on the Kerch Bridge"),
    ("Evening", "Nvidia posts its record quarter"),
    ("Night", "Cyclone Akvan strengthens over the Bay of Bengal"),
]

ALSO_TODAY = [
    "New York orders a travel ban as a major storm hits the U.S. East",
    "Russia to equip new nuclear submarines with hypersonic missiles",
    "German president Steinmeier to visit the Beirut blast site",
    "GTA VI launches at midnight, region by region",
]

FOOTER = ("40 stories \u00b7 7 regions \u00b7 every story first reported on "
          "Wednesday 18 November 2026 \u00b7 date-checked")


# ------------------------------------------------------------------- map

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
    draw.polygon(_star(qx, qy, 15, 6), fill=BLAST, outline=(120, 40, 0))
    # Labels.
    lab = sans_bold(12)
    small = sans_bold(10)
    draw.text((x + w * 0.60, y + h * 0.10), "IRAN", font=lab, fill=INK)
    draw.text((x + w * 0.07, y + h * 0.30), "GULF", font=lab,
              fill=(255, 255, 255))
    draw.text((qx - w * 0.16, qy + h * 0.13), "QESHM ISLAND", font=small,
              fill=(255, 255, 255))
    draw.text((x + w * 0.47, y + h * 0.82), "STRAIT OF HORMUZ", font=small,
              fill=(255, 255, 255))
    draw.rectangle([x, y, x + w, y + h], outline=INK, width=2)


# ------------------------------------------------------------------ cards

LABEL_SIZE = 10
LABEL_LH = 12


def card_plan(draw, story, col_w, head_size, body_size, body_cap):
    """Measure one card: returns (label, head_lines, body_lines, height)."""
    label, headline, body = story
    head_font = serif(head_size)
    head_lines = wrap_text(draw, headline, head_font, col_w)
    while len(head_lines) > 2 and head_size > 12:
        head_size -= 1
        head_font = serif(head_size)
        head_lines = wrap_text(draw, headline, head_font, col_w)
    if len(head_lines) > 2:
        head_lines = truncate_lines(draw, headline, head_font, col_w, 2)
    body_font = sans(body_size)
    full_body = wrap_text(draw, body, body_font, col_w)
    if len(full_body) > body_cap:
        body_lines = truncate_lines(draw, body, body_font, col_w, body_cap)
    else:
        body_lines = full_body
    head_lh = head_size + 2
    body_lh = body_size + 3
    height = (LABEL_LH + len(head_lines) * head_lh
              + len(body_lines) * body_lh)
    return {
        "label": label, "head_lines": head_lines, "body_lines": body_lines,
        "body": body, "full_body": full_body, "head_size": head_size,
        "body_size": body_size, "head_lh": head_lh, "body_lh": body_lh,
        "height": height,
    }


def plan_grid(draw, col_w, avail_h):
    """Pick font sizes / body caps so the 12 rows fit avail_h, then spend
    any leftover height on extra body lines."""
    rows = [STORIES[i:i + 3] for i in range(0, len(STORIES), 3)]
    configs = [
        (15, 12, 3), (15, 12, 2), (15, 11, 2), (14, 11, 2),
        (14, 11, 1), (14, 10, 1), (13, 10, 1),
    ]
    chosen = None
    for head_size, body_size, cap in configs:
        plans = [[card_plan(draw, s, col_w, head_size, body_size, cap)
                  for s in row] for row in rows]
        total = sum(max(p["height"] for p in row) + 5 for row in plans)
        if total <= avail_h:
            chosen = (plans, total)
            break
    if chosen is None:  # tightest config, whatever it measures
        head_size, body_size, cap = configs[-1]
        plans = [[card_plan(draw, s, col_w, head_size, body_size, cap)
                  for s in row] for row in rows]
        total = sum(max(p["height"] for p in row) + 5 for row in plans)
        chosen = (plans, total)
    plans, total = chosen
    # Spend leftover height on extra body lines, row by row.
    leftover = avail_h - total
    for row in plans:
        row_h = max(p["height"] for p in row)
        for plan in row:
            while (len(plan["body_lines"]) < len(plan["full_body"])
                   and leftover >= plan["body_lh"]):
                n = len(plan["body_lines"]) + 1
                if n < len(plan["full_body"]):
                    plan["body_lines"] = truncate_lines(
                        draw, plan["body"], sans(plan["body_size"]),
                        col_w, n)
                else:
                    plan["body_lines"] = plan["full_body"]
                plan["height"] += plan["body_lh"]
                new_row_h = max(p["height"] for p in row)
                leftover -= max(0, new_row_h - row_h)
                row_h = new_row_h
    return plans


def draw_card(draw, plan, x, y, col_w):
    draw.text((x, y), plan["label"], font=sans_bold(LABEL_SIZE), fill=RED)
    ty = y + LABEL_LH
    head_font = serif(plan["head_size"])
    for line in plan["head_lines"]:
        draw.text((x, ty), line, font=head_font, fill=INK)
        ty += plan["head_lh"]
    body_font = sans(plan["body_size"])
    for line in plan["body_lines"]:
        draw.text((x, ty), line, font=body_font, fill=BODY_INK)
        ty += plan["body_lh"]


# ------------------------------------------------------------------ page

def build_page():
    canvas = Image.new("RGB", (W, H), PAPER)
    draw = ImageDraw.Draw(canvas)
    x0 = MARGIN
    x1 = W - MARGIN
    y = 16

    # 1. Masthead.
    draw.text((x0, y), "THE WORLD IN ONE DAY", font=serif(31), fill=INK)
    tag = "ALL THE NEWS OF ONE WEDNESDAY"
    tag_font = sans_bold(15)
    tw = draw.textlength(tag, font=tag_font)
    draw.text((x1 - tw, y + 12), tag, font=tag_font, fill=RED)
    y += 40
    draw.line([x0, y, x1, y], fill=RULE, width=2)
    y += 6

    # 2. Date line.
    date_font, date_size = fit_font(
        draw, "Wednesday 18 November 2026", serif, 56, 40, CW)
    draw.text((x0, y), "Wednesday 18 November 2026", font=date_font, fill=INK)
    y += date_size + 8

    # 3. Strapline.
    strap = ("Gulf escalation at Hormuz \u00b7 Xi and Putin open APEC in "
             "Shenzhen \u00b7 Ukraine strikes the Kerch Bridge again \u00b7 "
             "Voyager 1 reaches one light-day")
    strap_font, _ = fit_font(draw, strap, sans_bold, 15, 11, CW)
    draw.text((x0, y), strap, font=strap_font, fill=BODY_INK)
    y += 22
    draw.line([x0, y, x1, y], fill=RULE, width=1)
    y += 8

    # 4. Lead story: text left, map right.
    lead_top = y
    map_w, map_h = 356, 170
    map_x = x1 - map_w
    text_w = CW - map_w - 16
    draw.text((x0, y), LEAD_LABEL, font=sans_bold(13), fill=RED)
    y += 17
    head_lines = wrap_text(draw, LEAD_HEADLINE, serif(29), text_w)
    if len(head_lines) > 2:
        head_lines = truncate_lines(draw, LEAD_HEADLINE, serif(29),
                                    text_w, 2)
    for line in head_lines:
        draw.text((x0, y), line, font=serif(29), fill=INK)
        y += 33
    y += 2
    # Body with a drop cap: the first letter is set large in red serif,
    # and the first three lines are indented to flow around it.
    body_font = sans(13)
    cap_font = serif(46)
    cap_w = int(draw.textlength(LEAD_BODY[0], font=cap_font)) + 8
    draw.text((x0, y - 5), LEAD_BODY[0], font=cap_font, fill=RED)
    widths = [text_w - cap_w] * 3 + [text_w]
    body_lines = wrap_variable(draw, LEAD_BODY[1:], body_font, widths)
    for i, line in enumerate(body_lines):
        lx = x0 + cap_w if i < 3 else x0
        draw.text((lx, y), line, font=body_font, fill=BODY_INK)
        y += 17
    draw_map(draw, map_x, lead_top, map_w, map_h)
    y = lead_top + map_h + 8
    draw.line([x0, y, x1, y], fill=RULE, width=3)
    y += 8

    # Bottom sections are measured first so the grid gets what is left.
    also_text = "ALSO TODAY \u2014 " + " \u00b7 ".join(ALSO_TODAY)
    also_font = sans(13)
    also_lines = wrap_text(draw, also_text, also_font, CW - 20)
    also_h = len(also_lines) * 17 + 12
    timeline_h = 16 + 13 + 2 * 13 + 6
    footer_h = 16
    grid_avail = (H - 12 - footer_h - also_h - timeline_h - 14) - y

    # 5. Story grid: 12 rows x 3 columns.
    gutter = 14
    col_w = (CW - 2 * gutter) // 3
    col_xs = [x0, x0 + col_w + gutter, x0 + 2 * (col_w + gutter)]
    plans = plan_grid(draw, col_w, grid_avail)
    for row in plans:
        row_h = max(p["height"] for p in row)
        for plan, cx in zip(row, col_xs):
            draw_card(draw, plan, cx, y, col_w)
        y += row_h + 5
        draw.line([x0, y - 3, x1, y - 3], fill=(120, 115, 100), width=1)
    y += 2
    draw.line([x0, y, x1, y], fill=RULE, width=2)
    y += 6

    # 6. Timeline strip.
    draw.text((x0, y), "THE DAY BY THE CLOCK \u2014 UTC",
              font=sans_bold(12), fill=RED)
    y += 16
    seg_w = (CW - 3 * gutter) // 4
    seg_font = sans(11)
    for i, (period, item) in enumerate(TIMELINE):
        sx = x0 + i * (seg_w + gutter)
        draw.text((sx, y), period, font=serif(13), fill=INK)
        lines = truncate_lines(draw, item, seg_font, seg_w, 2)
        for j, line in enumerate(lines):
            draw.text((sx, y + 15 + j * 13), line, font=seg_font,
                      fill=BODY_INK)
    y += 15 + 2 * 13 + 6
    draw.line([x0, y, x1, y], fill=RULE, width=1)
    y += 6

    # 7. ALSO TODAY band.
    draw.rectangle([x0, y, x1, y + also_h], fill=INK)
    ty = y + 6
    for line in also_lines:
        draw.text((x0 + 10, ty), line, font=also_font, fill=PAPER)
        ty += 17
    y += also_h + 6

    # 8. Footer.
    foot_font = sans(11)
    fw = draw.textlength(FOOTER, font=foot_font)
    draw.text(((W - fw) / 2, y), FOOTER, font=foot_font, fill=BODY_INK)

    return canvas


def main():
    page = build_page()
    buf = io.BytesIO()
    page.save(buf, format="PNG", optimize=True)
    data = buf.getvalue()
    fmt = "PNG"
    if len(data) > MAX_BYTES:
        buf = io.BytesIO()
        page.save(buf, format="JPEG", quality=90, optimize=True)
        data = buf.getvalue()
        fmt = "JPEG"
    out = ROOT / "entry.png"
    out.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    print(f"entry.png: {len(data)} bytes, format {fmt}, sha256 {digest}")


if __name__ == "__main__":
    main()
