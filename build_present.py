#!/usr/bin/env python3
"""Build a self-contained present.html (single file, base64-inlined images)
with a VoxDeck-inspired motion layer: Ken Burns drift on photographs,
directional wipe reveals, and overshoot (bounce) entrances.

Source of truth: present.html in this folder. Output goes to the
"Two Cities. Two Stories. Roorkee & Joshimath" sibling folder so it can be
run standalone from anywhere. The original VoxDeck stub is preserved as
present_original_voxdeck.html.
"""
import base64, os, re, shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(os.path.dirname(ROOT), "Two Cities. Two Stories. Roorkee & Joshimath")
OUT = os.path.join(OUT_DIR, "present.html")

MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
        ".webp": "image/webp", ".gif": "image/gif", ".svg": "image/svg+xml"}

src = open(os.path.join(ROOT, "present.html"), encoding="utf-8").read()

# ---- 1. Inline every assets/ reference (img src and CSS url()) as a data URI ----
def data_uri(name):
    path = os.path.join(ROOT, "assets", name)
    ext = os.path.splitext(name)[1].lower()
    b64 = base64.b64encode(open(path, "rb").read()).decode("ascii")
    return f"data:{MIME.get(ext, 'application/octet-stream')};base64,{b64}"

refs = sorted(set(re.findall(r"assets/([A-Za-z0-9_.-]+)", src)))
missing = [r for r in refs if not os.path.exists(os.path.join(ROOT, "assets", r))]
if missing:
    raise SystemExit(f"missing assets: {missing}")
for name in refs:
    src = src.replace(f"assets/{name}", data_uri(name))
print(f"inlined {len(refs)} assets")

# ---- 2. VoxDeck-inspired motion layer (appended last so it layers on top) ----
FX = """
<style id="voxdeck-fx">
/* ===== VoxDeck-style motion layer (build_present.py) =====
   Ideas taken from the VoxDeck player's effect vocabulary:
   directional wipes, Ken Burns pan/zoom on photos, fade + bounce entrances. */

/* Ken Burns: slow, calm pan/zoom on every photograph while its slide is up */
.slide.active .hero-strip img, .slide.active .half img,
.slide.active .close-strip img, .slide.active .cmp-img img,
.slide.active .photo-frame img, .slide.active .full-bleed img {
  animation: kbDrift 26s ease-in-out infinite alternate;
}
@keyframes kbDrift {
  from { transform: scale(1.03) translate(0, 0); }
  to   { transform: scale(1.11) translate(-1.4%, 1.1%); }
}

/* Directional wipe reveal on the big photo strips */
.slide.visible .hero-strip, .slide.visible .close-strip,
.slide.visible .cmp-img, .slide.visible .photo-frame {
  animation: wipeIn 1.15s cubic-bezier(.72,0,.18,1) both;
}
@keyframes wipeIn {
  from { clip-path: inset(0 100% 0 0); }
  to   { clip-path: inset(0 0 0 0); }
}

/* Overshoot (bounce) entrance on scaled cards + stat chips */
.slide.visible .scale-in { animation: popIn .95s cubic-bezier(.22,1.38,.36,1) both; }
@keyframes popIn {
  from { opacity: 0; transform: scale(.94) translateY(12px); }
  to   { opacity: 1; transform: none; }
}

/* Gentle whole-slide rise on entry (VoxDeck fade-and-drift feel) */
.slide.active .slide-inner { animation: slideRise .9s cubic-bezier(.2,.8,.2,1) both; }
@keyframes slideRise {
  from { opacity: .35; transform: translateY(16px); }
  to   { opacity: 1; transform: none; }
}

@media (prefers-reduced-motion: reduce) {
  .slide.active .hero-strip img, .slide.active .half img,
  .slide.active .close-strip img, .slide.active .cmp-img img,
  .slide.active .photo-frame img, .slide.active .full-bleed img,
  .slide.visible .hero-strip, .slide.visible .close-strip,
  .slide.visible .cmp-img, .slide.visible .photo-frame,
  .slide.visible .scale-in, .slide.active .slide-inner { animation: none; }
}
</style>
"""
src = src.replace("</head>", FX + "</head>", 1)

# ---- 3. Write output; preserve the original VoxDeck stub ----
os.makedirs(OUT_DIR, exist_ok=True)
stub = os.path.join(OUT_DIR, "present.html")
if os.path.exists(stub) and b"voxdeck" not in open(stub, "rb").read(2048).lower():
    pass  # our own file from a previous run — safe to overwrite
orig = os.path.join(OUT_DIR, "present_original_voxdeck.html")
if not os.path.exists(orig) and os.path.exists(stub) and os.path.getsize(stub) < 5000:
    shutil.copy2(stub, orig)
    print("preserved original VoxDeck stub as present_original_voxdeck.html")
open(OUT, "w", encoding="utf-8").write(src)
print("Wrote", OUT, "(%.1f MB)" % (os.path.getsize(OUT) / 1e6))
