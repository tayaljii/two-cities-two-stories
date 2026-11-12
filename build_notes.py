#!/usr/bin/env python3
"""Generate speaker-notes.md from the deck's data-notes attributes (single source of truth)."""
import re, html, os

ROOT = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(ROOT, "present.html"), encoding="utf-8").read()

# Slide titles in deck order (used as headings)
titles = [
    "Opening — Two Cities. Two Stories.",
    "The Journey — From the Gangetic Plain to the High Himalaya",
    "Roorkee — From a Small Village to an Engineering City",
    "Roorkee — The Solani Aqueduct: Water Flows Over Water",
    "Roorkee — The Engineering Legacy (College → IIT)",
    "Roorkee — Culture & Places Around",
    "Joshimath — Gateway to the Himalayas",
    "Joshimath — Ancient Heritage & Spiritual Identity",
    "Joshimath — Beyond the Town (Destinations)",
    "Joshimath — When the Mountains Send a Warning",
    "Two Cities, Two Relationships with Nature",
    "What Makes Our Cities Special?",
    "Closing — One Uttarakhand",
    "Sources & Image Credits (not presented)",
]
speakers = [
    "Om + Saloni", "Om + Saloni", "Om", "Om", "Om", "Om",
    "Saloni", "Saloni", "Saloni", "Saloni", "Om + Saloni", "Om + Saloni", "Om + Saloni", "—",
]

pat = re.compile(r'<section class="slide [^"]*" data-speaker="([^"]*)"\s+data-notes="([^"]*)"(?:\s+data-speaker-notes-time="([^"]*)")?', re.S)
meta = pat.findall(src)
assert len(meta) == 14, f"expected 14 slides, got {len(meta)}"

out = ["# Speaker Notes — Two Cities. Two Stories.",
       "",
       "Presented by **Om Tayal** (Roorkee) and **Saloni** (Joshimath). Target total: ~10–12 minutes.",
       "",
       "> These notes are also embedded in the PPTX (View → Notes Page) and available live in the browser deck by pressing **N**.",
       ""]
total = 0.0
for i, ((sp, notes, t), title) in enumerate(zip(meta, titles), 1):
    body = html.unescape(notes)
    tmatch = re.search(r'Time:\s*~?(\d+):(\d+)s?|Time:\s*~?(\d+)s', body)
    secs = 0
    if tmatch:
        secs = (int(tmatch.group(1)) * 60 + int(tmatch.group(2))) if tmatch.group(3) is None else int(tmatch.group(3))
    else:
        secs = 0
    t = "~%ds" % secs
    total += secs
    out += [f"## Slide {i} — {title}", "", f"**Presenters:** {html.unescape(sp)}  ·  **Suggested time:** {t or '—'}", "", body.replace(" | ", "\n\n"), "", "---", ""]
out += [f"**Total suggested time:** ~{total/60:.1f} minutes.",
        "",
        "## Balance check",
        "- Om (Roorkee): slides 1–2 (intro), 3–6 (Roorkee chapter) — ~4.5 min",
        "- Saloni (Joshimath): slides 1–2 (intro), 7–10 (Joshimath chapter) — ~4.5 min",
        "- Together: slide 2 handover, slide 11 comparison, 12 personal, 13 closing — ~2.5 min",
        ""]
open(os.path.join(ROOT, "speaker-notes.md"), "w", encoding="utf-8").write("\n".join(out))
print("Wrote speaker-notes.md; total suggested time ~%.1f min" % (total / 60))
