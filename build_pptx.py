#!/usr/bin/env python3
"""Build the PowerPoint deck from slide screenshots + speaker notes parsed from present.html."""
import re, html, glob, os
from pptx import Presentation
from pptx.util import Inches, Emu
import zipfile, shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(ROOT, "present.html"), encoding="utf-8").read()

# Parse slides: data-speaker, data-notes, data-speaker-notes-time
pat = re.compile(
    r'<section class="slide ([^"]*)" data-speaker="([^"]*)"\s+data-notes="([^"]*)"(?:\s+data-speaker-notes-time="([^"]*)")?',
    re.S)
slides_meta = pat.findall(src)

def clean(s):
    s = s.replace(" | Extra context:", "\n\nEXTRA CONTEXT — ").replace(" | Transition:", "\n\nTRANSITION — ").replace(" | Time:", "\n\nTIME — ")
    return html.unescape(s).strip()

# Animated-build frames (3 stages per slide: background plate, mid-build, final).
# Stacked full-bleed + native PowerPoint timing XML => the slide assembles itself,
# mirroring the HTML deck's entrance animation (see timing injection below).
frames_dir = os.path.join(ROOT, "slide-frames")

def frames_for(n):  # n: 1-based slide number
    return [
        os.path.join(frames_dir, "slide_%02d_f1.jpg" % n),
        os.path.join(frames_dir, "slide_%02d_f2.jpg" % n),
        os.path.join(frames_dir, "slide_%02d_f3.png" % n),
    ]

assert len(slides_meta) >= 1 and all(os.path.exists(f) for f in frames_for(1)), \
    "run shoot_frames.js first: slide-frames/ must contain 3 frames per slide"

prs = Presentation()
# Exact standard 16:9 widescreen EMU values (12192000 x 6858000) — Keynote's
# importer rejects off-spec sizes / a mismatched sldSz type attribute.
prs.slide_width = Emu(12192000)
prs.slide_height = Emu(6858000)
blank = prs.slide_layouts[6]

for idx_meta, meta in enumerate(slides_meta, 1):
    _, speaker, notes, time = meta
    slide = prs.slides.add_slide(blank)
    for frame in frames_for(idx_meta):
        slide.shapes.add_picture(frame, 0, 0, width=prs.slide_width, height=prs.slide_height)
    tf = slide.notes_slide.notes_text_frame
    txt = clean(notes)
    if time:
        txt += f"\n\nSPEAKER(S): {html.unescape(speaker)}  ·  SUGGESTED TIME: {time}"
    tf.text = txt

out = os.path.join(ROOT, "Roorkee-Joshimath-Two-Cities-Two-Stories.pptx")
prs.save(out)

