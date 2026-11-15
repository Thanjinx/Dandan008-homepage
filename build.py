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
<!-- 侧边抽屉：Pleiades 监视塔（细线蓝图版）。开 / 关自动漫游时用它把光标收进去 / 放出来 -->
<div class="tower" id="tower" aria-hidden="true">
  <svg viewBox="0 0 76 470" preserveAspectRatio="none">
    <defs>
      <radialGradient id="gateGlow" cx="50%" cy="100%" r="85%">
        <stop offset="0%" stop-color="#f2cb7c" stop-opacity=".62"/>
        <stop offset="60%" stop-color="#f2cb7c" stop-opacity=".16"/>
        <stop offset="100%" stop-color="#f2cb7c" stop-opacity="0"/>
      </radialGradient>
      <clipPath id="shaftClip"><rect x="0.5" y="88.5" width="75" height="347"/></clipPath>
    </defs>
    <path class="tw-spire" d="M0 88 L6.8 88 L6.8 62 L20.5 62 L20.5 32 L34.2 32 L34.2 10 L36.2 10 L36.2 2 L38 0 L39.8 2 L39.8 10 L41.8 10 L41.8 32 L55.5 32 L55.5 62 L69.2 62 L69.2 88 Z"/>
    <circle class="tw-tip" cx="38" cy="2" r="2.2"/>
    <rect class="tw-shaft" x="0.5" y="88.5" width="75" height="347"/>
    <g class="tw-rings">
      <path d="M1 114 H75"/>
      <path d="M1 140 H75"/>
      <path d="M1 166 H75"/>
      <path d="M1 192 H75"/>
      <path d="M1 218 H75"/>
      <path d="M1 244 H75"/>
      <path d="M1 270 H75"/>
      <path d="M1 296 H75"/>
      <path d="M1 322 H75"/>
      <path d="M1 348 H75"/>
      <path d="M1 374 H75"/>
      <path d="M1 400 H75"/>
    </g>
    <g class="tw-stars">
      <circle cx="30" cy="116" r="1.3"/>
      <circle cx="42" cy="110" r="1.3"/>
      <circle cx="50" cy="124" r="1.3"/>
      <circle cx="38" cy="132" r="1.3"/>
      <circle cx="26" cy="128" r="1.3"/>
      <circle cx="45" cy="138" r="1.3"/>
      <circle cx="33" cy="142" r="1.3"/>
    </g>
    <g class="gate" clip-path="url(#shaftClip)">
      <path class="lite" d="M16 436 V414 A22 22 0 0 1 60 414 V436 Z"/>
      <path class="leaf" d="M16 436 V414 A22 22 0 0 1 60 414 V436 Z"/>
    </g>
    <g class="tw-base">
      <path d="M0 436 H76"/>
      <path d="M0 456 H76"/>
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
