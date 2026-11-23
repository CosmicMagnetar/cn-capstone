#!/usr/bin/env python3
"""Build the curated Phase 2 Markdown, terminal excerpts, and PDF."""

from __future__ import annotations

import html
import textwrap
from pathlib import Path

from PIL import Image as PILImage, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Flowable, Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "phase2/evidence"
SOURCES = EVIDENCE / "sources"
REPORT = ROOT / "phase2/README.md"
PDF = ROOT / "documentation/CN_Phase2_Final_Report.pdf"
SHARE = "https://chatgpt.com/share/6b03b06a-dd40-83e8-9bf8-6fcc23ebb9a0"
FONT_DIR = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/native/libreoffice-headless/libreoffice/LibreOfficeDev.app/Contents/Resources/fonts/truetype"
MONO = Path("/System/Library/Fonts/Menlo.ttc")
BT = chr(96)

# Every excerpt is an unchanged, contiguous line range of one pasted chat message.
# These are evidence selections, not claims that the full turn is reproduced in the image.
FIGURES = [
    ("01-edge-load-balancing", 21, 21, 75, "Mac 2 / Krishna", "Corrected upstream; six alternating HTTP 200 A/B responses", "Baseline"),
    ("02-client-verified-https", 27, 77, 121, "Mac 4 / Saumya Mishra", "Strict TLS and HTTP 200 using --resolve; DNS bypassed for this request", "Baseline"),
    ("03-client-dual-dns", 29, 12, 45, "Mac 4 / Saumya Mishra", "Client resolver file lists both DNS servers; domain HTTPS succeeds", "A"),
    ("04-backup-dns-answer", 31, 18, 43, "Mac 4 / Saumya Mishra", "Backup DNS directly answers the project name", "A"),
    ("05-ttl-cache-expiry", 65, 93, 160, "Mac 2 / Krishna", "Old cached answer at TTL 1, then new address after expiry", "B"),
    ("06-firewall-backend-a", 39, 20, 39, "Mac 3 / Rachit Gupta", "Backend A pf rules active", "C"),
    ("07-firewall-backend-b", 39, 60, 80, "Mac 4 / Saumya Mishra", "Backend B pf rules active", "C"),
    ("08-edge-backend-access", 39, 81, 106, "Mac 2 / Krishna", "Edge obtains HTTP 200 from both backend ports", "C"),
    ("09-client-direct-access-denied", 41, 1, 8, "Mac 1 / Aditya Rana", "Non-edge client TCP probes to 3001 and 3002 time out", "C"),
    ("10-backend-a-down", 33, 1, 49, "Mac 2 / Krishna", "Six HTTP 200 responses served by B during A outage", "D"),
    ("11-backend-a-restored", 35, 49, 97, "Mac 2 / Krishna", "A appears again after recovery", "D"),
    ("12-standby-edge", 57, 30, 64, "Mac 3 / Rachit Gupta", "Standby nginx listens on 8443 and serves HTTPS", "E"),
    ("13-dns-cutover", 59, 5, 20, "Team / edge migration", "Both DNS servers answer Mac 3; domain HTTPS returns HTTP 200", "E"),
    ("14-dns-restored", 61, 1, 25, "Mac 2 / Krishna", "Both DNS servers and domain HTTPS return to Mac 2", "E"),
]

EXTENSIONS = [
    ("A", "Backup DNS resolver",
     "Mac 4 ran backup dnsmasq with the same project records. The client listed Mac 1 and Mac 4 as DNS servers. A direct query to Mac 4 returned the primary edge address.",
     "The pasted sequence restarts Mac 1 before the later client lookup. Automatic client fallback while Mac 1 remains down still needs a live capture.",
     "A backup resolver only proves resilience when a client resolves during the primary outage."),
    ("B", "DNS TTL and controlled record change",
     "Both project DNS configurations use a 30-second local TTL. A temporary caching resolver on Mac 2 kept the old edge address at TTL 1 while primary DNS answered Mac 3, then returned Mac 3 after expiry.",
     "The output proves cache expiry for that temporary resolver. An immediate post-flush macOS client lookup is not captured.",
     "DNS cutover is gradual because cached clients can retain the old address until expiry or a verified cache flush."),
    ("C", "Backend service isolation",
     "pf rules were enabled on Macs 3 and 4. Mac 2 reached both backends with HTTP 200; Mac 1 timed out on direct TCP connections to both backend ports.",
     "The rule backups are referenced in the pasted setup, but the final restoration and verification are not captured. Backend B also allows Mac 3 for its standby edge role, an explicit exception to the brief's literal only-Mac-2 rule.",
     "Test the active filter from both permitted and denied sources, then verify rollback."),
    ("D", "Backend failure and recovery",
     "With Backend A stopped, six edge requests returned HTTP 200 from B. After A restarted, A appeared again among six successful requests.",
     "The remaining single point of failure in the normal path is Mac 2's edge nginx. A standby edge reduces that risk only after DNS cutover and client cache expiry.",
     "Measure availability at the client through the edge, not only at the backend process."),
    ("E", "Controlled edge migration",
     "Standby nginx on Mac 3 listened on 8443 and returned HTTP 200. Both DNS servers were moved to Mac 3, a domain HTTPS request succeeded through nginx/1.31.9, and both records were restored to Mac 2.",
     "The pasted output does not time a cached client continuing to reach the old edge while a fresh lookup reaches Mac 3.",
     "The standby needs the same hostname, trusted certificate, reachable backends, and coordinated DNS records."),
    ("F", "Faculty-injected fault",
     "No faculty fault has been injected in the supplied material. The live diagnosis sequence is DNS, TCP, TLS, then HTTP and backend.",
     "Pending evaluation; no result or fix is claimed.",
     "Locate the first failing layer before editing configuration."),
]

