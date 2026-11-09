#!/usr/bin/env python3
"""Rust-in-AI moment kit: one theme, many animated graphics, uniform across episodes.

Turns a small JSON spec into AI Producer composition files (1920x1080) plus the host <div> lines for
index.html, a caption-window list and a sound-effect hint list.

  python3 series/rust-in-ai/kit/moments.py spec.json OUTDIR

OUTDIR gets:  compositions/<id>.html   hosts.html   caption_windows.json   sfx_hints.json

Spec (times are GLOBAL seconds on the finished cut; item "at" values are seconds from the moment's start):
{
  "moments": [
    {"id": "intro", "type": "title_card", "start": 0.3, "duration": 4.5, "title": "...", "kicker": "...", "sub": "..."},
    {"id": "cards", "type": "chip_cards", "start": 40, "duration": 12, "items": [{"name": "...", "role": "...", "tag": "...", "at": 1.0}]},
    ...
  ]
}
Types: title_card, chip_cards, compare, layers, code_card, flow, checklist, stat_compare, outro_next, lower_third,
statement, big_stat, bars, triple, spikes, stat_chip (soft light theme).
Full-cover types paint their own ground; lower_third is a transparent overlay.
Layout rule (landscape): payload lives between y=140 and y=690; captions sit at y~722-962 (position 78).
"""
import html
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------- theme tokens (keep in sync with THEME.md)
T = dict(
    ground="#e4efeb", ground_hi="#fbf6ef", panel="#ffffff", panel2="#f6eee5", line="#eadfd3",
    ink="#1c3a3f", mute="#5f7c80", dim="#9db3b4",
    accent="#ee7d45", accent_text="#df6a2f", accent_soft="#ffe3d3", teal="#2f9c8f", teal_soft="#d6eee9",
    bad="#e0626a", bad_soft="#fde1e3", good="#35b184", good_soft="#d7f2e6", python="#5b8def", python_soft="#dce7fd",
    code_bg="#1f2e3a", code_bar="#2a3b49", code_ink="#e9f0f5",
)
# Episode variants (spec "theme"): studio-red matches a white wall lit with a red lamp (008 on). Red is the one accent,
# slate replaces teal so nothing else competes with it.
THEMES = {"studio-red": dict(
    ground="#f3eeee", ground_hi="#ffffff", panel="#ffffff", panel2="#f4eded", line="#ecdede",
    ink="#22191b", mute="#6b5e61", dim="#b3a7a9",
    accent="#e0393b", accent_text="#c92d30", accent_soft="#fde0df", teal="#4d5966", teal_soft="#e3e7ec",
    bad="#b3262a", bad_soft="#f9dadb", good="#2f9e6f", good_soft="#d8f0e4",
    glow_a="rgba(235,70,70,.20)", glow_b="rgba(235,60,60,.30)", shadow="60,30,32"),
  # home-warm (009): living-room set: cream floor/wall ground, walnut ink, gold-trim amber accent (matches the #ffa726
  # proof marks), grey wall panels as the quiet second colour
  "home-warm": dict(
    ground="#f4ede3", ground_hi="#fffaf3", panel="#ffffff", panel2="#f7f0e6", line="#eadccb",
    ink="#2b1f17", mute="#6e5f52", dim="#b5a796",
    accent="#ee9a2a", accent_text="#b8700f", accent_soft="#fde9cc", teal="#5d6266", teal_soft="#e7e6e3",
    bad="#c4473f", bad_soft="#f8dcd8", good="#3c9a6a", good_soft="#dcefe3",
    glow_a="rgba(245,170,80,.30)", glow_b="rgba(150,115,85,.20)", shadow="70,50,30")}
T.update(glow_a="rgba(255,196,160,.42)", glow_b="rgba(150,214,198,.48)", shadow="40,70,70")
FONT_SANS = "'Geist', 'Helvetica Neue', Arial, sans-serif"
FONT_MONO = "'JetBrains Mono', 'SF Mono', Menlo, Consolas, monospace"

def _css():
    return f"""
.k-ground {{ position: absolute; inset: 0; background: radial-gradient(circle at 90% 8%, {T['glow_a']}, transparent 30%), radial-gradient(circle at 6% 94%, {T['glow_b']}, transparent 34%), radial-gradient(ellipse 75% 85% at 50% 42%, {T['ground_hi']} 0%, {T['ground']} 100%); }}
.k-kicker {{ font: 700 26px/1 {FONT_SANS}; letter-spacing: .16em; text-transform: uppercase; color: {T['accent_text']}; }}
.k-card {{ position: absolute; background: {T['panel']}; border: 2px solid {T['line']}; border-radius: 30px; box-shadow: 0 26px 60px rgba({T['shadow']},.14), 0 4px 14px rgba({T['shadow']},.07); }}
.k-name {{ font: 800 46px/1.05 {FONT_SANS}; color: {T['ink']}; }}
.k-role {{ font: 500 27px/1.25 {FONT_SANS}; color: {T['mute']}; }}
.k-tag {{ display: inline-block; font: 700 21px/1 {FONT_SANS}; letter-spacing: .06em; text-transform: uppercase; color: #ffffff; background: {T['accent']}; border-radius: 999px; padding: 8px 16px; }}
.k-title {{ font: 800 88px/1.04 {FONT_SANS}; color: {T['ink']}; letter-spacing: -2px; text-align: center; }}
.k-sub {{ font: 500 34px/1.3 {FONT_SANS}; color: {T['mute']}; text-align: center; }}
.k-mono {{ font-family: {FONT_MONO}; }}
.k-kw {{ color: #ffb184; }} .k-str {{ color: #8fe0b8; }} .k-cm {{ color: #7d93a6; }} .k-num {{ color: #8db4ff; }}
.k-center {{ position: absolute; left: 0; right: 0; display: flex; flex-direction: column; align-items: center; gap: 28px; }}
"""
CSS = _css()


