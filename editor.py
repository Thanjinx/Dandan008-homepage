#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地可视化编辑页：改文字 → 保存 → 自动重建 index.html。

浏览器里只出现文字框，动效和排版都在 build.py / style.css / fx.js 里，
不需要在编辑页里碰。

启动：
    python editor.py            # 打开 http://127.0.0.1:8772
或者双击 编辑.bat
"""

import json
import mimetypes
import subprocess
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import build as builder

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content.json"
PORT_BASE = 8772

PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>编辑 · Dandan008 个人主页</title>
<style>
  :root {
    --bg:#0a0c10; --panel:#12161d; --line:rgba(255,255,255,.09);
    --txt:#e8eef7; --dim:#8b98ab; --accent:#5b9dff;
  }
  * { box-sizing: border-box; }
  body {
    margin:0; height:100vh; display:flex; flex-direction:column;
    background:var(--bg); color:var(--txt);
    font:14px/1.6 ui-sans-serif, system-ui, "Microsoft YaHei", sans-serif;
  }
  header {
    display:flex; align-items:center; gap:14px;
    padding:12px 20px; border-bottom:1px solid var(--line); background:var(--panel);
  }
  header h1 { font-size:15px; margin:0; font-weight:600; }
  header .hint { color:var(--dim); font-size:12px; }
  header .spacer { flex:1; }
  button {
    font:inherit; color:var(--txt); background:#1b2230; border:1px solid var(--line);
    border-radius:8px; padding:7px 14px; cursor:pointer;
  }
  button:hover { border-color:var(--accent); }
  button.primary { background:var(--accent); border-color:var(--accent); color:#08101c; font-weight:600; }
  button.ghost { background:transparent; }
  button.publish { border-color:var(--accent); color:var(--accent); background:transparent; font-weight:600; }
  button.publish:disabled, button.primary:disabled { opacity:.5; cursor:default; }
  #logbox { position:fixed; left:16px; bottom:16px; max-width:52vw; max-height:32vh; overflow:auto;
            background:#0b1018; border:1px solid var(--line); border-radius:10px; padding:8px 12px;
            font-size:12px; display:none; z-index:60; box-shadow:0 10px 30px rgba(0,0,0,.5); }
  #logbox b { color:#cfe0f5; font-weight:600; }
  #logbox pre { margin:8px 0 0; white-space:pre-wrap; word-break:break-all; color:#8fa3ba; line-height:1.5; }
  main { flex:1; display:flex; min-height:0; }
  #form { width:52%; overflow:auto; padding:18px 20px 60px; }
  #preview-wrap { width:48%; border-left:1px solid var(--line); background:#05070a; }
  #preview { width:100%; height:100%; border:0; }
  section {
    border:1px solid var(--line); border-radius:12px; padding:14px 16px;
    margin-bottom:14px; background:var(--panel);
  }
  section > h2 { font-size:13px; margin:0 0 12px; color:var(--dim); font-weight:600; letter-spacing:.04em; }
  label { display:block; margin-bottom:10px; }
  label > span { display:block; font-size:12px; color:var(--dim); margin-bottom:4px; }
  input, textarea {
    width:100%; font:inherit; color:var(--txt); background:#0c1117;
    border:1px solid var(--line); border-radius:7px; padding:8px 10px;
  }
  input:focus, textarea:focus { outline:none; border-color:var(--accent); }
  textarea { min-height:70px; resize:vertical; }
  .item {
    border:1px dashed var(--line); border-radius:10px; padding:10px 12px 4px;
    margin-bottom:10px; position:relative;
  }
  .item .del {
    position:absolute; top:8px; right:8px; padding:2px 8px; font-size:12px;
    border-color:transparent; color:var(--dim);
  }
  .item .del:hover { color:#ff7b8a; }
  .add { margin-top:2px; font-size:13px; }
  #status { font-size:12px; color:var(--dim); min-width:110px; }
  #status.ok { color:#7ef0c8; }
  #status.err { color:#ff7b8a; }
</style>
</head>
<body>
<header>
  <h1>编辑内容</h1>
  <span class="hint">只改文字，保存后自动重建页面</span>
  <span class="spacer"></span>
  <button class="primary" onclick="save()">保存</button>
  <button class="publish" onclick="publish()">发布</button>
  <button class="ghost" onclick="document.getElementById('preview').contentWindow.location.reload()">刷新预览</button>
  <span id="status"></span>
</header>
<main>
  <div id="form"></div>
  <div id="preview-wrap"><iframe id="preview" src="/files/index.html"></iframe></div>
</main>

<script>
const SPEC = [
  { key:'site', title:'站点', fields:[
      ['title','网页标题（浏览器标签）'],
      ['brand','左上角名字'],
      ['footer','页脚文字']
  ]},
  { key:'hero', title:'首屏', fields:[
      ['eyebrow','标题上方的小字'],
      ['title_1','大标题第一行'],
      ['title_2','大标题第二行（渐变色）'],
      ['lede','介绍段落', 'textarea']
  ], list:{ key:'buttons', label:'按钮', add:'加一个按钮', fields:[
      ['label','按钮文字'], ['href','跳转地址'], ['style','样式（primary / ghost）']
  ]}},
  { key:'about', title:'关于我', fields:[
      ['title','小标题']
  ], list:{ key:'paragraphs', label:'段落', add:'加一段', text:true },
     facts:{ key:'facts', label:'信息条目', add:'加一条', fields:[
      ['key','名称'], ['value','内容']
  ]}},
  { key:'work', title:'作品', fields:[
      ['title','小标题']
  ], list:{ key:'cards', label:'卡片', add:'加一张卡片', fields:[
      ['tag','标签'], ['title','卡片标题'], ['desc','描述','textarea']
  ]}},
  { key:'links', title:'链接', fields:[
      ['title','小标题']
  ], list:{ key:'items', label:'链接', add:'加一条链接', fields:[
      ['label','文字'], ['href','地址'], ['copy','点击复制的内容（填了就不跳转）'], ['external','新标签打开（true / false）']
  ]}}
];

let data = null;

const form = document.getElementById('form');
const status = document.getElementById('status');

function setStatus(text, cls) {
  status.textContent = text || '';
  status.className = cls || '';
}

function field(label, value, onChange, multiline) {
  const wrap = document.createElement('label');
  const cap = document.createElement('span');
  cap.textContent = label;
  wrap.appendChild(cap);
  const input = document.createElement(multiline ? 'textarea' : 'input');
  input.value = value == null ? '' : value;
  if (!multiline) input.type = 'text';
  input.addEventListener('input', () => onChange(input.value));
  wrap.appendChild(input);
  return wrap;
}

function render() {
  form.innerHTML = '';
  for (const sec of SPEC) {
    const box = document.createElement('section');
    const h = document.createElement('h2');
    h.textContent = sec.title;
    box.appendChild(h);

    const obj = data[sec.key] || (data[sec.key] = {});

    for (const [k, label, type] of (sec.fields || [])) {
      box.appendChild(field(label, obj[k], v => { obj[k] = v; }, type === 'textarea'));
    }

    if (sec.list) {
      const list = obj[sec.list.key] || (obj[sec.list.key] = []);
      list.forEach((item, idx) => {
        const wrap = document.createElement('div');
        wrap.className = 'item';
        const del = document.createElement('button');
        del.className = 'del';
        del.textContent = '删除';
        del.onclick = () => { list.splice(idx, 1); render(); };
        wrap.appendChild(del);
        if (sec.list.text) {
          wrap.appendChild(field('段落 ' + (idx + 1), item, v => { list[idx] = v; }, true));
        } else {
          for (const [k, label, type] of sec.list.fields) {
            wrap.appendChild(field(label, item[k], v => {
              item[k] = (k === 'external') ? (v === 'true') : v;
            }, type === 'textarea'));
          }
        }
        box.appendChild(wrap);
      });
      const add = document.createElement('button');
      add.className = 'add ghost';
      add.textContent = '+ ' + sec.list.add;
      add.onclick = () => {
        if (sec.list.text) list.push('');
        else {
          const fresh = {};
          for (const [k] of sec.list.fields) fresh[k] = '';
          list.push(fresh);
        }
        render();
      };
      box.appendChild(add);
    }

    if (sec.facts) {
      const list = obj[sec.facts.key] || (obj[sec.facts.key] = []);
      list.forEach((item, idx) => {
        const wrap = document.createElement('div');
        wrap.className = 'item';
        const del = document.createElement('button');
        del.className = 'del';
        del.textContent = '删除';
        del.onclick = () => { list.splice(idx, 1); render(); };
        wrap.appendChild(del);
        for (const [k, label] of sec.facts.fields) {
          wrap.appendChild(field(label, item[k], v => { item[k] = v; }));
        }
        box.appendChild(wrap);
      });
      const add = document.createElement('button');
      add.className = 'add ghost';
      add.textContent = '+ ' + sec.facts.add;
      add.onclick = () => { list.push({ key: '', value: '' }); render(); };
      box.appendChild(add);
    }

    form.appendChild(box);
  }
}

async function save() {
  setStatus('保存中…');
  try {
    const res = await fetch('/api/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    const out = await res.json();
    if (!out.ok) throw new Error(out.error || '保存失败');
    setStatus('已保存', 'ok');
    document.getElementById('preview').contentWindow.location.reload();
    setTimeout(() => setStatus(''), 4000);
  } catch (e) {
    setStatus('保存失败：' + e.message, 'err');
  }
}

function showLog(title, text) {
  document.getElementById('logtitle').textContent = title;
  document.getElementById('log').textContent = text || '';
  document.getElementById('logbox').style.display = 'block';
}

async function publish() {
  const msg = prompt('这次改了什么？（写一句更新说明，方便以后回滚）', '更新内容');
  if (msg === null) return;
  const message = msg.trim() || '更新内容';
  const btns = document.querySelectorAll('button');
  btns.forEach(b => b.disabled = true);
  setStatus('发布中…');
  try {
    const res = await fetch('/api/publish', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });
    const out = await res.json();
    if (!out.ok) {
      setStatus('发布失败', 'err');
      showLog('发布失败', out.log || out.error || '没有返回日志');
      return;
    }
    setStatus('已发布', 'ok');
    showLog('发布成功 · ' + message, out.log);
    setTimeout(() => setStatus(''), 6000);
  } catch (e) {
    setStatus('发布失败：' + e.message, 'err');
    showLog('发布失败', String(e));
  } finally {
    btns.forEach(b => b.disabled = false);
  }
}

(async () => {
  const res = await fetch('/api/content');
  data = await res.json();
  render();
})();
</script>
<div id="logbox"><b id="logtitle">发布日志</b><pre id="log"></pre></div>
</body>
</html>
"""