def source_lines(turn: int) -> list[str]:
    path = SOURCES / f"turn-{turn:03d}.txt"
    if not path.exists():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8").splitlines()

def excerpt(turn: int, first: int, last: int) -> list[str]:
    lines = source_lines(turn)
    if not (1 <= first <= last <= len(lines)):
        raise ValueError((turn, first, last, len(lines)))
    return lines[first - 1:last]

def mono(size: int):
    path = MONO if MONO.exists() else FONT_DIR / "DejaVuSansMono.ttf"
    return ImageFont.truetype(str(path), size)

def render_figure(item: tuple) -> Path:
    slug, turn, first, last, owner, claim, extension = item
    lines = excerpt(turn, first, last)
    display = []
    for line in lines:
        line = line.expandtabs(4).replace("\u00a0", " ")
        display.extend(textwrap.wrap(line, width=108, break_long_words=True,
                                     break_on_hyphens=False, replace_whitespace=False,
                                     drop_whitespace=False) or [""])
    font = mono(20)
    small = mono(16)
    width, line_height = 1460, 28
    height = 106 + line_height * len(display) + 34
    img = PILImage.new("RGB", (width, height), "#080808")
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, width - 1, 68), fill="#2b2b2b")
    for x, c in [(27, "#ff5f57"), (58, "#febc2e"), (89, "#28c840")]:
        d.ellipse((x, 24, x + 17, 41), fill=c)
    d.text((130, 20), f"Terminal - {owner}", font=mono(19), fill="#f0f0f0")
    y = 88
    for line in display:
        if d.textlength(line, font=font) > width - 68:
            raise ValueError(f"clipped {slug}: {line}")
        d.text((31, y), line, font=font, fill="#f6f6f6")
        y += line_height
    d.text((31, height - 25), f"PASTED CHAT TURN {turn:03d} / LINES {first}-{last} / EXACT EXCERPT",
           font=small, fill="#a0a0a0")
    path = EVIDENCE / f"{slug}.png"
    img.save(path, optimize=True)
    return path