def set_theme(name):
    global CSS
    if name:
        T.update(THEMES[name]); CSS = _css()

HEAD = '<template>\n  <div data-composition-id="{id}" data-width="1920" data-height="1080">\n    <style>{css}</style>\n'
TAIL = '    <script>\n      const root = document.querySelector(\'[data-composition-id="{id}"]\');\n      const Q = (s) => root.querySelector(s);\n      const QA = (s) => Array.from(root.querySelectorAll(s));\n      const tl = gsap.timeline({{ paused: true }});\n{js}\n      window.__timelines[\'{id}\'] = tl;\n    </script>\n  </div>\n</template>\n'

E = html.escape


def fade_js(m, ground=True):
    d = m["duration"]
    js = ""
    if ground and m.get("fade_in", True):
        js += "      tl.fromTo(Q('.k-ground'), { opacity: 0 }, { opacity: 1, duration: 0.25, ease: 'none' }, 0);\n"
    if m.get("fade_out", True):
        tgt = "[Q('.k-ground'), ...QA('.k-fade')]" if ground else "QA('.k-fade')"
        js += f"      tl.to({tgt}, {{ opacity: 0, duration: 0.25, ease: 'none' }}, {max(d - 0.25, 0.3):.2f});\n"
    return js


def highlight(code, lang):
    """Tiny syntax colouring: strings, comments, keywords, numbers."""
    kws = {
        "rust": "fn let mut pub use impl struct enum match if else for while loop return self Self mod crate async await move ref unsafe where trait type const static as in",
        "python": "def class import from as if elif else for while return with try except in is not and or None True False lambda async await yield pass",
        "shell": "cargo pip maturin docker run install build show",
        "c": "char int void return if else for while struct static const sizeof free malloc",
    }.get(lang, "")
    kw = set(kws.split())
    out = []
    for tok in re.findall(r'//.*$|#.*$|"[^"]*"|\'[^\']*\'|[A-Za-z_][A-Za-z_0-9]*!?|\d+|\s+|.', code):
        t = E(tok)
        if tok.startswith("//") or (tok.startswith("#") and lang != "rust"):
            out.append(f'<span class="k-cm">{t}</span>')
        elif tok[:1] in "\"'" and len(tok) > 1:
            out.append(f'<span class="k-str">{t}</span>')
        elif tok in kw:
            out.append(f'<span class="k-kw">{t}</span>')
        elif tok.isdigit():
            out.append(f'<span class="k-num">{t}</span>')
        else:
            out.append(t)
    return "".join(out)


# ---------------------------------------------------------------- component builders (return body_html, js, full_cover)
def title_card(m):
    body = f"""    <div class="k-ground"></div>
    <div class="k-center k-fade" style="top:190px">
      <div class="k-kicker" data-k="kick">{E(m.get('kicker', 'Rust in AI'))}</div>
      <div class="k-title" style="max-width:1560px" data-k="title">{E(m['title'])}</div>
      <div class="k-sub" data-k="sub">{E(m.get('sub', ''))}</div>
    </div>
"""
    js = fade_js(m) + """      tl.fromTo(Q('[data-k=kick]'), { opacity: 0, y: -16 }, { opacity: 1, y: 0, duration: 0.4, ease: 'power3.out' }, 0.2);
      tl.fromTo(Q('[data-k=title]'), { opacity: 0, y: 40, scale: 0.96 }, { opacity: 1, y: 0, scale: 1, duration: 0.6, ease: 'back.out(1.4)' }, 0.35);
      tl.fromTo(Q('[data-k=sub]'), { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.5, ease: 'power2.out' }, 0.9);
"""
    return body, js, True


