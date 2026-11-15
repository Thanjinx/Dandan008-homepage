#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 content.json 渲染成 index.html。

只改文字就改 content.json（或用 编辑.bat 打开编辑页），不要手改 index.html——
手改的内容下次渲染会被覆盖。

用法：
    python build.py          # 生成 index.html
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content.json"
OUTPUT = ROOT / "index.html"


def esc(text):
    """HTML 转义，避免手滑写出标签把页面搞坏。"""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render(data):
    site = data.get("site", {})
    hero = data.get("hero", {})
    about = data.get("about", {})
    work = data.get("work", {})
    links = data.get("links", {})

    nav_html = "\n".join(
        '      <a href="{}">{}</a>'.format(esc(i.get("href", "#")), esc(i.get("label", "")))
        for i in data.get("nav", [])
    )

    buttons_html = "\n".join(
        '      <a class="btn {}" href="{}">{}</a>'.format(
            esc(b.get("style", "ghost")), esc(b.get("href", "#")), esc(b.get("label", ""))
        )
        for b in hero.get("buttons", [])
    )

    paragraphs_html = "\n".join(
        "    <p data-piece>{}</p>".format(esc(p)) for p in about.get("paragraphs", [])
    )

    facts_html = "\n".join(
        "      <li data-piece><b>{}</b> {}</li>".format(esc(f.get("key", "")), esc(f.get("value", "")))
        for f in about.get("facts", [])
    )

    cards_html = "\n".join(
        """      <article class="card" data-piece>
        <div class="tag">{tag}</div>
        <h3>{title}</h3>
        <p>{desc}</p>
      </article>""".format(
            tag=esc(c.get("tag", "")), title=esc(c.get("title", "")), desc=esc(c.get("desc", ""))
        )
        for c in work.get("cards", [])
    )

    link_rows = []
    for item in links.get("items", []):
        if item.get("copy"):
            link_rows.append(
                '      <li data-piece><button type="button" class="link-copy" data-copy="{}">{} '
                '<span class="hint">复制</span></button></li>'.format(
                    esc(item["copy"]), esc(item.get("label", ""))
                )
            )
            continue
        target = ' target="_blank" rel="noreferrer"' if item.get("external") else ""
        link_rows.append(
            '      <li data-piece><a href="{}"{}>{} <span>→</span></a></li>'.format(
                esc(item.get("href", "#")), target, esc(item.get("label", ""))
            )
        )
    links_html = "\n".join(link_rows)

    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{title}</title>
<link rel="stylesheet" href="style.css" />
</head>
<body>
<!-- 本文件由 build.py 从 content.json 生成；改文字请用 编辑.bat -->
<!-- 动态鼠标画布：所有光标、拖拽选框都画在这里 -->
<canvas id="fx" aria-hidden="true"></canvas>

<header class="nav">
  <div class="nav-inner">
    <div class="brand">{brand}<span class="dot">{dot}</span></div>
    <nav>
{nav}
    </nav>
  </div>
</header>

<main>
  <section class="hero" id="top">
    <p class="eyebrow" data-piece>{eyebrow}</p>
    <h1 data-piece>{t1}<br /><span class="grad">{t2}</span></h1>
    <p class="lede" data-piece>
      {lede}
    </p>
    <div class="actions" data-piece>
{buttons}
    </div>
  </section>

  <section id="about">
    <h2 data-piece>{about_title}</h2>
{paragraphs}
    <ul class="facts">
{facts}
    </ul>
  </section>

  <section id="work">
    <h2 data-piece>{work_title}</h2>
    <div class="cards">
{cards}
    </div>
  </section>

  <section id="links">
    <h2 data-piece>{links_title}</h2>
    <ul class="links">
{links}
    </ul>
  </section>
</main>

<footer>
  <p>{footer}</p>
</footer>