def markdown(paths: dict[str, Path]) -> None:
    out = [
        "# CN Capstone Project - Phase 2 Final Report",
        "",
        "**Team:** Netforcers",
        "",
        "**Domain:** " + BT + "app.cn-capstone.test" + BT,
        "",
        "**Evidence date:** 22 November 2026",
        "",
        "## 1. Scope and evidence",
        "",
        "This report updates the Phase 1 architecture and covers mandatory Phase 2 Extensions A-F. "
        "The fourteen terminal figures below are **selected, contiguous excerpts** from the team's pasted outputs in the "
        f"[shared chat]({SHARE}). Each title bar shows the Mac/person; each footer identifies the source turn and exact line range. "
        "They are rendered images of pasted text, not original screen captures or new tests. "
        "The matching complete selected source messages are stored in " + BT + "phase2/evidence/sources/" + BT + ". "
        "Phase 1 packet captures remain historical evidence with earlier DHCP addresses.",
        "",
        "## 2. Team, network, and architecture",
        "",
        "| Mac | Team member | Phase 2 services | Recorded LAN IP |",
        "|---|---|---|---|",
        "| 1 | Aditya Rana | Primary DNS :53; client | " + BT + "10.7.17.8" + BT + " |",
        "| 2 | Krishna | Primary nginx HTTPS :8443; load balancer | " + BT + "10.7.12.238" + BT + " |",
        "| 3 | Rachit Gupta | Backend A HTTP :3001; standby nginx HTTPS :8443; pf | " + BT + "10.7.21.149" + BT + " |",
        "| 4 | Saumya Mishra | Backend B HTTP :3002; backup DNS :53; pf; client | " + BT + "10.7.21.214" + BT + " |",
        "",
        "All four Macs used " + BT + "en0" + BT + " on " + BT + "10.7.0.0/19" + BT + " with gateway " + BT + "10.7.0.1" + BT + ". "
        "These were DHCP addresses; recheck them before evaluation.",
        "",
        BT * 3 + "mermaid",
        "flowchart TD",
        "    C[Client on Mac 1 or Mac 4]",
        "    M1[Mac 1: Aditya Rana<br/>Primary DNS :53]",
        "    M2[Mac 2: Krishna<br/>Primary nginx HTTPS :8443]",
        "    M3[Mac 3: Rachit Gupta<br/>Backend A :3001 and standby nginx :8443]",
        "    M4[Mac 4: Saumya Mishra<br/>Backend B :3002 and backup DNS :53]",
        "    C -->|DNS| M1",
        "    C -.->|backup DNS| M4",
        "    C -->|HTTPS / TLS| M2",
        "    M2 -->|HTTP| M3",
        "    M2 -->|HTTP| M4",
        "    C -.->|DNS cutover then HTTPS| M3",
        "    M3 -.->|standby upstream| M4",
        BT * 3,
        "",
        "The normal path is client DNS to Mac 1, then client TLS to Mac 2, then HTTP to Mac 3 or Mac 4. "
        "During controlled edge migration both DNS servers temporarily pointed to Mac 3. "
        "Each physical Mac appears once in the diagram, including Mac 4's two services.",
        "",
        "## 3. Phase 2 configuration changes",
        "",
        "Phase 1 had one DNS resolver, one HTTPS edge, two REST backends, cache headers, and protocol captures. "
        "Phase 2 added backup DNS on Mac 4, backend pf rules, and standby nginx on Mac 3. "
        "The versioned configuration bundle is in " + BT + "phase2/configs/" + BT + ". "
        "Both project DNS configurations set " + BT + "local-ttl=30" + BT + ". "
        "Backend B's pf exception for Mac 3 supports its standby edge role.",
        "",
        "**Troubleshooting during setup:** old Phase 1 backend IPs initially produced nginx 504 responses; the upstream addresses were corrected. "
        "Mac 4's scoped resolver initially pointed to an older Mac 1 address and was corrected. "
        "A changed authoritative DNS record did not immediately replace a cached answer. "
        "The standby edge needs the trusted certificate and backend reachability. "
        "The normal HTTPS endpoint uses explicit port " + BT + "8443" + BT + ".",
        "",
        "## 4. Resilience results and learning",
        "",
    ]
    for letter, title, result, limit, learning in EXTENSIONS:
        out += [f"### Extension {letter} - {title}", "", "**Observed:** " + result, "",
                "**Evidence limit:** " + limit, "", "**Learning:** " + learning, ""]
    out += [
        "## 5. Curated terminal evidence",
        "",
        "The figures show the exact selected command/output lines, including failures and prompts where they occur. "
        "No result line inside a selected range was removed. Their source messages can be checked against the shared chat.",
        "",
    ]
    for slug, turn, first, last, owner, claim, extension in FIGURES:
        out += [f"### {slug.replace('-', ' ').title()} - {owner}", "",
                f"**Supports:** {claim}. Source: pasted turn {turn:03d}, lines {first}-{last}.",
                "", f"![{claim}](evidence/{slug}.png)", ""]
    out += [
        "## 6. Final demonstration and remaining live proof",
        "",
        "| Step | Show during evaluation |",
        "|---|---|",
        "| 1-2 | Diagram, four current IPs and ports, then pairwise LAN ping |",
        "| 3-4 | Client DNS answer and trusted HTTPS by domain, without insecure flags |",
        "| 5-7 | A/B responses, Phase 1 DNS/TCP/TLS packet captures, cache headers and 304 |",
        "| 8 | Stop Backend A, show B-only HTTP 200, restart A and show A/B |",
        "| 9 | Backup DNS during primary-down state, TTL expiry and cache flush, then edge cutover |",
        "| 10 | Diagnose the faculty fault in DNS -> TCP -> TLS -> HTTP order |",
        "| 11 | Each team member explains their machine and the full request path |",
        "",
        "**Still to capture live:** (1) a client resolving through Mac 4 while Mac 1 dnsmasq stays stopped; "
        "(2) an immediate changed answer after a verified macOS cache flush; "
        "(3) a cached client still reaching the old edge during cutover; "
        "(4) pf restoration and verification; and (5) the faculty-injected fault. "
        "The pasted logs do not establish these outcomes. The Phase 1 unified script was not rerun on this workspace's physical LAN.",
        "",
        "**Diagnosis order:** " + BT + "dig" + BT + " against both project resolvers -> TCP probe to selected edge :8443 "
        "-> verified TLS handshake with the project certificate -> HTTP status and X-Backend -> nginx/backend logs.",
        "",
        "## 7. Sources",
        "",
        f"- [Pasted terminal conversation]({SHARE})",
        "- Course specification: " + BT + "CN_Project_Doc (1).pdf" + BT + ", sections 7-10.",
        "- Phase 1 PDFs and packet captures remain in " + BT + "documentation/" + BT + " and " + BT + "evidence/" + BT + ".",
        "- This report, its 14 PNG figures, and the PDF are regenerated by " + BT + "phase2/tools/build_report.py" + BT + ".",
        "",
    ]
    REPORT.write_text("\n".join(out), encoding="utf-8")

