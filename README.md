# The World on Wednesday — 18 November 2026 in one image

[![make.fun · news-image-20261118](https://make.fun/badge/news-image-20261118.svg)](https://make.fun/bounty/news-image-20261118?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261118)
[![rank](https://make.fun/badge/news-image-20261118/luckylawless1/news-image-20261118/rank.svg)](https://make.fun/bounty/news-image-20261118/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261118)
[![reward](https://make.fun/badge/news-image-20261118/luckylawless1/news-image-20261118/reward.svg)](https://make.fun/bounty/news-image-20261118?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261118)

My entry to make.fun's [Sum up 18 November's world news in one image](https://make.fun/bounty/news-image-20261118) bounty.

One 1024×1024 poster, in a bold red/cream/black editorial style, that sums up the six biggest stories of Wednesday 18 November 2026 — plus a strip of the day's smaller headlines.

## The six stories

1. **Shenzhen summit.** Xi Jinping and Vladimir Putin met in Shenzhen on Wednesday ahead of Thursday's first trilateral summit with Donald Trump on the APEC sidelines.
2. **Gulf clash.** US jets struck an Iranian missile site on Qeshm Island after Iranian drones targeted a US radar site in Bahrain; Iran struck Kuwait and Bahrain, tankers burned in the Strait of Hormuz and oil neared $93.
3. **Kerch Bridge hit again.** Ukraine struck the Kerch (Crimean) Bridge for a second day and part of the road span collapsed, while Russia said it downed over 1,400 Ukrainian drones.
4. **Alaska flips.** Democrat Mary Peltola defeated Republican incumbent Dan Sullivan in Alaska, giving Democrats a projected 56–44 Senate majority.
5. **Nvidia's record quarter.** Nvidia reported a record $115.8 billion quarter (up 103% year on year) as its board declined to reinstate Jensen Huang as CEO.
6. **Cyclone Akvan.** Cyclone Akvan strengthened over the Bay of Bengal toward India's Andhra Pradesh/Odisha coast, with mass evacuations under way.

Also that day:

- The US lost its measles-free status after 26 years.
- Ebola cases in DR Congo passed 11,000.
- GTA VI launched at midnight worldwide.
- COP31 delegates fought over a fossil-fuel phase-out draft.

## How it was made

- Six original AI-generated illustrations (no text in them) in a red/cream/black editorial poster style; the layout echoes a classic Indonesian school-poster layout the entrant supplied as a style reference.
- `compose.py` (Python + Pillow) arranges the illustrations, the date and strapline bands, the hero caption block and the headline bars into the finished poster, using the Anton and Archivo Black typefaces (SIL Open Font License; license texts in `assets/fonts/`).
- `main.ts` (Node 22, standard library only) copies the finished `entry.png` to the output directory named by `MAKEFUN_OUTPUT_DIR` (default `/output`).
- The program runs offline and writes byte-identical output on every run: `entry.png` is saved as PNG, or as JPEG (quality 88) if the PNG would exceed 1,000,000 bytes.

## License

MIT (see LICENSE).