def chip_cards(m):
    items = m["items"]; n = len(items)
    cols = min(n, 3) if n <= 3 else (2 if n == 4 else 3)
    rows = -(-n // cols)
    w = {1: 700, 2: 640, 3: 520}[cols]
    h = 250 if rows == 1 else 200
    gap = 36
    total_w = cols * w + (cols - 1) * gap
    x0 = (1920 - total_w) // 2
    total_h = rows * h + (rows - 1) * gap
    y0 = 140 + (550 - total_h) // 2 + (40 if m.get("heading") else 0)
    cards = []
    for i, it in enumerate(items):
        r, c = divmod(i, cols)
        # centre a short last row
        in_row = min(cols, n - r * cols)
        off = (cols - in_row) * (w + gap) // 2 if r == rows - 1 else 0
        cards.append(f"""    <div class="k-card k-fade" data-k="card" style="left:{x0 + c * (w + gap) + off}px;top:{y0 + r * (h + gap)}px;width:{w}px;height:{h}px;padding:30px 34px;box-sizing:border-box;display:flex;flex-direction:column;justify-content:space-between">
      <div class="k-name">{E(it['name'])}</div>
      <div class="k-role">{E(it.get('role', ''))}</div>
      <div>{f'<span class="k-tag">{E(it["tag"])}</span>' if it.get('tag') else ''}</div>
    </div>""")
    head = ""
    if m.get("heading"):
        head = f'    <div class="k-kicker k-fade" data-k="head" style="position:absolute;left:0;right:0;top:130px;text-align:center">{E(m["heading"])}</div>\n'
    ats = [float(it.get("at", 0.6 + 0.5 * i)) for i, it in enumerate(items)]
    js = fade_js(m) + f"      const AT = {json.dumps(ats)};\n"
    if head:
        js += "      tl.fromTo(Q('[data-k=head]'), { opacity: 0, y: -14 }, { opacity: 1, y: 0, duration: 0.35, ease: 'power3.out' }, 0.15);\n"
    js += "      QA('[data-k=card]').forEach((el, i) => tl.fromTo(el, { opacity: 0, y: 46, scale: 0.92 }, { opacity: 1, y: 0, scale: 1, duration: 0.4, ease: 'back.out(1.6)' }, AT[i]));\n"
    return '    <div class="k-ground"></div>\n' + head + "\n".join(cards) + "\n", js, True


def compare(m):
    def col(side, x):
        c = m[side]; tone = c.get("tone", "good" if side == "right" else "bad")
        colr = T["good"] if tone == "good" else T["bad"]
        mark = "&#10003;" if tone == "good" else "&#10005;"
        lis = "".join(f'<div class="k-row" data-k="{side}-item"><span style="color:{colr};font-weight:800;margin-right:16px">{mark}</span>{E(t)}</div>' for t in c["items"])
        return f"""    <div class="k-card k-fade" data-k="{side}" style="left:{x}px;top:160px;width:790px;min-height:470px;padding:38px 44px;box-sizing:border-box;border-color:{colr}66">
      <div class="k-name" style="color:{colr};margin-bottom:26px">{E(c['title'])}</div>
      {lis}
    </div>"""
    body = ('    <div class="k-ground"></div>\n    <style>.k-row{font:500 32px/1.3 ' + FONT_SANS + ';color:' + T['ink'] + ';margin:0 0 18px}</style>\n'
            + col("left", 120) + "\n" + col("right", 1010) + "\n")
    al, ar = float(m.get("at_left", 0.4)), float(m.get("at_right", 2.2))
    js = fade_js(m) + f"""      tl.fromTo(Q('[data-k=left]'), {{ opacity: 0, x: -60 }}, {{ opacity: 1, x: 0, duration: 0.5, ease: 'power3.out' }}, {al});
      QA('[data-k=left-item]').forEach((el, i) => tl.fromTo(el, {{ opacity: 0, x: -20 }}, {{ opacity: 1, x: 0, duration: 0.3, ease: 'power2.out' }}, {al} + 0.35 + i * {float(m.get('item_gap', 0.35))}));
      tl.fromTo(Q('[data-k=right]'), {{ opacity: 0, x: 60 }}, {{ opacity: 1, x: 0, duration: 0.5, ease: 'power3.out' }}, {ar});
      QA('[data-k=right-item]').forEach((el, i) => tl.fromTo(el, {{ opacity: 0, x: 20 }}, {{ opacity: 1, x: 0, duration: 0.3, ease: 'power2.out' }}, {ar} + 0.35 + i * {float(m.get('item_gap', 0.35))}));
"""
    return body, js, True


def layers(m):
    ls = m["layers"]; n = len(ls)
    h = 112; gap = 18; total = n * h + (n - 1) * gap; y0 = 150 + (540 - total) // 2
    rows = []
    for i, l in enumerate(ls):
        rows.append(f"""    <div class="k-card k-fade" data-k="layer" style="left:260px;top:{y0 + i * (h + gap)}px;width:1400px;height:{h}px;padding:0 40px;box-sizing:border-box;display:flex;align-items:center;gap:34px">
      <div class="k-kicker" style="min-width:150px;color:{T['mute']}" data-k="num">{E(l['name'])}</div>
      <div style="flex:1"><div class="k-name" style="font-size:38px">{E(l['sub'])}</div><div class="k-role" style="font-size:25px;margin-top:6px">{E(l.get('tools', ''))}</div></div>
    </div>""")
    hl = m.get("highlight", [{"index": i, "at": 1.0 + 1.5 * i} for i in range(n)])
    js = fade_js(m) + f"      const HL = {json.dumps(hl)};\n      const L = QA('[data-k=layer]');\n"
    js += "      L.forEach((el, i) => tl.fromTo(el, { opacity: 0, x: -50 }, { opacity: 0.55, x: 0, duration: 0.4, ease: 'power3.out' }, 0.2 + i * 0.12));\n"
    js += f"""      HL.forEach((h, k) => {{
        tl.to(L[h.index], {{ opacity: 1, borderColor: '{T['accent']}', scale: 1.03, duration: 0.3, ease: 'power2.out' }}, h.at);
        tl.to(QA('[data-k=num]')[h.index], {{ color: '{T['accent']}', duration: 0.3 }}, h.at);
        if (k < HL.length - 1 || {str(m.get('dim_last', True)).lower()}) tl.to(L[h.index], {{ opacity: 0.55, borderColor: '{T['line']}', scale: 1, duration: 0.3, ease: 'power2.inOut' }}, (HL[k + 1] ? HL[k + 1].at : {m['duration'] - 0.6}) - 0.05);
      }});
"""
    return '    <div class="k-ground"></div>\n' + "\n".join(rows) + "\n", js, True


def code_card(m):
    lang = m.get("lang", "rust"); lines = m["lines"]
    rows = []; js_rows = ""
    for i, ln in enumerate(lines):
        if isinstance(ln, str):
            ln = {"t": ln}
        code = ln["t"]; n = len(code)
        cls = " k-err" if ln.get("err") else ""
        rows.append(f'      <div class="k-line{cls}" data-k="line"><span class="k-lno">{i + 1}</span><span class="k-typed" style="width:{n}ch" data-n="{n}">{highlight(code, lang)}</span></div>')
        at = float(ln.get("at", 0.4 + 0.7 * i)); dur = float(ln.get("dur", max(0.4, n * 0.035)))
        if ln.get("out"):   # output line: fades in whole, muted colour
            js_rows += f"      tl.fromTo(QA('[data-k=line]')[{i}], {{ opacity: 0 }}, {{ opacity: 1, duration: 0.3 }}, {at});\n      tl.set(QA('.k-typed')[{i}], {{ width: '{n}ch', color: '{ln.get("col", "#b7c6d3")}' }}, 0);\n"
        else:
            js_rows += f"      tl.fromTo(QA('.k-typed')[{i}], {{ width: '0ch' }}, {{ width: '{n}ch', duration: {dur:.2f}, ease: 'steps({n})' }}, {at});\n"
        if ln.get("hl"):
            js_rows += f"      tl.to(QA('[data-k=line]')[{i}], {{ backgroundColor: 'rgba(238,125,69,0.55)', duration: 0.35 }}, {float(ln['hl'])});\n"
        if ln.get("flag"):
            js_rows += f"      tl.to(QA('[data-k=line]')[{i}], {{ backgroundColor: 'rgba(255,120,120,0.28)', duration: 0.3 }}, {float(ln['flag'])});\n"
    n_l = len(lines); fs = 50 if n_l <= 4 else (42 if n_l <= 6 else 34); lh = int(fs * 1.55)
    ch = 58 + 36 * 2 + n_l * lh
    w = 1320
    body = f"""    <div class="k-ground"></div>
    <style>.k-line{{display:flex;font:500 {fs}px/{lh}px {FONT_MONO};color:{T['code_ink']};white-space:pre;border-radius:8px;padding:0 10px;margin:0 -10px}}.k-lno{{width:64px;color:#7d93a6}}.k-typed{{display:inline-block;overflow:hidden;white-space:pre}}</style>
    <div class="k-card k-fade" style="left:{(1920 - w) // 2}px;top:{150 + max(0, (520 - ch) // 2)}px;width:{w}px;height:{ch}px;overflow:hidden;background:{T['code_bg']}" data-k="card">
      <div style="height:58px;background:{T['code_bar']};display:flex;align-items:center;padding:0 24px;gap:12px"><span style="width:16px;height:16px;border-radius:50%;background:#5d7385"></span><span style="width:16px;height:16px;border-radius:50%;background:#5d7385"></span><span style="width:16px;height:16px;border-radius:50%;background:#5d7385"></span><span class="k-mono" style="margin-left:18px;font-size:24px;color:{T['mute']}">{E(m.get('file', 'main.rs'))}</span></div>
      <div style="padding:36px 40px">
{chr(10).join(rows)}
      </div>
    </div>
"""
    js = fade_js(m) + "      tl.fromTo(Q('[data-k=card]'), { opacity: 0, y: 40 }, { opacity: 1, y: 0, duration: 0.45, ease: 'power3.out' }, 0.05);\n" + js_rows
    return body, js, True


def flow(m):
    ns = m["nodes"]; n = len(ns)
    w = 330 if n <= 4 else 270; gap = (1680 - n * w) // max(n - 1, 1) if n > 1 else 0
    gap = min(gap, 150); total = n * w + (n - 1) * gap; x0 = (1920 - total) // 2; y = 300
    nodes, arrows = [], []
    for i, nd in enumerate(ns):
        tone = nd.get("tone", "")
        col = {"bad": T["bad"], "good": T["good"]}.get(tone, T["line"])
        nodes.append(f"""    <div class="k-card k-fade" data-k="node" style="left:{x0 + i * (w + gap)}px;top:{y}px;width:{w}px;height:190px;border-color:{col};display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;text-align:center;padding:0 18px;box-sizing:border-box">
      <div class="k-name" style="font-size:38px">{E(nd['label'])}</div><div class="k-role" style="font-size:24px">{E(nd.get('sub', ''))}</div></div>""")
        if i < n - 1:
            arrows.append(f'    <div class="k-fade" data-k="arrow" style="position:absolute;left:{x0 + i * (w + gap) + w + 8}px;top:{y + 86}px;width:{gap - 16}px;height:6px;border-radius:3px;background:{T["accent"]};transform-origin:0 50%"></div>')
    ats = [float(nd.get("at", 0.6 + 0.9 * i)) for i, nd in enumerate(ns)]
    js = fade_js(m) + f"      const AT = {json.dumps(ats)};\n"
    js += "      const ND = QA('[data-k=node]'), AR = QA('[data-k=arrow]');\n"
    js += "      ND.forEach((el, i) => tl.fromTo(el, { opacity: 0, y: 40, scale: 0.9 }, { opacity: 1, y: 0, scale: 1, duration: 0.4, ease: 'back.out(1.6)' }, AT[i]));\n"
    js += "      AR.forEach((el, i) => tl.fromTo(el, { opacity: 0, scaleX: 0 }, { opacity: 1, scaleX: 1, duration: 0.3, ease: 'power2.out' }, AT[i + 1] - 0.25));\n"
    head = f'    <div class="k-kicker k-fade" data-k="head" style="position:absolute;left:0;right:0;top:150px;text-align:center">{E(m["heading"])}</div>\n' if m.get("heading") else ""
    if head:
        js += "      tl.fromTo(Q('[data-k=head]'), { opacity: 0, y: -14 }, { opacity: 1, y: 0, duration: 0.35, ease: 'power3.out' }, 0.1);\n"
    return '    <div class="k-ground"></div>\n' + head + "\n".join(arrows) + "\n" + "\n".join(nodes) + "\n", js, True


def checklist(m):
    its = m["items"]; n = len(its)
    h = 150 if n <= 3 else 120; gap = 24; total = n * h + (n - 1) * gap; y0 = 150 + (540 - total) // 2
    rows = []
    for i, it in enumerate(its):
        rows.append(f"""    <div class="k-card k-fade" data-k="item" style="left:260px;top:{y0 + i * (h + gap)}px;width:1400px;height:{h}px;padding:0 44px;box-sizing:border-box;display:flex;align-items:center;gap:36px">
      <div style="width:76px;height:76px;border-radius:50%;background:{T['accent']};color:#fff;font:800 44px/76px {FONT_SANS};text-align:center;flex:none">{E(str(it.get('n', i + 1)))}</div>
      <div><div class="k-name" style="font-size:42px">{E(it['text'])}</div><div class="k-role" style="font-size:27px;margin-top:6px">{E(it.get('sub', ''))}</div></div>
    </div>""")
    ats = [float(it.get("at", 0.6 + 1.2 * i)) for i, it in enumerate(its)]
    js = fade_js(m) + f"      const AT = {json.dumps(ats)};\n      QA('[data-k=item]').forEach((el, i) => tl.fromTo(el, {{ opacity: 0, x: -60 }}, {{ opacity: 1, x: 0, duration: 0.45, ease: 'power3.out' }}, AT[i]));\n"
    return '    <div class="k-ground"></div>\n' + "\n".join(rows) + "\n", js, True


def stat_compare(m):
    a, b = m["left"], m["right"]
    def side(s, x, col, k):
        return f"""    <div class="k-fade" data-k="{k}" style="position:absolute;left:{x}px;top:200px;width:700px;text-align:center">
      <div style="font:900 190px/1 {FONT_SANS};color:{col};letter-spacing:-6px">{E(s['value'])}</div>
      <div class="k-name" style="margin-top:22px">{E(s['label'])}</div>
      <div class="k-role" style="margin-top:8px">{E(s.get('sub', ''))}</div>
    </div>"""
    tc = lambda t, d: {"bad": T["bad"], "good": T["good"], "accent": T["accent"], "teal": T["teal"]}.get(t, d)
    body = ('    <div class="k-ground"></div>\n' + side(a, 150, tc(a.get("tone"), T["bad"]), "a")
            + f'\n    <div class="k-fade k-kicker" data-k="vs" style="position:absolute;left:880px;top:310px;width:160px;text-align:center;font-size:40px;color:{T["mute"]}">{E(m.get("vs", "VS"))}</div>\n'
            + side(b, 1070, tc(b.get("tone"), T["good"]), "b") + "\n")
    js = fade_js(m) + f"""      tl.fromTo(Q('[data-k=a]'), {{ opacity: 0, y: 50 }}, {{ opacity: 1, y: 0, duration: 0.5, ease: 'power3.out' }}, {float(m.get('at_left', 0.4))});
      tl.fromTo(Q('[data-k=vs]'), {{ opacity: 0, scale: 0.6 }}, {{ opacity: 1, scale: 1, duration: 0.3, ease: 'back.out(2)' }}, {float(m.get('at_right', 2.0)) - 0.3});
      tl.fromTo(Q('[data-k=b]'), {{ opacity: 0, y: 50 }}, {{ opacity: 1, y: 0, duration: 0.5, ease: 'power3.out' }}, {float(m.get('at_right', 2.0))});
"""
    return body, js, True


def outro_next(m):
    body = f"""    <div class="k-ground"></div>
    <div class="k-center k-fade" style="top:220px">
      <div class="k-kicker" data-k="kick">{E(m.get('kicker', 'Next episode'))}</div>
      <div class="k-title" style="max-width:1500px;font-size:80px" data-k="title">{E(m['title'])}</div>
      <div class="k-sub" data-k="sub">{E(m.get('sub', 'Subscribe so you do not miss it'))}</div>
    </div>
"""
    js = fade_js(m) + """      tl.fromTo(Q('[data-k=kick]'), { opacity: 0, y: -16 }, { opacity: 1, y: 0, duration: 0.4, ease: 'power3.out' }, 0.2);
      tl.fromTo(Q('[data-k=title]'), { opacity: 0, y: 40 }, { opacity: 1, y: 0, duration: 0.55, ease: 'back.out(1.4)' }, 0.4);
      tl.fromTo(Q('[data-k=sub]'), { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.45, ease: 'power2.out' }, 1.0);
"""
    return body, js, True


def lower_third(m):
    side = m.get("pos", "left")
    pos = "left:90px" if side == "left" else "right:90px"
    body = f"""    <div class="k-fade" data-k="lt" style="position:absolute;{pos};top:84px;padding:20px 30px;background:rgba(255,255,255,.94);border-left:8px solid {T['accent']};border-radius:18px;box-shadow:0 14px 36px rgba(30,50,60,.28);max-width:640px">
      <div class="k-name" style="font-size:40px">{E(m['title'])}</div>
      <div class="k-role" style="font-size:24px;margin-top:6px;font-family:{FONT_MONO}">{E(m.get('sub', ''))}</div>
    </div>
"""
    d = m["duration"]
    off = "-80" if side == "left" else "80"
    js = (f"      tl.fromTo(Q('[data-k=lt]'), {{ opacity: 0, x: {off} }}, {{ opacity: 1, x: 0, duration: 0.4, ease: 'power3.out' }}, 0.05);\n"
          f"      tl.to(Q('[data-k=lt]'), {{ opacity: 0, x: {off}, duration: 0.3, ease: 'power2.in' }}, {max(d - 0.35, 0.5):.2f});\n")
    return body, js, False


# ---------------------------------------------------------------- v2 builders (soft light theme)
def _words(text, hl):
    hl = {h.lower() for h in hl}
    out = []
    for w in text.split():
        bare = re.sub(r"[^A-Za-z0-9+#]", "", w).lower()
        cls = "k-w k-hl" if bare in hl else "k-w"
        out.append(f'<span class="{cls}" style="display:inline-block;margin:0 .14em">{E(w)}</span>')
    return " ".join(out)


def statement(m):
    size = m.get("size", 104)
    body = f"""    <div class="k-ground"></div>
    <style>.k-hl{{color:{T['accent_text']}}}</style>
    <div class="k-center k-fade" style="top:{m.get('top', 250)}px">
      {f'<div class="k-kicker" data-k="kick">{E(m["kicker"])}</div>' if m.get('kicker') else ''}
      <div style="font:800 {size}px/1.08 {FONT_SANS};color:{T['ink']};letter-spacing:-2px;text-align:center;max-width:1560px" data-k="text">{_words(m['text'], m.get('hl', []))}</div>
      {f'<div class="k-sub" data-k="sub">{E(m["sub"])}</div>' if m.get('sub') else ''}
    </div>
"""
    js = fade_js(m)
    if m.get("kicker"):
        js += "      tl.fromTo(Q('[data-k=kick]'), { opacity: 0, y: -14 }, { opacity: 1, y: 0, duration: 0.4, ease: 'power3.out' }, 0.1);\n"
    js += "      tl.fromTo(QA('.k-w'), { opacity: 0, y: 36, rotateX: -35 }, { opacity: 1, y: 0, rotateX: 0, duration: 0.5, ease: 'back.out(1.5)', stagger: 0.07 }, 0.25);\n"
    js += "      tl.fromTo(QA('.k-hl'), { scale: 1 }, { scale: 1.08, duration: 0.35, ease: 'power2.inOut', yoyo: true, repeat: 1 }, 0.9);\n"
    if m.get("sub"):
        js += f"      tl.fromTo(Q('[data-k=sub]'), {{ opacity: 0, y: 18 }}, {{ opacity: 1, y: 0, duration: 0.5, ease: 'power2.out' }}, {float(m.get('sub_at', 1.0))});\n"
    return body, js, True


def big_stat(m):
    tone = {"bad": T["bad"], "good": T["good"], "accent": T["accent"], "teal": T["teal"]}.get(m.get("tone", "accent"), T["accent"])
    dec = int(m.get("decimals", 0)); a, b = float(m.get("from", 0)), float(m["to"])
    body = f"""    <div class="k-ground"></div>
    <div class="k-center k-fade" style="top:{m.get('top', 215)}px;gap:18px">
      {f'<div class="k-kicker" data-k="kick">{E(m["kicker"])}</div>' if m.get('kicker') else ''}
      <div data-k="num" style="font:900 {m.get('size', 280)}px/1 {FONT_SANS};color:{tone};letter-spacing:-8px"><span data-k="pre">{E(m.get('prefix', ''))}</span><span data-k="val">{a:.{dec}f}</span><span data-k="suf" style="font-size:.5em;letter-spacing:-2px">{E(m.get('suffix', ''))}</span></div>
      <div class="k-name" style="font-size:48px;text-align:center;max-width:1400px" data-k="label">{E(m['label'])}</div>
      {f'<div class="k-sub" data-k="sub" style="font-size:30px">{E(m["sub"])}</div>' if m.get('sub') else ''}
    </div>
"""
    at, dur = float(m.get("at", 0.5)), float(m.get("count", 1.6))
    js = fade_js(m)
    if m.get("kicker"):
        js += "      tl.fromTo(Q('[data-k=kick]'), { opacity: 0, y: -14 }, { opacity: 1, y: 0, duration: 0.4, ease: 'power3.out' }, 0.1);\n"
    js += f"""      tl.fromTo(Q('[data-k=num]'), {{ opacity: 0, scale: 0.8 }}, {{ opacity: 1, scale: 1, duration: 0.5, ease: 'back.out(1.6)' }}, {at - 0.1});
      const C = {{ v: {a} }};
      tl.to(C, {{ v: {b}, duration: {dur}, ease: 'power2.out', onUpdate: () => {{ Q('[data-k=val]').textContent = Number(C.v.toFixed({dec})).toLocaleString('en-US', {{ minimumFractionDigits: {dec}, maximumFractionDigits: {dec} }}); }} }}, {at});
      tl.fromTo(Q('[data-k=label]'), {{ opacity: 0, y: 20 }}, {{ opacity: 1, y: 0, duration: 0.5, ease: 'power2.out' }}, {at + 0.5});
"""
    if m.get("sub"):
        js += f"      tl.fromTo(Q('[data-k=sub]'), {{ opacity: 0, y: 16 }}, {{ opacity: 1, y: 0, duration: 0.5, ease: 'power2.out' }}, {at + 1.0});\n"
    return body, js, True


def bars(m):
    rows = m["rows"]; n = len(rows)
    h = 120; gap = 34; total = n * h + (n - 1) * gap; y0 = 175 + (500 - total) // 2
    out = []
    for i, r in enumerate(rows):
        col = {"bad": T["bad"], "good": T["good"], "accent": T["accent"], "teal": T["teal"]}.get(r.get("tone", "accent"), T["accent"])
        w = 1000 * float(r["value"]) / 100
        out.append(f"""    <div class="k-fade" data-k="row" style="position:absolute;left:150px;top:{y0 + i * (h + gap)}px;width:1620px;height:{h}px;display:flex;align-items:center;gap:36px">
      <div class="k-name" style="width:330px;font-size:40px;text-align:right">{E(r['label'])}</div>
      <div style="position:relative;width:1000px;height:78px;border-radius:39px;background:{T['panel2']};box-shadow:inset 0 2px 6px rgba(40,70,70,.08)">
        <div data-k="fill" data-w="{w:.0f}" style="position:absolute;left:0;top:0;height:78px;width:0;border-radius:39px;background:{col}"></div></div>
      <div data-k="val" style="font:900 64px/1 {FONT_SANS};color:{col};min-width:160px">{E(r['text'])}</div>
    </div>""")
    head = f'    <div class="k-kicker k-fade" data-k="head" style="position:absolute;left:0;right:0;top:130px;text-align:center">{E(m["heading"])}</div>\n' if m.get("heading") else ""
    ats = [float(r.get("at", 0.6 + 1.4 * i)) for i, r in enumerate(rows)]
    js = fade_js(m) + f"      const AT = {json.dumps(ats)};\n"
    if head:
        js += "      tl.fromTo(Q('[data-k=head]'), { opacity: 0, y: -14 }, { opacity: 1, y: 0, duration: 0.35, ease: 'power3.out' }, 0.1);\n"
    js += """      QA('[data-k=row]').forEach((el, i) => {
        tl.fromTo(el, { opacity: 0, x: -40 }, { opacity: 1, x: 0, duration: 0.4, ease: 'power3.out' }, AT[i]);
        const f = el.querySelector('[data-k=fill]');
        tl.fromTo(f, { width: 0 }, { width: +f.dataset.w, duration: 0.9, ease: 'power3.out' }, AT[i] + 0.2);
        tl.fromTo(el.querySelector('[data-k=val]'), { opacity: 0, scale: 0.7 }, { opacity: 1, scale: 1, duration: 0.4, ease: 'back.out(2)' }, AT[i] + 0.8);
      });
"""
    return '    <div class="k-ground"></div>\n' + head + "\n".join(out) + "\n", js, True


def triple(m):
    its = m["items"]; n = len(its); gap = 40
    w = {2: 780, 3: 540, 4: 410}[n]; h = m.get("h", 380)
    x0 = (1920 - (n * w + (n - 1) * gap)) // 2; y0 = 150 + (540 - h) // 2 + (30 if m.get("heading") else 0)
    cards = []
    for i, it in enumerate(its):
        tone = it.get("tone", "accent")
        col = {"bad": T["bad"], "good": T["good"], "accent": T["accent"], "teal": T["teal"], "python": T["python"]}[tone]
        soft = {"bad": T["bad_soft"], "good": T["good_soft"], "accent": T["accent_soft"], "teal": T["teal_soft"], "python": T["python_soft"]}[tone]
        cards.append(f"""    <div class="k-card k-fade" data-k="card" style="left:{x0 + i * (w + gap)}px;top:{y0}px;width:{w}px;height:{h}px;padding:36px;box-sizing:border-box;display:flex;flex-direction:column;gap:20px;align-items:flex-start">
      <div style="width:84px;height:84px;border-radius:26px;background:{soft};color:{col};font:800 46px/84px {FONT_SANS};text-align:center">{E(it.get('icon', str(i + 1)))}</div>
      <div class="k-name" style="font-size:{it.get('size', 44)}px">{E(it['title'])}</div>
      <div class="k-role" style="font-size:28px">{E(it.get('sub', ''))}</div>
    </div>""")
    head = f'    <div class="k-kicker k-fade" data-k="head" style="position:absolute;left:0;right:0;top:128px;text-align:center">{E(m["heading"])}</div>\n' if m.get("heading") else ""
    ats = [float(it.get("at", 0.6 + 1.0 * i)) for i, it in enumerate(its)]
    js = fade_js(m) + f"      const AT = {json.dumps(ats)};\n"
    if head:
        js += "      tl.fromTo(Q('[data-k=head]'), { opacity: 0, y: -14 }, { opacity: 1, y: 0, duration: 0.35, ease: 'power3.out' }, 0.1);\n"
    js += "      QA('[data-k=card]').forEach((el, i) => tl.fromTo(el, { opacity: 0, y: 60, scale: 0.9, rotateX: -12 }, { opacity: 1, y: 0, scale: 1, rotateX: 0, duration: 0.5, ease: 'back.out(1.5)' }, AT[i]));\n"
    return '    <div class="k-ground"></div>\n' + head + "\n".join(cards) + "\n", js, True


def spikes(m):
    import math
    W, H = 1360, 360
    n = 120; pts = []
    peaks = m.get("peaks", [0.22, 0.52, 0.82])
    for i in range(n + 1):
        x = i / n; y = 0.16 + 0.05 * math.sin(i * 0.9)
        for pk in peaks:
            d = abs(x - pk)
            if d < 0.035: y += (0.035 - d) / 0.035 * 0.62
        pts.append((x * W, H - 30 - y * (H - 60)))
    path = "M" + " L".join(f"{a:.1f},{b:.1f}" for a, b in pts)
    flat = "M" + " L".join(f"{x * W / n:.1f},{H - 30 - (0.16 + 0.012 * math.sin(x * 0.9)) * (H - 60):.1f}" for x in range(n + 1))
    fx = float(m.get("fix_at", 6.5))
    body = f"""    <div class="k-ground"></div>
    <div class="k-card k-fade" data-k="card" style="left:260px;top:175px;width:1400px;height:500px;padding:34px 20px 20px;box-sizing:border-box">
      <div style="display:flex;justify-content:space-between;padding:0 30px"><div class="k-name" style="font-size:38px" data-k="t1">{E(m.get('label', 'Latency'))}</div><div class="k-tag" data-k="b1" style="background:{T['bad']}">{E(m.get('bad_tag', 'Go · garbage collector'))}</div><div class="k-tag" data-k="b2" style="background:{T['good']};position:absolute;right:50px;top:36px;opacity:0">{E(m.get('good_tag', 'Rust'))}</div></div>
      <svg viewBox="0 0 {W} {H}" width="1360" height="360" style="margin:22px 20px 0">
        <line x1="0" y1="{H - 30}" x2="{W}" y2="{H - 30}" stroke="{T['line']}" stroke-width="3"/>
        <path data-k="bad" d="{path}" fill="none" stroke="{T['bad']}" stroke-width="7" stroke-linejoin="round" stroke-linecap="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"/>
        <path data-k="good" d="{flat}" fill="none" stroke="{T['good']}" stroke-width="7" stroke-linecap="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"/>
      </svg>
      <div class="k-role" data-k="cap" style="position:absolute;left:60px;bottom:26px;font-size:27px">{E(m.get('caption', 'A spike about every two minutes'))}</div>
    </div>
"""
    js = fade_js(m) + f"""      tl.fromTo(Q('[data-k=card]'), {{ opacity: 0, y: 40 }}, {{ opacity: 1, y: 0, duration: 0.45, ease: 'power3.out' }}, 0.05);
      tl.to(Q('[data-k=bad]'), {{ strokeDashoffset: 0, duration: {max(fx - 1.2, 1):.2f}, ease: 'none' }}, 0.5);
      tl.to(Q('[data-k=bad]'), {{ opacity: 0.12, duration: 0.4 }}, {fx});
      tl.to([Q('[data-k=b1]'), Q('[data-k=cap]')], {{ opacity: 0, duration: 0.3 }}, {fx});
      tl.to(Q('[data-k=b2]'), {{ opacity: 1, duration: 0.4 }}, {fx + 0.2});
      tl.to(Q('[data-k=good]'), {{ strokeDashoffset: 0, duration: 1.2, ease: 'power2.out' }}, {fx + 0.2});
"""
    return body, js, True


def stat_chip(m):
    pos = "right:110px" if m.get("pos", "right") == "right" else "left:110px"
    body = f"""    <div class="k-fade" data-k="chip" style="position:absolute;{pos};top:{m.get('top', 120)}px;padding:26px 38px;background:rgba(255,255,255,.95);border-radius:28px;box-shadow:0 18px 44px rgba(30,50,60,.3);text-align:center">
      <div class="k-kicker" style="font-size:22px">{E(m.get('kicker', ''))}</div>
      <div style="font:900 78px/1.05 {FONT_SANS};color:{T['ink']};margin-top:10px"><span data-k="from" style="color:{T['bad']};text-decoration:line-through;text-decoration-thickness:6px">{E(m['from'])}</span> <span style="color:{T['dim']}">&rarr;</span> <span data-k="to" style="color:{T['good']}">{E(m['to'])}</span></div>
    </div>
"""
    d = m["duration"]
    js = (f"      tl.fromTo(Q('[data-k=chip]'), {{ opacity: 0, y: -40, scale: 0.9 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.45, ease: 'back.out(1.7)' }}, 0.05);\n"
          f"      tl.fromTo(Q('[data-k=to]'), {{ scale: 0.6, opacity: 0 }}, {{ scale: 1, opacity: 1, duration: 0.4, ease: 'back.out(2.4)' }}, {float(m.get('at_to', 0.9))});\n"
          f"      tl.to(Q('[data-k=chip]'), {{ opacity: 0, y: -30, duration: 0.3, ease: 'power2.in' }}, {max(d - 0.35, 0.6):.2f});\n")
    return body, js, False


BUILDERS = dict(title_card=title_card, chip_cards=chip_cards, compare=compare, layers=layers, code_card=code_card,
                flow=flow, checklist=checklist, stat_compare=stat_compare, outro_next=outro_next, lower_third=lower_third, statement=statement, big_stat=big_stat, bars=bars, triple=triple, spikes=spikes, stat_chip=stat_chip)

SFX_HINT = dict(statement="whoosh", big_stat="riser", bars="whoosh", triple="pop-per-card", spikes="whoosh", stat_chip="pop", title_card="whoosh", chip_cards="pop-per-card", compare="whoosh", layers="whoosh", code_card="whoosh",
                flow="pop-per-node", checklist="pop-per-item", stat_compare="whoosh", outro_next="whoosh", lower_third="pop")


def build(spec, out):
    set_theme(spec.get("theme"))
    out = Path(out); (out / "compositions").mkdir(parents=True, exist_ok=True)
    hosts, caps, sfx = [], [], []
    prev_end = None
    for m in spec["moments"]:
        cid = "m-" + re.sub(r"[^a-z0-9-]", "-", m["id"].lower())
        if m["type"] not in BUILDERS:
            raise SystemExit(f"unknown type {m['type']}")
        m = dict(m)
        body, js, full = BUILDERS[m["type"]](m)
        text = HEAD.format(id=cid, css=CSS) + body + TAIL.format(id=cid, js=js.rstrip("\n"))
        f = out / "compositions" / f"{cid}.html"
        if not f.exists() or f.read_text() != text: f.write_text(text)   # unchanged graphics keep their mtime, so the local renderer reuses them
        title = m.get("label") or m.get("title") or m["id"]
        hosts.append(f'      <div class="visual-host clip" data-composition-id="{cid}" data-title="{E(str(title))[:48]}" data-composition-src="compositions/{cid}.html" data-start="{m["start"]:g}" data-duration="{m["duration"]:g}" data-track-index="3" data-width="1920" data-height="1080" data-hide-captions="false" data-caption-position="{m.get("caption_pos", 78)}"{'' if not full else ' data-caption-ink="' + T['ink'] + '"'}></div>')
        caps.append({"start": m["start"], "end": round(m["start"] + m["duration"], 3), "position": m.get("caption_pos", 78), **({"ink": T["ink"]} if full else {})})
        sfx.append({"id": cid, "type": m["type"], "start": m["start"], "hint": SFX_HINT[m["type"]], "full_cover": full})
        end = m["start"] + m["duration"]
        if prev_end is not None and m["start"] < prev_end - 1e-6:
            print(f"WARNING: {m['id']} overlaps the previous moment (track 3 clips cannot overlap)")
        prev_end = end
        if len(text.encode()) > 60000:
            print(f"WARNING: {cid}.html is near the 64 KiB limit")
    (out / "hosts.html").write_text("\n".join(hosts) + "\n")
    (out / "caption_windows.json").write_text(json.dumps(caps, indent=1))
    (out / "sfx_hints.json").write_text(json.dumps(sfx, indent=1))
    print(f"built {len(hosts)} moments -> {out}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    build(json.loads(Path(sys.argv[1]).read_text()), sys.argv[2])