def pdf_fonts() -> tuple[str, str]:
    reg = FONT_DIR / "DejaVuSans.ttf"
    bold = FONT_DIR / "DejaVuSans-Bold.ttf"
    if reg.exists() and bold.exists():
        pdfmetrics.registerFont(TTFont("CNBody", str(reg)))
        pdfmetrics.registerFont(TTFont("CNBold", str(bold)))
        return "CNBody", "CNBold"
    return "Helvetica", "Helvetica-Bold"

REG, BOLD = pdf_fonts()
INK = colors.HexColor("#18263a")
BLUE = colors.HexColor("#34658e")
PALE = colors.HexColor("#eaf1f7")
LINE = colors.HexColor("#cfdae5")
W, H = A4
CONTENT = W - 92
STYLES = {
    "title": ParagraphStyle("title", fontName=BOLD, fontSize=21, leading=27, textColor=INK, spaceAfter=12),
    "h1": ParagraphStyle("h1", fontName=BOLD, fontSize=13, leading=18, textColor=BLUE, spaceAfter=8),
    "h2": ParagraphStyle("h2", fontName=BOLD, fontSize=10, leading=14, textColor=BLUE, spaceAfter=5),
    "body": ParagraphStyle("body", fontName=REG, fontSize=8.7, leading=13, textColor=INK, spaceAfter=9),
    "small": ParagraphStyle("small", fontName=REG, fontSize=7.4, leading=10.5, textColor=INK, spaceAfter=6),
    "cell": ParagraphStyle("cell", fontName=REG, fontSize=7.4, leading=10.5, textColor=INK),
    "head": ParagraphStyle("head", fontName=BOLD, fontSize=7.4, leading=10.5, textColor=colors.white),
}
def para(s: str, style: str = "body") -> Paragraph:
    return Paragraph(html.escape(s).replace("\n", "<br/>"), STYLES[style])
