#!/usr/bin/env python3
"""Render the Selected work product cards.

Every card is 720x300 so the README grid stays even, and every value in them —
palettes, panel widths, row heights, fonts — is copied from the tool's own
source rather than eyeballed. Menlo everywhere, because that is what the pets
and the status line actually draw with.

    python3 scripts/generate-work-cards.py
"""

import os

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "work")
W, H = 720, 300
MONO = "ui-monospace, Menlo, SFMono-Regular, monospace"
ADV = 0.602            # Menlo advance width, in ems

def adv(size):
    return size * ADV

def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def text(t, x, y, size=12, fill="#e6e6e6", weight=None, anchor=None, opacity=None):
    a = f' font-weight="{weight}"' if weight else ""
    b = f' text-anchor="{anchor}"' if anchor else ""
    c = f' opacity="{opacity}"' if opacity is not None else ""
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}"{a}{b}{c}>{esc(t)}</text>'

def rect(x, y, w, h, fill, rx=0, stroke=None, sw=1, opacity=None):
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    o = f' opacity="{opacity}"' if opacity is not None else ""
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}"{s}{o}/>'

def lerp_hex(c1, c2, n):
    """Same integer per-mille lerp the status line uses, so the ramp matches."""
    r1, g1, b1 = int(c1[0:2], 16), int(c1[2:4], 16), int(c1[4:6], 16)
    r2, g2, b2 = int(c2[0:2], 16), int(c2[2:4], 16), int(c2[4:6], 16)
    out = []
    for i in range(n):
        p = i * 1000 // (n - 1) if n > 1 else 0
        out.append("#%02x%02x%02x" % (r1 + (r2 - r1) * p // 1000,
                                      g1 + (g2 - g1) * p // 1000,
                                      b1 + (b2 - b1) * p // 1000))
    return out

def gradient_text(s, x, y, c1, c2, size=13, weight="700"):
    """One span per character — terminals have no gradients, and neither does SVG text."""
    cols = lerp_hex(c1, c2, len(s))
    step = adv(size)
    return "".join(text(ch, x + i * step, y, size, cols[i], weight) for i, ch in enumerate(s))

def rgba(c, a=None):
    return c if a is None else c

def card(body, bg="#0b0b0d", stroke="#1e1e24"):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
            f'viewBox="0 0 {W} {H}" font-family="{MONO}">'
            f'{rect(0, 0, W, H, bg)}'
            f'{rect(0.5, 0.5, W - 1, H - 1, "none", 0, stroke)}'
            f'{body}</svg>\n')

def write(name, svg):
    path = os.path.join(OUT, name)
    with open(path, "w") as f:
        f.write(svg)
    print("wrote", os.path.relpath(path))


# ---------------------------------------------------------------- statusline
# Four tmux panes, each with its own ground colour and its own status line —
# the ramps are the pane themes from bin/paint, the field colours are the ones
# in bin/statusline-neon.sh.
def statusline_card():
    panes = [
        # dim bg,   active bg, border,    ramp end,  project,     model,     effort,  eff colour, tokens,             tok colour
        ("#04100a", "#071a12", "#39ff88", "#22e0ff", "chessuno",  "Opus 5",  "xhigh", "#c6ff00", "880k/1.0M (88%)",  "#ff2b4d"),
        ("#100603", "#1a0a05", "#ff6a2b", "#ffc21e", "vlogify",   "Opus 5",  "high",  "#7dff4f", "412k/1.0M (41%)",  "#ff7a1f"),
        ("#0a0313", "#12061f", "#b26bff", "#ff3d94", "quokka",    "Opus 5",  "medium","#39ff88", "296k/1.0M (30%)",  "#ff7a1f"),
        ("#020c10", "#04141a", "#22e0ff", "#39ff88", "premiere",  "Fable 5.1","low",  "#2e8b57", "118k/1.0M (12%)",  "#ff9d4d"),
    ]
    pw, ph, gap = 336, 122, 12
    ox, oy = 20, 26
    b = [text("PER-PANE COLOUR · ONE STATUS LINE EACH", ox, 18, 9.5, "#5a5a66", "700")]
    for i, (dim, active, border, grad_end, proj, model, eff, eff_c, tok, tok_c) in enumerate(panes):
        x = ox + (i % 2) * (pw + gap)
        y = oy + (i // 2) * (ph + gap)
        is_active = (i == 0)
        b.append(rect(x, y, pw, ph, active if is_active else dim, 6,
                      border, 1.6 if is_active else 1))
        # the status line, drawn the way the script prints it
        fs = 10.5
        sx, sy = x + 14, y + ph - 16
        b.append(gradient_text("▏" + proj, sx, sy, border.lstrip("#"), grad_end.lstrip("#"), fs))
        sx += adv(fs) * (len(proj) + 1)
        for value, colour in ((" │ ", "#4e4e4e"), (model, "#4da3ff"),
                              (" │ ", "#4e4e4e"), (eff, eff_c),
                              (" │ ", "#4e4e4e"), (tok, tok_c)):
            b.append(text(value, sx, sy, fs, colour, "700" if colour != "#4e4e4e" else None))
            sx += adv(fs) * len(value)
        # a few lines of pretend session above it, so the pane reads as a pane
        for j, frag in enumerate(("$ claude", "· running tests", "✓ 155 passed")):
            b.append(text(frag, x + 14, y + 24 + j * 16, 10, border, opacity=0.26 + j * 0.07))
    return card("".join(b), "#08080a")


# ---------------------------------------------------------------- costpriority
# The board from cost/board.lua: 380 wide, 16 pad, 13/11 type, the `cost`
# palette from cost/themes.lua (cream card, green accent, hot P0).
def cost_card():
    P = {"card": "#faf7f0", "stroke": "#5c855f", "text": "#1c261e", "dim": "#6b7a6e",
         "accent": "#598f61", "rule": "#293d2e",
         "p0": "#b84d2e", "p1": "#598f61", "p2": "#708c7a", "p3": "#858f87"}
    bw, pad = 380, 16
    bx, by, bh = 34, 26, 248
    b = [text("CLICK THE PET · THE DAY, RANKED", bx, 18, 9.5, "#5a5a66", "700")]
    b.append(rect(bx, by, bw, bh, P["card"], 12, P["stroke"], 1))
    b.append(text("TODAY", bx + pad, by + 26, 11, P["dim"], "700"))
    b.append(text("Thu · 5 events", bx + bw - pad, by + 26, 10.5, P["dim"], anchor="end"))
    rows = [("P0", "p0", "Ship the status line docs", "the only thing today with a deadline", "9:30"),
            ("P1", "p1", "Axiom intern call", "3 people are waiting on this decision", "14:00"),
            ("P2", "p2", "Premiere Shelf preview cache", "unblocks the release, not urgent", "—"),
            ("P3", "p3", "Reply to the Stanford KID thread", "", "—")]
    y = by + 48
    for rank, key, title, why, when in rows:
        b.append(text(rank, bx + pad, y, 12, P[key], "700"))
        b.append(text(title, bx + pad + 30, y, 13, P["text"]))
        b.append(text(when, bx + bw - pad, y, 10.5, P["dim"], anchor="end"))
        y += 16
        if why:
            b.append(text(why, bx + pad + 30, y, 11, P["dim"]))
            y += 16
        y += 8
    b.append(rect(bx + pad, y - 4, bw - pad * 2, 1, P["rule"], opacity=0.13))
    b.append(text("ALSO ON TODAY", bx + pad, y + 16, 10, P["dim"], "700"))
    for i, line in enumerate(("· Dentist, 16:30", "· Pickleball with Dillon, 18:00")):
        b.append(text(line, bx + pad, y + 34 + i * 15, 11, P["dim"]))
    # the ghost, redrawn from the sprite's silhouette
    gx, gy = 520, 92
    ghost = (f'<g transform="translate({gx},{gy}) scale(1.6)">'
             '<path d="M0 62 V26 A26 26 0 0 1 52 26 V62 '
             'l-8.7 -7 -8.7 7 -8.6 -7 -8.7 7 -8.7 -7 Z" fill="#5c9160"/>'
             '<ellipse cx="17" cy="30" rx="5.4" ry="6.8" fill="#111"/>'
             '<ellipse cx="35" cy="30" rx="5.4" ry="6.8" fill="#111"/>'
             '<path d="M20 41 A6.5 6.5 0 0 0 33 41 Z" fill="#111"/></g>')
    b.append(ghost)
    b.append(text("P0", gx + 32, gy + 130, 12, "#5c9160", "700", anchor="middle"))
    b.append(text("menu bar", gx + 32, gy + 146, 9.5, "#5a5a66", anchor="middle"))
    return card("".join(b), "#0d0f0d")


# ---------------------------------------------------------------- organizepet
# petmanager/panel.lua: W=420, PAD=18, ROW=46, SHORT_ROW=34, HEADER=46,
# FOOTER=34, RADIUS=16, with the `noir` palette and the real row strings.
def organizepet_card():
    P = {"card": "#0e0e10", "text": "#f5f5f7", "dim": "#8e8e96",
         "accent": "#fa992e", "on": "#5cd180", "off": "#8c8c95"}
    pw, pad = 420, 18
    pets = [("Claude Code Pet", "on screen", "on", "hide", True),
            ("cost", "on screen", "on", "hide", False),
            ("mochi", "hidden", "off", "show", False)]
    settings = [("Hide every pet", "A"),
                ("Tidy — stack down the right edge", "T")]
    ph = 38 + len(pets) * 42 + 12 + len(settings) * 30 + 28
    x0, y0 = 272, (H - ph) / 2
    b = [text("⌃⌥⌘SPACE · EVERY PET, ONE PANEL", 20, 20, 9.5, "#5a5a66", "700")]

    # The pets the panel is talking about, loose on the desktop to its left.
    b.append('<g transform="translate(74,92) scale(2.2)">'
             '<rect x="0" y="0" width="36" height="18" fill="#e8552f"/>'
             '<rect x="8" y="4" width="5" height="5" fill="#111"/>'
             '<rect x="23" y="4" width="5" height="5" fill="#111"/>'
             '<rect x="2" y="18" width="5" height="7" fill="#e8552f"/>'
             '<rect x="11" y="18" width="5" height="7" fill="#e8552f"/>'
             '<rect x="20" y="18" width="5" height="7" fill="#e8552f"/>'
             '<rect x="29" y="18" width="5" height="7" fill="#e8552f"/></g>')
    b.append('<g transform="translate(92,180) scale(0.85)">'
             '<path d="M0 62 V26 A26 26 0 0 1 52 26 V62 '
             'l-8.7 -7 -8.7 7 -8.6 -7 -8.7 7 -8.7 -7 Z" fill="#5c9160"/>'
             '<ellipse cx="17" cy="30" rx="5.4" ry="6.8" fill="#111"/>'
             '<ellipse cx="35" cy="30" rx="5.4" ry="6.8" fill="#111"/>'
             '<path d="M20 41 A6.5 6.5 0 0 0 33 41 Z" fill="#111"/></g>')

    b.append(rect(x0, y0, pw, ph, P["card"], 16, "#3a3a42", 1))
    b.append(text("PETS", x0 + pad, y0 + 24, 11, P["dim"], "700"))
    b.append(text("↑↓  ⏎ toggle   ⌘⏎ its menu   esc", x0 + pw - pad, y0 + 24, 10, P["dim"], anchor="end"))
    y = y0 + 38
    for label, status, tone, hint, selected in pets:
        if selected:
            b.append(rect(x0 + 8, y - 2, pw - 16, 36, P["accent"], 8, opacity=0.16))
        b.append(text(label, x0 + pad, y + 14, 13, P["accent"] if selected else P["text"]))
        b.append(text(status, x0 + pad, y + 28, 10, P["on"] if tone == "on" else P["off"]))
        b.append(text(hint, x0 + pw - pad, y + 18, 10, P["dim"], anchor="end"))
        y += 42
    b.append(rect(x0 + pad, y + 2, pw - pad * 2, 1, "#ffffff", opacity=0.09))
    y += 12
    for label, hint in settings:
        b.append(text(label, x0 + pad, y + 18, 12, P["text"]))
        b.append(text(hint, x0 + pw - pad, y + 18, 10, P["dim"], anchor="end"))
        y += 30
    b.append(text("A hide all   ·   T tidy   ·   R reload", x0 + pad, y + 14, 10, P["dim"]))
    return card("".join(b), "#08080a")


# ---------------------------------------------------------------- phone
# The two status rows from ~/.tmux.conf, in tmux's own palette:
# colour235 #262626, colour114 #87d787, colour238 #444444, colour250 #bcbcbc.
def phone_card():
    C235, C114, C238, C250, C245 = "#262626", "#87d787", "#444444", "#bcbcbc", "#8a8a8a"
    b = [text("SESSIONS LIVE ON THE MAC · THE PHONE JUST ATTACHES", 20, 18, 9.5, "#5a5a66", "700")]
    # Mac: the 8-up grid, shrunk to a schematic
    mx, my, mw, mh = 20, 34, 420, 210
    b.append(rect(mx, my, mw, mh, "#0f0f12", 8, "#2a2a32", 1))
    cell_w, cell_h = (mw - 30) / 4, (mh - 58) / 2
    ramps = [("#39ff88", "#22e0ff"), ("#ff6a2b", "#ffc21e"), ("#b26bff", "#ff3d94"), ("#22e0ff", "#39ff88"),
             ("#ff3d94", "#b26bff"), ("#ffc21e", "#ff6a2b"), ("#5aa9ff", "#b26bff"), ("#b8ff29", "#39ff88")]
    for i in range(8):
        cx = mx + 10 + (i % 4) * (cell_w + 2.5)
        cy = my + 10 + (i // 4) * (cell_h + 4)
        b.append(rect(cx, cy, cell_w, cell_h, "#0a0a0c", 3, ramps[i][0], 1))
        b.append(text(str(i + 1), cx + 6, cy + 16, 9, ramps[i][0], "700"))
        for k, frag in enumerate(("· claude", "· ▌▌▌▌▌▌", "· ▌▌▌▌")):
            b.append(text(frag, cx + 6, cy + 30 + k * 11, 7.5, ramps[i][0],
                          opacity=0.34 - k * 0.08))
    # status row 0: windows, then row 1: panes of the current window
    sy = my + mh - 34
    b.append(rect(mx + 8, sy, mw - 16, 15, C235, 2))
    b.append(text(" dev ", mx + 12, sy + 11, 9.5, C114, "700"))
    b.append(text("1:zsh(8)", mx + 52, sy + 11, 9.5, C250))
    b.append(rect(mx + 108, sy + 1.5, 74, 12, C114, 2))
    b.append(text("2:claude(8)", mx + 112, sy + 11, 9.5, C235, "700"))
    b.append(text("Sep 12 15:58", mx + mw - 20, sy + 11, 9.5, C245, anchor="end"))
    sy += 17
    b.append(rect(mx + 8, sy, mw - 16, 15, C235, 2))
    px = mx + 12
    for i in range(8):
        w = 46
        active = (i == 1)
        b.append(rect(px, sy + 1.5, w, 12, C114 if active else C238, 2))
        b.append(text(f"{i+1}:claude", px + 4, sy + 11, 8.5, C235 if active else C250,
                      "700" if active else None))
        px += w + 3
    # Phone: the same pane, zoomed
    px0, py0, pw0, ph0 = 486, 28, 148, 244
    b.append(rect(px0, py0, pw0, ph0, "#0f0f12", 20, "#3a3a42", 1.5))
    b.append(rect(px0 + 52, py0 + 8, 44, 5, "#2a2a32", 3))
    b.append(rect(px0 + 8, py0 + 22, pw0 - 16, ph0 - 46, "#0a0a0c", 6, "#ff6a2b", 1))
    for i, line in enumerate(("$ claude", "▸ running the", "  simulator", "  matrix", "", "✓ 3 devices",
                              "✓ 155 passed")):
        b.append(text(line, px0 + 14, py0 + 42 + i * 15, 9, "#ff9d4d" if i == 0 else "#c8c8d0",
                      opacity=0.9 if i < 2 else 0.6))
    b.append(rect(px0 + 8, py0 + ph0 - 20, pw0 - 16, 13, C235, 2))
    b.append(text("2:claude", px0 + 14, py0 + ph0 - 10, 8.5, C114, "700"))
    b.append(text("alt-2 zooms", px0 + pw0 - 14, py0 + ph0 - 10, 8, C245, anchor="end"))
    b.append(text("Termius over Tailscale — detach, not death", 20, 262, 9.5, "#5a5a66"))
    return card("".join(b), "#08080a")


# ---------------------------------------------------------------- describatory
# A real before/after: this repo's own About line was empty until the tool ran.
def describatory_card():
    b = [text("ONE PASS · EVERY REPO · ONE VOICE", 20, 18, 9.5, "#5a5a66", "700")]
    b.append(rect(20, 30, 680, 120, "#0f0f12", 8, "#2a2a32", 1))
    b.append(text("BEFORE", 36, 52, 9.5, "#6a6a76", "700"))
    b.append(text("mattypark/statusline", 36, 74, 12, "#8a8a95"))
    b.append(text("About", 36, 100, 10.5, "#6a6a76"))
    b.append(text("(no description, website, or topics provided)", 92, 100, 11, "#4e4e58"))
    b.append(text("Topics", 36, 124, 10.5, "#6a6a76"))
    b.append(text("—", 92, 124, 11, "#4e4e58"))
    b.append(text("↓", 360, 166, 13, "#fa992e", "700", anchor="middle"))
    b.append(rect(20, 178, 680, 104, "#0f0f12", 8, "#3a3a42", 1))
    b.append(text("AFTER", 36, 200, 9.5, "#fa992e", "700"))
    for i, line in enumerate(("Colour-coded Claude Code status line — gradient project name, blue",
                              "model, green effort, orange-to-red tokens — plus a tmux painter that",
                              "gives every pane its own background so the line and its pane match.")):
        b.append(text(line, 36, 222 + i * 16, 11.5, "#e6e6ea"))
    topics = ["claude-code", "statusline", "tmux", "ansi-colors", "truecolor", "shell-script"]
    tx = 36
    for t in topics:
        tw = adv(9.5) * len(t) + 14
        b.append(rect(tx, 262, tw, 15, "#1e2a3a", 7, "#2f4667", 1))
        b.append(text(t, tx + 7, 273, 9.5, "#79b8ff"))
        tx += tw + 6
    return card("".join(b), "#08080a")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    write("statusline.svg", statusline_card())
    write("costpriority.svg", cost_card())
    write("organizepet.svg", organizepet_card())
    write("phone-terminals.svg", phone_card())
    write("describatory.svg", describatory_card())