def decode_git(data):
    """git 输出优先按 UTF-8 解，解不开就当 GBK（中文 Windows 的 git 常是 GBK）。"""
    if not data:
        return ""
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("gbk", "replace")


def join_log(parts):
    return (chr(10) * 2).join(parts)


class Handler(BaseHTTPRequestHandler):
    server_version = "Dandan008Editor/1.0"

    def log_message(self, fmt, *args):  # 安静一点，别刷屏
        pass

    def _send(self, code, body, ctype="text/plain; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            return self._send(200, PAGE, "text/html; charset=utf-8")
        if self.path == "/api/content":
            return self._send(200, CONTENT.read_text(encoding="utf-8"), "application/json; charset=utf-8")
        if self.path.startswith("/files/"):
            rel = self.path[len("/files/"):].split("?")[0]
            target = (ROOT / rel).resolve()
            if ROOT not in target.parents and target != ROOT:
                return self._send(403, "forbidden")
            if target.is_file():
                ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
                if ctype.startswith("text/") or ctype in ("application/javascript",):
                    ctype += "; charset=utf-8"
                return self._send(200, target.read_bytes(), ctype)
            return self._send(404, "not found")
        self._send(404, "not found")

    def _git(self, *args, stdin_bytes=None):
        """跑一条 git 命令，返回 (成功, 输出)。

        不指定 text=True：Windows 上 git 的输出可能是 GBK，统一收字节再自己解码。
        """
        try:
            proc = subprocess.run(
                ["git", *args],
                cwd=str(ROOT),
                capture_output=True,
                input=stdin_bytes,
                timeout=180,
            )
        except Exception as exc:
            return False, "git %s 失败：%s" % (" ".join(args), exc)
        return proc.returncode == 0, decode_git(proc.stdout) + decode_git(proc.stderr)

    def _publish(self, message):
        """add → commit（有改动才提交）→ push。返回 (成功, 日志, 错误)。"""
        log = []
        ok, out = self._git("add", "-A")
        log.append("$ git add -A\n" + (out or "(无输出)"))
        if not ok:
            return False, join_log(log), "git add 失败"

        _, pending = self._git("status", "--porcelain")
        if pending:
            # 走 stdin 传提交信息：绕开 Windows 命令行参数的编码转换，保证是 UTF-8
            ok, out = self._git("commit", "-F", "-", stdin_bytes=message.encode("utf-8"))
            log.append("$ git commit -m " + message + "\n" + (out or "(无输出)"))
            if not ok:
                return False, join_log(log), "git commit 失败"
        else:
            log.append("没有新的改动，跳过 commit。")

        ok, out = self._git("push")
        log.append("$ git push\n" + (out or "(无输出)"))
        if not ok:
            low = out.lower()
            if "authentication" in low or "credential" in low or "permission" in low:
                return False, join_log(log), "推送被拒：需要重新登录 GitHub"
            return False, join_log(log), "git push 失败"
        return True, join_log(log), ""


    def _handle_publish(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8") if length else "{}"
            message = (json.loads(raw or "{}").get("message") or "更新内容").strip()[:120]
            ok, log, error = self._publish(message)
            self._send(
                200,
                json.dumps({"ok": ok, "log": log, "error": error}, ensure_ascii=False),
                "application/json; charset=utf-8",
            )
        except Exception as exc:
            self._send(
                500,
                json.dumps({"ok": False, "error": str(exc), "log": ""}, ensure_ascii=False),
                "application/json; charset=utf-8",
            )

    def do_POST(self):
        if self.path == "/api/publish":
            return self._handle_publish()
        if self.path != "/api/save":
            return self._send(404, "not found")
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8")
            data = json.loads(raw)
            CONTENT.write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            builder.build()
            self._send(200, json.dumps({"ok": True}), "application/json; charset=utf-8")
        except Exception as exc:  # 出错了要能看见，而不是白屏
            self._send(
                500,
                json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False),
                "application/json; charset=utf-8",
            )


def main():
    # 先保证 index.html 是最新的
    try:
        builder.build()
    except Exception as exc:
        print("警告：初始构建失败：", exc)

    for offset in range(10):
        port = PORT_BASE + offset
        try:
            httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            break
        except OSError:
            continue
    else:
        raise SystemExit("没有可用端口")

    url = "http://127.0.0.1:{}".format(port)
    print("编辑页：", url)
    threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已关闭")


if __name__ == "__main__":
    main()