def table(rows: list[list[str]], widths: list[float]) -> Table:
    t = Table([[para(x, "head" if i == 0 else "cell") for x in row]
               for i, row in enumerate(rows)], colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
        ("GRID", (0, 0), (-1, -1), .35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t
def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.line(46, 38, W - 46, 38)
    canvas.setFont(REG, 7)
    canvas.setFillColor(INK)
    canvas.drawString(46, 25, "NETFORCERS | CN PHASE 2 | CURATED TERMINAL EVIDENCE")
    canvas.drawRightString(W - 46, 25, f"Page {doc.page}")
    canvas.restoreState()

class FourMacDiagram(Flowable):
    def __init__(self):
        Flowable.__init__(self)
        self.width = CONTENT
        self.height = 160

    def draw(self):
        c = self.canv
        nodes = [
            (0, 84, "MAC 1 / ADITYA RANA", "Primary DNS :53"),
            (260, 84, "MAC 2 / KRISHNA", "Primary nginx HTTPS :8443"),
            (0, 0, "MAC 3 / RACHIT GUPTA", "Backend A :3001 + standby nginx :8443"),
            (260, 0, "MAC 4 / SAUMYA MISHRA", "Backend B :3002 + backup DNS :53"),
        ]
        for x, y, title, role in nodes:
            c.setFillColor(PALE)
            c.setStrokeColor(LINE)
            c.roundRect(x, y, 245, 65, 6, fill=1, stroke=1)
            c.setFillColor(INK)
            c.setFont(BOLD, 7.5)
            c.drawString(x + 9, y + 42, title)
            c.setFont(REG, 7)
            c.drawString(x + 9, y + 21, role)
        c.setStrokeColor(BLUE)
        c.setLineWidth(1.2)
        c.line(245, 116, 260, 116)
        c.line(382, 84, 382, 65)
        c.line(295, 84, 215, 65)
        c.line(245, 32, 260, 32)

def pdf(paths: dict[str, Path]) -> None:
    story = [Spacer(1, 13), para("CN Capstone Project", "title"),
             para("Phase 2 - Harden, Recover, and Troubleshoot", "h1"),
             para("Netforcers | app.cn-capstone.test | Evidence: 22 November 2026", "small"),
             para("1. Scope and evidence method", "h1"),
             para("This report updates the Phase 1 architecture and documents mandatory Extensions A-F. Fourteen selected terminal excerpts are rendered from user-pasted chat messages. Each figure names its owner and source line range. These are not original Mac screen captures or new tests."),
             para("2. Team and four-machine architecture", "h1"),
             KeepTogether(table([
                 ["Mac", "Team member", "Phase 2 roles", "Recorded IP"],
                 ["1", "Aditya Rana", "Primary DNS :53; client", "10.7.17.8"],
                 ["2", "Krishna", "Primary nginx HTTPS :8443", "10.7.12.238"],
                 ["3", "Rachit Gupta", "Backend A :3001; standby nginx :8443; pf", "10.7.21.149"],
                 ["4", "Saumya Mishra", "Backend B :3002; backup DNS :53; pf; client", "10.7.21.214"],
             ], [32, 106, 267, CONTENT - 405])),
             Spacer(1, 10),
             FourMacDiagram(),
             Spacer(1, 9),
             para("10.7.0.0/19 via en0; gateway 10.7.0.1. Normal path: client -> Mac 1 DNS -> Mac 2 TLS/nginx -> Mac 3 or Mac 4 HTTP. Controlled cutover: both DNS servers point the client to Mac 3 standby nginx. Mac 4 is one physical machine with two services."),
             para("3. Changes from Phase 1", "h1"),
             para("Phase 2 added backup DNS, backend pf isolation, and a standby edge. Both project DNS configurations set local-ttl=30. Configuration files are in phase2/configs/. The recorded IPs are DHCP leases and must be checked before evaluation."),
             para("Setup troubleshooting: old Phase 1 backend IPs initially caused nginx 504 responses; Mac 4's scoped resolver pointed to an old DNS address. Both were corrected. The normal HTTPS URL requires explicit port 8443."),
             para("4. Results and learning", "h1")]
    for letter, title, result, limit, learning in EXTENSIONS:
        story.append(KeepTogether([
            para(f"Extension {letter} - {title}", "h2"),
            para("Observed: " + result, "small"),
            para("Evidence limit: " + limit, "small"),
            para("Learning: " + learning, "small"),
        ]))
    story += [para("5. Remaining live proof", "h1"),
              para("Capture primary-down DNS fallback, an immediate macOS cache-flush lookup, client cache timing during cutover, pf restoration, and the faculty-injected fault. The pasted outputs do not prove these outcomes. Re-run the Phase 1 unified suite only on the physical LAN and record its real result."),
              para("Final demo: inventory and ping; DNS; trusted domain HTTPS; A/B; historical packet captures; cache and 304; backend outage/recovery; Phase 2 DNS/cutover; faculty fault; individual viva."),
              para(f"Sources: {SHARE}. Course brief: CN_Project_Doc (1).pdf, sections 7-10. Full selected pasted messages: phase2/evidence/sources/. GitHub report: phase2/README.md.", "small"),
              PageBreak()]
    for slug, turn, first, last, owner, claim, extension in FIGURES:
        path = paths[slug]
        story += [para(f"Figure {slug[:2]} - {owner}", "h1"),
                  para(f"Extension {extension}. {claim}. Pasted chat turn {turn:03d}, lines {first}-{last}. Exact contiguous excerpt; not an original screenshot.", "small")]
        with PILImage.open(path) as im:
            pw, ph = im.size
        iw = CONTENT
        ih = ph * iw / pw
        if ih > 615:
            iw *= 615 / ih
            ih = 615
        story += [Image(str(path), width=iw, height=ih), PageBreak()]
    doc = SimpleDocTemplate(str(PDF), pagesize=A4, leftMargin=46, rightMargin=46,
                            topMargin=45, bottomMargin=54,
                            title="CN Capstone Project - Phase 2 Final Report", author="Netforcers")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)

def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    paths = {item[0]: render_figure(item) for item in FIGURES}
    markdown(paths)
    pdf(paths)
    print(f"Built {len(paths)} curated PNGs, {REPORT}, and {PDF}")

if __name__ == "__main__":
    main()