<!-- 右下角：时钟 + 自动漫游开关 -->
<div class="hud" id="hud">
  <span class="hud-time" id="hudTime">--:--:--</span>
  <button type="button" class="hud-btn" id="hudBtn" aria-pressed="true"
          title="关掉后光标会飞到三个角上待着；再点一次继续">
    <span class="led"></span><span class="hud-label">自动漫游</span>
  </button>
</div>

<script>
// 点一下就复制（Email 之类不想跳走的链接）
document.addEventListener('click', function (e) {{
  const btn = e.target.closest('.link-copy');
  if (!btn) return;
  const text = btn.dataset.copy || '';
  const hint = btn.querySelector('.hint');
  const done = () => {{
    const old = hint.textContent;
    btn.classList.add('copied');
    hint.textContent = '已复制';
    setTimeout(() => {{ btn.classList.remove('copied'); hint.textContent = old; }}, 1600);
  }};
  if (navigator.clipboard && navigator.clipboard.writeText) {{
    navigator.clipboard.writeText(text).then(done, () => legacyCopy(text, done));
  }} else {{
    legacyCopy(text, done);
  }}
}});

function legacyCopy(text, done) {{
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.cssText = 'position:fixed;left:-9999px;top:0';
  document.body.appendChild(ta);
  ta.select();
  try {{ document.execCommand('copy'); done(); }} catch (err) {{ alert('复制失败，手动选一下：' + text); }}
  ta.remove();
}}
</script>
<!-- 侧边抽屉：Pleiades 监视塔（照原作设定图重画的细线版） -->
<div class="tower" id="tower" aria-hidden="true">
<svg viewBox="0 0 76 476" preserveAspectRatio="none">
    <defs>
      <radialGradient id="gateGlow" cx="50%" cy="100%" r="90%">
        <stop offset="0%" stop-color="#f2cb7c" stop-opacity=".70"/>
        <stop offset="55%" stop-color="#f2cb7c" stop-opacity=".18"/>
        <stop offset="100%" stop-color="#f2cb7c" stop-opacity="0"/>
      </radialGradient>
      <clipPath id="shaftClip"><rect x="0" y="120" width="76" height="330"/></clipPath>
    </defs>
      <g class="tw-minis"><g class="tw-mini" style="animation-delay:-1.5s">
          <path class="tw-mini-dome" d="M33.8 116 L33.8 110 A4.2 4.2 0 0 1 42.2 110 L42.2 116"/>
          <path d="M33.8 116 L36.236 196 L39.764 196 L42.2 116 Z"/>
          <path class="tw-mini-hair" d="M34.64 142 L41.36 142"/>
          <path class="tw-mini-hair" d="M35.396 172 L40.604 172"/>
          <path class="tw-mini-hair" d="M35.9 200 L40.1 200"/>
        </g></g>
        <path class="tw-body" d="M32 132 L32 300 L14 430 L8 436 L8 448 L68 448 L68 436 L62 430 L44 300 L44 132 Z"/>
        <path class="tw-dome" d="M33 132 L33 118 A5 5 0 0 1 43 118 L43 132"/>
        <path class="tw-dome" d="M26 132 L26 123 A3.5 3.5 0 0 1 33 123 L33 132"/>
        <path class="tw-dome" d="M43 132 L43 123 A3.5 3.5 0 0 1 50 123 L50 132"/>
        <path class="tw-dome" d="M21 132 L21 126.5 A2.5 2.5 0 0 1 26 126.5 L26 132"/>
        <path class="tw-dome" d="M50 132 L50 126.5 A2.5 2.5 0 0 1 55 126.5 L55 132"/>
        <g class="tw-minis"><g class="tw-mini" style="animation-delay:.0s">
          <path class="tw-mini-dome" d="M18.8 130 L18.8 124 A5.2 5.2 0 0 1 29.2 124 L29.2 130"/>
          <path d="M18.8 130 L24.6 272.0 L23.4 272.0 L29.2 130 Z"/>
          <path class="tw-mini-hair" d="M19.84 156 L28.16 156"/>
          <path class="tw-mini-hair" d="M20.776 186 L27.224 186"/>
          <path class="tw-mini-hair" d="M21.4 214 L26.6 214"/>
        </g><g class="tw-mini" style="animation-delay:-3.2s">
          <path class="tw-mini-dome" d="M46.8 130 L46.8 124 A5.2 5.2 0 0 1 57.2 124 L57.2 130"/>
          <path d="M46.8 130 L52.6 272.0 L51.4 272.0 L57.2 130 Z"/>
          <path class="tw-mini-hair" d="M47.84 156 L56.16 156"/>
          <path class="tw-mini-hair" d="M48.775999999999996 186 L55.224000000000004 186"/>
          <path class="tw-mini-hair" d="M49.4 214 L54.6 214"/>
        </g></g>
        <path class="tw-spire-line" d="M38 4 L36 96 L40 96 Z"/>
        <circle class="tw-tip" cx="38" cy="3" r="2"/>
        <path class="tw-wing" d="M10 446 C 3 320, 10 168, 31 60"/>
        <path class="tw-wing" d="M66 446 C 73 320, 66 168, 45 60"/>
        <path class="tw-hair" d="M26.3 341 L49.7 341"/>
        <path class="tw-hair" d="M22.2 371 L53.8 371"/>
        <path class="tw-hair" d="M18.0 401 L58.0 401"/>
        <path class="tw-body" d="M25 300 L51 300"/>
        <path class="tw-hair" d="M27 294 L27 300"/>
        <path class="tw-hair" d="M31 294 L31 300"/>
        <path class="tw-hair" d="M35 294 L35 300"/>
        <path class="tw-hair" d="M39 294 L39 300"/>
        <path class="tw-hair" d="M43 294 L43 300"/>
        <path class="tw-hair" d="M47 294 L47 300"/>
        <path class="tw-body" d="M26 432 L38 424 L50 432"/>
        <path class="tw-hair" d="M29 432 L29 449"/>
        <path class="tw-hair" d="M33 432 L33 449"/>
        <path class="tw-hair" d="M43 432 L43 449"/>
        <path class="tw-hair" d="M47 432 L47 449"/>
        <path class="tw-hair" d="M8 449 L68 449"/>
        <path class="tw-hair" d="M8 452.5 L68 452.5"/>
        <path class="tw-hair" d="M8 456 L68 456"/>
        <path class="tw-dash" d="M10 464 L34 464 M42 464 L66 464"/>
        <path class="tw-dash" d="M14 470 L30 470 M46 470 L62 470"/>
    <g class="gate" clip-path="url(#shaftClip)">
      <path class="lite" d="M31 449 L31 434 A7 7 0 0 1 45 434 L45 449 Z"/>
      <path class="leaf" d="M31 449 L31 434 A7 7 0 0 1 45 434 L45 449 Z"/>
    </g>
  </svg>
</div>
<div class="tower-slit" aria-hidden="true"></div>

<script src="fx.js"></script>
</body>
</html>
""".format(
        title=esc(site.get("title", "个人主页")),
        brand=esc(site.get("brand", "")),
        dot=esc(site.get("brand_dot", ".")),
        nav=nav_html,
        eyebrow=esc(hero.get("eyebrow", "")),
        t1=esc(hero.get("title_1", "")),
        t2=esc(hero.get("title_2", "")),
        lede=esc(hero.get("lede", "")),
        buttons=buttons_html,
        about_title=esc(about.get("title", "")),
        paragraphs=paragraphs_html,
        facts=facts_html,
        work_title=esc(work.get("title", "")),
        cards=cards_html,
        links_title=esc(links.get("title", "")),
        links=links_html,
        footer=esc(site.get("footer", "")),
    )


def build():
    data = json.loads(CONTENT.read_text(encoding="utf-8"))
    OUTPUT.write_text(render(data), encoding="utf-8", newline="\n")
    return OUTPUT


if __name__ == "__main__":
    path = build()
    pieces = path.read_text(encoding="utf-8").count("data-piece")
    print("已生成 {} （{} 个可动块）".format(path.name, pieces))