# Post-fix pipeline (Keeps PowerPoint happy, makes Keynote happy, adds motion):
# 1. python-pptx (on Python 3.15) writes duplicate zip entries for theme/master/layout
#    parts — dedupe them.
# 2. The default template stamps type="screen4x3" on <p:sldSz> even for 16:9 — fix it.
# 3. Keynote REJECTS any pptx whose <p:notes> parts lack <p:clrMapOvr> ("The file
#    format is invalid"), even though the schema calls it optional. Inject it.
# 4. Add a fade transition on every slide so the deck has native motion in
#    PowerPoint/Keynote (VoxDeck-style polish; static renderers simply ignore it).
tmp = out + ".tmp"
with zipfile.ZipFile(out, "r") as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
    infos = zin.infolist()
    names = [i.filename for i in infos]
    last_idx = {}
    for idx, n in enumerate(names):
        last_idx[n] = idx  # last occurrence wins
    # find the relationship id of the notes master (needed for the notesMasterIdLst fix)
    rels = zin.read("ppt/_rels/presentation.xml.rels")
    m = re.search(rb'<Relationship [^>]*notesMaster[^>]*/>', rels)
    nm_rid = re.search(rb'Id="([^"]+)"', m.group(0)).group(1) if m else None
    for idx, item in enumerate(infos):
        if idx != last_idx[item.filename]:
            continue  # duplicate entry — keep only the final version
        name = item.filename
        data = zin.read(name)
        if name == "ppt/presentation.xml":
            data = data.replace(b'type="screen4x3"', b'type="screen16x9"')
            if nm_rid and b"notesMasterIdLst" not in data:
                # python-pptx omits <p:notesMasterIdLst>; real PowerPoint files always
                # declare it. Keynote validates this chain and rejects the file without
                # it ("The file format is invalid"). CT_Presentation order:
                # sldMasterIdLst -> notesMasterIdLst -> sldIdLst.
                data = data.replace(
                    b"</p:sldMasterIdLst>",
                    b"</p:sldMasterIdLst>"
                    + b"<p:notesMasterIdLst><p:notesMasterId r:id=\"" + nm_rid + b"\"/></p:notesMasterIdLst>",
                    1)
        elif name == "ppt/notesSlides/notesSlide1.xml" or name.startswith("ppt/notesSlides/notesSlide"):
            marker = b"</p:cSld>"
            if b"<p:clrMapOvr>" not in data:
                data = data.replace(marker, marker + b"<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>", 1)
        elif name.startswith("ppt/slides/slide") and name.endswith(".xml"):
            marker = b"<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>"
            if b"<p:transition" not in data and marker in data:
                data = data.replace(
                    marker,
                    marker + b'<p:transition spd="med" advClick="1"><p:fade/></p:transition>',
                    1)
            # Progressive build: fade in frame 2 at 2.0s and frame 3 at 4.8s after
            # the slide appears (absolute delays from slide start; both groups
            # fire on sequence begin). presetID 10 = Fade entrance.
            if b"<p:timing>" not in data:
                pics = re.findall(rb"<p:pic>.*?</p:pic>", data, re.S)
                pic_ids = [re.search(rb'<p:cNvPr id="(\d+)"', p).group(1) for p in pics]
                if len(pic_ids) >= 3:
                    def build_group(gid, delay, spid):
                        return (
                            b"<p:par><p:cTn id=\"%d\" fill=\"hold\">"
                            b"<p:stCondLst><p:cond delay=\"indefinite\"/>"
                            b"<p:cond evt=\"onBegin\" delay=\"0\"><p:tn val=\"2\"/></p:cond></p:stCondLst>"
                            b"<p:childTnLst><p:par><p:cTn id=\"%d\" fill=\"hold\">"
                            b"<p:stCondLst><p:cond delay=\"%d\"/></p:stCondLst>"
                            b"<p:childTnLst><p:par>"
                            b"<p:cTn id=\"%d\" presetID=\"10\" presetClass=\"entr\" presetSubtype=\"0\" "
                            b"fill=\"hold\" grpId=\"0\" nodeType=\"afterEffect\">"
                            b"<p:stCondLst><p:cond delay=\"0\"/></p:stCondLst><p:childTnLst>"
                            b"<p:set><p:cBhvr><p:cTn id=\"%d\" dur=\"1\" fill=\"hold\">"
                            b"<p:stCondLst><p:cond delay=\"0\"/></p:stCondLst></p:cTn>"
                            b"<p:tgtEl><p:spTgt spid=\"%s\"/></p:tgtEl>"
                            b"<p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst>"
                            b"</p:cBhvr><p:to><p:strVal val=\"visible\"/></p:to></p:set>"
                            b"<p:animEffect transition=\"in\" filter=\"fade\"><p:cBhvr>"
                            b"<p:cTn id=\"%d\" dur=\"800\"/>"
                            b"<p:tgtEl><p:spTgt spid=\"%s\"/></p:tgtEl></p:cBhvr></p:animEffect>"
                            b"</p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par>"
                            b"</p:childTnLst></p:cTn></p:par>"
                        ) % (gid, gid + 1, delay, gid + 2, gid + 3, spid, gid + 4, spid)

                    groups = (build_group(3, 2000, pic_ids[1]) + build_group(10, 4800, pic_ids[2]))
                    timing = (
                        b"<p:timing><p:tnLst><p:par>"
                        b"<p:cTn id=\"1\" dur=\"indefinite\" restart=\"never\" nodeType=\"tmRoot\">"
                        b"<p:childTnLst><p:seq concurrent=\"1\" nextAc=\"seek\">"
                        b"<p:cTn id=\"2\" dur=\"indefinite\" nodeType=\"mainSeq\">"
                        b"<p:childTnLst>" + groups + b"</p:childTnLst></p:cTn>"
                        b"<p:prevCondLst><p:cond evt=\"onPrev\" delay=\"0\">"
                        b"<p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>"
                        b"<p:nextCondLst><p:cond evt=\"onNext\" delay=\"0\">"
                        b"<p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst>"
                        b"</p:seq></p:childTnLst></p:cTn></p:par></p:tnLst>"
                        b"<p:bldLst><p:bldP spid=\"" + pic_ids[1] + b"\" grpId=\"0\"/>"
                        b"<p:bldP spid=\"" + pic_ids[2] + b"\" grpId=\"0\"/></p:bldLst>"
                        b"</p:timing>")
                    data = data.replace(b"</p:sld>", timing + b"</p:sld>", 1)
        zout.writestr(item.filename, data)
shutil.move(tmp, out)
print("Saved", out, "with", len(slides_meta), "animated slides (3 build frames each)")
