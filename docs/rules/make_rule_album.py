#!/usr/bin/env python3
"""Bind the rule screenshots into one PDF.

Each picture already carries its own caption — the condition, what it means,
and every robot's position — because it was labelled at the moment it was
taken. This groups them by condition, adds a contents page, and records what
did NOT appear, which is often the more useful half.

    python3 docs/rules/make_rule_album.py docs/rules/shots docs/rules/amr-rules-in-action.pdf
"""

import os
import re
import sys
from collections import OrderedDict

from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, Frame, Image as RLImage,
                                PageBreak, PageTemplate, Paragraph, Spacer,
                                Table, TableStyle)

INK = colors.HexColor("#16232B")
SOFT = colors.HexColor("#4A5C67")
FAINT = colors.HexColor("#8B9BA5")
RULE = colors.HexColor("#C7D4DB")
BLUE = colors.HexColor("#1E5F8C")
OK = colors.HexColor("#2E7D5B")

#: Conditions that exist in the code. Anything here with no picture did not
#: happen during the run — which for the failure conditions is the point.
NEVER_FIRED_MATTERS = {
    "gave-way-for": "the 45-second give-up that cost jobs in earlier runs",
    "deadlocked-with": "the deadlock breaker",
    "standing-aside-threat": "a yielder blocked on its way to the lay-by",
    "nowhere-to-stand-aside": "a yielder with no reachable lay-by",
    "robot-ahead-on-the-road": "the protective corridor stopping a robot",
    "queueing-behind": "a follower held behind a robot that is giving way",
    "pulling-out-road-not-clear": "a robot unable to reverse out of a bay",
    "battery-flat": "a robot stopped with a flat battery",
}


def condition_of(filename):
    stem = re.sub(r"^\d+_", "", os.path.splitext(filename)[0])
    return re.sub(r"^amr\d+-", "", stem)


def build(shots_dir, out_path):
    files = sorted(f for f in os.listdir(shots_dir) if f.endswith(".png"))
    if not files:
        print("no images in", shots_dir, file=sys.stderr)
        return 1

    groups = OrderedDict()
    for f in files:
        groups.setdefault(condition_of(f), []).append(f)

    page = landscape(A4)
    doc = BaseDocTemplate(out_path, pagesize=page,
                          leftMargin=14 * mm, rightMargin=14 * mm,
                          topMargin=12 * mm, bottomMargin=12 * mm,
                          title="AMR rules in action",
                          author="T-Robotics / Foil_A082")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height,
                  id="body")

    def furniture(canvas, d):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(FAINT)
        canvas.drawString(doc.leftMargin, 7 * mm,
                          "Foil_A082  ·  every picture taken at the instant the "
                          "condition fired, from the overhead camera in the world")
        canvas.drawRightString(page[0] - doc.rightMargin, 7 * mm,
                               "page %d" % canvas.getPageNumber())
        canvas.restoreState()

    doc.addPageTemplates([PageTemplate(id="all", frames=[frame],
                                       onPage=furniture)])

    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Normal"], fontName="Helvetica-Bold",
                        fontSize=24, leading=28, textColor=INK, spaceAfter=6)
    sub = ParagraphStyle("sub", parent=ss["Normal"], fontName="Helvetica",
                         fontSize=10.5, leading=15, textColor=SOFT, spaceAfter=14)
    h2 = ParagraphStyle("h2", parent=ss["Normal"], fontName="Helvetica-Bold",
                        fontSize=13, leading=16, textColor=BLUE, spaceAfter=6)
    body = ParagraphStyle("body", parent=ss["Normal"], fontName="Helvetica",
                          fontSize=9.5, leading=13, textColor=INK)
    small = ParagraphStyle("small", parent=body, fontSize=8.5, leading=11.5,
                           textColor=SOFT)

    story = [Paragraph("AMR rules in action", h1),
             Paragraph("Sixty moments from one five-robot run, each photographed "
                       "the instant a condition fired. The caption on every "
                       "picture was written at that moment: the condition, what "
                       "it means, and where all five robots were.", sub)]

    rows = [[Paragraph("<b>Condition</b>", small),
             Paragraph("<b>Times seen</b>", small)]]
    for name, shots in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        rows.append([Paragraph(name.replace("-", " "), body),
                     Paragraph(str(len(shots)), body)])
    t = Table(rows, colWidths=[doc.width * 0.62, doc.width * 0.16], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (0, -1), 0),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, INK),
        ("LINEBELOW", (0, 1), (-1, -2), 0.3, RULE),
    ]))
    story += [Paragraph("What was seen", h2), t, Spacer(1, 12)]

    missing = [(k, why) for k, why in NEVER_FIRED_MATTERS.items()
               if not any(k in g for g in groups)]
    if missing:
        story.append(Paragraph("What was NOT seen", h2))
        story.append(Paragraph(
            "These conditions exist in the code and did not fire once during "
            "the run. They are the failure paths that dominated earlier runs, "
            "so their absence is the result, not a gap in the recording.",
            small))
        story.append(Spacer(1, 5))
        for key, why in missing:
            story.append(Paragraph(
                '<font color="#2E7D5B">&#10003;</font> &nbsp; <b>%s</b> — %s'
                % (key.replace("-", " "), why), body))
    story.append(PageBreak())

    avail_w, avail_h = doc.width, doc.height - 16 * mm
    for name, shots in groups.items():
        for i, f in enumerate(shots, 1):
            path = os.path.join(shots_dir, f)
            with Image.open(path) as im:
                iw, ih = im.size
            scale = min(avail_w / iw, avail_h / ih)
            story.append(Paragraph("%s &nbsp;<font size=9 color='#8B9BA5'>"
                                   "(%d of %d)</font>"
                                   % (name.replace("-", " "), i, len(shots)), h2))
            story.append(RLImage(path, iw * scale, ih * scale))
            story.append(PageBreak())

    doc.build(story)
    print("wrote %s  (%d pictures, %d conditions)"
          % (out_path, len(files), len(groups)))
    return 0


if __name__ == "__main__":
    sys.exit(build(sys.argv[1], sys.argv[2]))
