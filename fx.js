/* 光标画布 v2
   - 所有坐标都是「文档坐标」（y 里含滚动量），绘制时减 scrollY → 选框跟着内容走
   - 每个光标自己认领一块 data-piece，各自拉框、各自合上，框一合上内容就蹦出来
*/
(() => {
  const canvas = document.getElementById('fx');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  const pieces = Array.from(document.querySelectorAll('[data-piece]'));
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduce) {
    pieces.forEach(el => el.classList.add('in'));
    return;
  }

  let W = 0, H = 0, DPR = 1, scrollY = window.scrollY || 0, lastScroll = 0;
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const rand = (a, b) => a + Math.random() * (b - a);

  function sbWidth() {
    const w = window.innerWidth - document.documentElement.clientWidth;
    document.documentElement.style.setProperty('--sbw', (w > 0 ? w : 0) + 'px');
  }

  function resize() {
    sbWidth();
    DPR = Math.min(2, window.devicePixelRatio || 1);
    W = window.innerWidth;
    H = window.innerHeight;
    canvas.width = Math.round(W * DPR);
    canvas.height = Math.round(H * DPR);
    canvas.style.width = W + 'px';
    canvas.style.height = H + 'px';
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
  }

  resize();
  window.addEventListener('resize', resize);

  /* ---------------- 光标 ---------------- */
  const PALETTE = [
    { name: '夏乌拉', color: '#ff8f3a' },      // 橙
    { name: 'Dandan008', color: '#00adef' },   // 奔驰蓝
    { name: '大肥鱼', color: '#4d6bfe' }        // DeepSeek 主题蓝
  ];

  const cursors = PALETTE.map((p, i) => ({
    name: p.name,
    color: p.color,
    x: rand(90, W - 90),
    y: scrollY + rand(130, 380),
    press: 0,
    dragging: false,
    dragFrom: null,
    queue: [],
    task: null,
    alpha: 1,
    fly: null,
    nextThink: performance.now() + i * 170
  }));

  /* ---------------- 右下角：时钟 + 抽屉开关 ---------------- */
  const hudTime = document.getElementById('hudTime');
  const hudBtn = document.getElementById('hudBtn');
  const tower = document.getElementById('tower');
  const gateEl = tower ? tower.querySelector('.gate .lite') : null;   // 量门洞本体，别量会滑走的门扇

  let auto = true;    // 光标是否在外面干活
  let away = false;   // 光标被收进塔里了
  let busy = false;   // 演出中，忽略连点

  // 默认就是自动漫游：页面要靠光标一块块搭出来，所以刷新后总是从「在外面」开始

  const pad2 = n => (n < 10 ? '0' + n : '' + n);
  function tickClock() {
    if (!hudTime) return;
    const d = new Date();
    hudTime.textContent = pad2(d.getHours()) + ':' + pad2(d.getMinutes()) + ':' + pad2(d.getSeconds());
  }
  tickClock();
  setInterval(tickClock, 1000);

  function syncHud() { if (hudBtn) hudBtn.setAttribute('aria-pressed', auto ? 'true' : 'false'); }
  function persist() { try { localStorage.setItem('fx-auto', auto ? 'on' : 'off'); } catch (e) {} }

  function stopMoves() {
    for (const c of cursors) {
      c.queue.length = 0;
      c.task = null;
      c.dragging = false;
      c.dragFrom = null;
      c.press = 0;
    }
  }

  // 门口坐标（塔是 fixed，换算成文档坐标给光标用）
  function gatePoint() {
    if (!gateEl) return { x: W - 52, y: scrollY + H / 2 };
    const r = gateEl.getBoundingClientRect();
    // 门口地面：光标走到门槛高度再往里跨
    return { x: r.left + r.width / 2, y: scrollY + r.bottom - 9 };
  }

  // 光标被收进去：塔滑进来 → 开门 → 三只飞进门 → 关门 → 塔退场
  function stowAway() {
    if (busy || away || !tower) return;
    busy = true;
    auto = false; persist(); syncHud(); stopMoves();
    frames.length = 0; floaters.length = 0;
    tower.classList.add('in');
    setTimeout(() => tower.classList.add('open'), 190);
    setTimeout(() => {
      const g = gatePoint();
      const now = performance.now();
      cursors.forEach((c, i) => {
        const ax = g.x - 78 + (i - 1) * 14;   // 先在门外排好
        const mx = g.x - 8 + (i - 1) * 6;     // 门槛
        const my = g.y + (i - 1) * 5;
        startFly(c, [
          { x0: c.x, y0: c.y, x: ax, y: my, a0: 1, a: 1, fade: [0, 1], dur: 380, t0: now + i * 40 },
          { x0: ax, y0: my, x: mx, y: my, a0: 1, a: 1, fade: [0, 1], dur: 200, t0: 0 },
          { x0: mx, y0: my, x: mx + 5, y: my - 12, a0: 1, a: 0, fade: [0.35, 1], dur: 220, t0: 0 }
        ]);
      });
    }, 420);
    setTimeout(() => tower.classList.remove('open'), 1300);
    setTimeout(() => tower.classList.remove('in'), 1520);
    setTimeout(() => {
      away = true; busy = false;
      document.body.classList.add('away');
      for (const c of cursors) { c.fly = null; c.alpha = 0; }
    }, 1740);
  }

  // 放出来：塔回来 → 开门 → 三只从门里飞出去 → 关门 → 塔退场
  function letOut() {
    if (busy || !away || !tower) return;
    busy = true;
    tower.classList.add('in');
    setTimeout(() => tower.classList.add('open'), 190);
    setTimeout(() => {
      const g = gatePoint();
      const now = performance.now();
      cursors.forEach((c, i) => {
        const sx = g.x - 6 + (i - 1) * 6;
        const sy = g.y - 16 + (i - 1) * 5;
        const ox = g.x - 78 + (i - 1) * 14;
        c.x = sx; c.y = sy; c.alpha = 0; c.press = 0;
        startFly(c, [
          // ① 门里亮起来
          { x0: sx, y0: sy, x: sx, y: sy, a0: 0, a: 1, fade: [0, 1], dur: 150, t0: now + i * 50 },
          // ② 走出门槛
          { x0: sx, y0: sy, x: ox, y: g.y + (i - 1) * 5, a0: 1, a: 1, fade: [0, 1], dur: 260, t0: 0 },
          // ③ 飞回页面
          { x0: ox, y0: g.y + (i - 1) * 5, x: rand(140, W - 200), y: scrollY + rand(150, Math.max(220, H * 0.6)),
            a0: 1, a: 1, fade: [0, 1], dur: 420, t0: 0 }
        ]);
      });
    }, 400);
    setTimeout(() => tower.classList.remove('open'), 1180);
    setTimeout(() => tower.classList.remove('in'), 1400);
    setTimeout(() => {
      auto = true; away = false; busy = false;
      document.body.classList.remove('away');
      persist(); syncHud();
      for (const c of cursors) c.nextThink = 0;
    }, 1620);
  }

  function startFly(c, segs) {
    c.fly = segs.shift();
    c.flyRest = segs;
  }

  // 分段飞行：每段可以只在 [p0,p1] 区间里改透明度，所以「进门」时可以先看得清、到门口才消失
  function advanceFly(c, now) {
    const f = c.fly;
    if (!f) return;
    const raw = (now - f.t0) / f.dur;
    if (raw < 0) return;
    const p = raw >= 1 ? 1 : raw;
    const e = 1 - Math.pow(1 - p, 3);
    c.x = f.x0 + (f.x - f.x0) * e;
    c.y = f.y0 + (f.y - f.y0) * e;
    const w = f.fade || [0, 1];
    const q = p <= w[0] ? 0 : p >= w[1] ? 1 : (p - w[0]) / (w[1] - w[0]);
    c.alpha = f.a0 + (f.a - f.a0) * q;
    if (p >= 1) {
      c.fly = null;
      if (c.flyRest && c.flyRest.length) {
        const nxt = c.flyRest.shift();
        nxt.x0 = c.x; nxt.y0 = c.y; nxt.a0 = c.alpha;
        nxt.t0 = now;
        c.fly = nxt;
      }
    }
  }

  if (hudBtn) {
    hudBtn.addEventListener('click', () => {
      if (busy) return;
      if (auto) stowAway(); else letOut();
    });
  }
  syncHud();


  const frames = [];    // 已合上的框（文档坐标）
  const floaters = [];  // 框合上后飘出来的 token 提示

  /* ---------------- 待建元素 ---------------- */
  const jobs = pieces.map(el => ({ el, done: false, claimed: false }));

  const rectOf = el => {
    const r = el.getBoundingClientRect();
    return { x0: r.left, y0: r.top + scrollY, x1: r.right, y1: r.bottom + scrollY };
  };

  // 文字类元素按「文字实际占的框」走，别框一整个通栏
  const TEXTY = /^(H1|H2|H3|P|LI|A)$/;
  const boxOf = el => {
    if (TEXTY.test(el.tagName)) {
      const range = document.createRange();
      range.selectNodeContents(el);
      const r = range.getBoundingClientRect();
      if (r.width > 6 && r.height > 6) {
        return { x0: r.left, y0: r.top + scrollY, x1: r.right, y1: r.bottom + scrollY };
      }
    }
    return rectOf(el);
  };

  const reveal = job => {
    if (job.done) return;
    job.done = true;
    job.claimed = false;
    job.el.classList.add('in');
  };

  // 从上往下按顺序领活：页面像被一点点「建」出来，而不是东一块西一块
  function pickJob(c) {
    let best = null;
    for (const job of jobs) {
      if (job.done || job.claimed) continue;
      const r = boxOf(job.el);
      const top = r.y0 - scrollY;
      const bottom = r.y1 - scrollY;
      if (bottom < -120) { reveal(job); continue; }   // 已经划过去了：直接给，别让它空着
      if (top > H * 1.6) continue;                     // 还太远：提前一屏多就开始建，滚过去刚好
      if (!best || r.y0 < best.r.y0) best = { job, r };
    }
    return best;
  }

  function assign(c, hit) {
    const { job, r } = hit;
    job.claimed = true;

    const pad = /^(ARTICLE|DIV|UL|SECTION)$/.test(job.el.tagName) ? 10 : 8;
    const x0 = r.x0 - pad, y0 = r.y0 - pad;
    const x1 = r.x1 + pad, y1 = r.y1 + pad;

    // 每个光标随机挑一对对角，避免动作整齐划一
    const flipX = Math.random() < 0.5;
    const flipY = Math.random() < 0.5;
    const sx = flipX ? x1 : x0;
    const sy = flipY ? y1 : y0;
    const ex = flipX ? x0 : x1;
    const ey = flipY ? y0 : y1;

    const travelDist = Math.hypot(sx - c.x, sy - c.y);
    const dragDist = Math.hypot(ex - sx, ey - sy);

    c.queue.push(
      { t: 'move', x: sx, y: sy, dur: clamp(travelDist * 1.15, 170, 520) },
      { t: 'press', dur: 90 },
      { t: 'drag', x: ex, y: ey, dur: clamp(dragDist * 0.85, 240, 520) },
      {
        t: 'release', dur: 90, linger: 620,
        on: () => reveal(job)
      }
    );
  }

  function tokenLabel() {
    const r = Math.random();
    if (r < 0.42) return 'token-' + rand(0.4, 3.9).toFixed(1) + 'k';
    if (r < 0.78) return 'token-' + Math.round(rand(120, 980));
    return 'token-' + Math.round(rand(2, 24)) + 'k';
  }

  function spawnToken(x0, y0, x1, y1, color, now) {
    floaters.push({
      text: tokenLabel(),
      x: (x0 + x1) / 2,
      y: y0 - 6,
      color,
      born: now,
      life: rand(1100, 1500)
    });
  }

  function wander(c, now) {
    c.queue.push({
      t: 'move',
      x: rand(70, W - 70),
      y: scrollY + rand(110, H - 110),
      dur: rand(900, 1700),
      idle: true
    });
    c.nextThink = now + rand(700, 1600);
  }

  const ease = t => 1 - Math.pow(1 - t, 3);

  function step(c, now) {
    if (!c.task && !c.queue.length) {
      if (now < c.nextThink) return;
      const hit = pickJob(c);
      if (hit) assign(c, hit);
      else wander(c, now);
    }
    if (c.task) return;

    const task = c.queue.shift();
    task.start = now;
    task.from = { x: c.x, y: c.y };
    if (task.t === 'press') c.press = 1;
    if (task.t === 'release') c.press = 0;
    c.task = task;
  }

  function advance(c, now) {
    const t = c.task;
    if (!t) return;
    const p = t.dur ? clamp((now - t.start) / t.dur, 0, 1) : 1;
    const e = ease(p);

    if (t.t === 'move' || t.t === 'drag') {
      c.x = t.from.x + (t.x - t.from.x) * e;
      c.y = t.from.y + (t.y - t.from.y) * e;
    } else if (t.t === 'press') {
      if (p >= 1) {
        c.press = 1;
        c.dragging = true;
        c.dragFrom = { x: c.x, y: c.y };
      }
    } else if (t.t === 'release') {
      if (p >= 1) {
        if (c.dragFrom) {
          const w = Math.abs(c.x - c.dragFrom.x);
          const h = Math.abs(c.y - c.dragFrom.y);
          if (w > 6 || h > 6) {
            const bx0 = Math.min(c.dragFrom.x, c.x);
            const by0 = Math.min(c.dragFrom.y, c.y);
            const bx1 = Math.max(c.dragFrom.x, c.x);
            const by1 = Math.max(c.dragFrom.y, c.y);
            frames.push({
              x0: bx0, y0: by0, x1: bx1, y1: by1,
              color: c.color,
              born: now,
              life: t.linger || 900
            });
            spawnToken(bx0, by0, bx1, by1, c.color, now);
          }
          if (t.on) t.on();
        }
        c.dragFrom = null;
        c.dragging = false;
      }
    }

    if (p >= 1) {
      if (t.idle) c.nextThink = now + rand(600, 1400);
      c.task = null;
    }
  }

  /* ---------------- 绘制 ---------------- */
  function drawArrow(x, y, color, pressed) {
    ctx.save();
    ctx.translate(x, y);
    const s = pressed ? 0.9 : 1;
    ctx.scale(s, s);
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(0, 17);
    ctx.lineTo(4.7, 13.1);
    ctx.lineTo(7.7, 19.7);
    ctx.lineTo(10.5, 18.3);
    ctx.lineTo(7.6, 11.9);
    ctx.lineTo(13.2, 11.5);
    ctx.closePath();
    ctx.fillStyle = color;
    ctx.shadowColor = color;
    ctx.shadowBlur = 14;
    ctx.fill();
    ctx.shadowBlur = 0;
    ctx.lineWidth = 1.1;
    ctx.strokeStyle = 'rgba(6,10,16,.85)';
    ctx.stroke();
    ctx.restore();
  }

  function drawLabel(x, y, text, color) {
    ctx.font = '600 10.5px ui-monospace, Consolas, "Microsoft YaHei", monospace';
    const w = ctx.measureText(text).width + 14;
    // 贴到右边缘时把标签翻到左边，别被裁掉
    const bx = x > W - 170 ? x - 15 - w : x + 15;
    const by = y + 15, bh = 18;
    ctx.save();
    ctx.beginPath();
    ctx.rect(bx + 0.5, by + 0.5, w, bh);
    ctx.fillStyle = 'rgba(6,10,16,.90)';
    ctx.fill();
    ctx.lineWidth = 1;
    ctx.strokeStyle = color;
    ctx.globalAlpha = 0.85;
    ctx.stroke();
    ctx.globalAlpha = 1;
    ctx.fillStyle = color;
    ctx.textBaseline = 'middle';
    ctx.fillText(text, bx + 7, by + bh / 2 + 0.5);
    ctx.restore();
  }

  function drawFrame(f, now, sy) {
    const age = (now - f.born) / f.life;
    if (age >= 1) return false;
    const a = 1 - age * age;
    const y0 = f.y0 - sy, y1 = f.y1 - sy;
    if (y1 < 0 || y0 > H) return false;

    ctx.save();
    ctx.globalAlpha = a;
    ctx.strokeStyle = f.color;
    ctx.lineWidth = 1.6;
    ctx.setLineDash([7, 6]);
    ctx.strokeRect(f.x0, y0, f.x1 - f.x0, y1 - y0);
    ctx.setLineDash([]);
    // 四角小方块，像选中态
    const corners = [[f.x0, y0], [f.x1, y0], [f.x0, y1], [f.x1, y1]];
    ctx.fillStyle = f.color;
    for (const [cx, cy] of corners) ctx.fillRect(cx - 2.5, cy - 2.5, 5, 5);
    ctx.restore();
    return true;
  }

  function drawFloater(f, now, sy) {
    const p = (now - f.born) / f.life;
    if (p >= 1) return;
    const rise = 28 * p;
    const alpha = p < 0.22 ? p / 0.22 : 1 - (p - 0.22) / 0.78;
    const ty = f.y - sy - rise;
    if (ty < -40 || ty > H + 40) return;

    ctx.save();
    ctx.font = '600 11px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace';
    const w = ctx.measureText(f.text).width + 14;
    const bx = f.x - w / 2;
    const by = ty - 10;
    ctx.globalAlpha = Math.max(0, alpha) * 0.85;
    ctx.beginPath();
    if (ctx.roundRect) ctx.roundRect(bx, by, w, 19, 5);
    else ctx.rect(bx, by, w, 19);
    ctx.fillStyle = 'rgba(8,12,18,.94)';
    ctx.fill();
    ctx.strokeStyle = f.color;
    ctx.lineWidth = 1;
    ctx.globalAlpha = Math.max(0, alpha);
    ctx.stroke();
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = f.color;
    ctx.fillText(f.text, f.x, ty + 0.5);
    ctx.restore();
  }

  function drawActive(c, sy) {
    if (!c.dragging || !c.dragFrom) return;
    const x0 = Math.min(c.dragFrom.x, c.x);
    const y0 = Math.min(c.dragFrom.y, c.y);
    const x1 = Math.max(c.dragFrom.x, c.x);
    const y1 = Math.max(c.dragFrom.y, c.y);
    const sy0 = y0 - sy, sy1 = y1 - sy;

    ctx.save();
    ctx.fillStyle = c.color;
    ctx.globalAlpha = 0.08;
    ctx.fillRect(x0, sy0, x1 - x0, sy1 - sy0);
    ctx.globalAlpha = 1;
    ctx.strokeStyle = c.color;
    ctx.lineWidth = 1.5;
    ctx.strokeRect(x0, sy0, x1 - x0, sy1 - sy0);
    ctx.fillStyle = c.color;
    for (const [cx, cy] of [[x0, sy0], [x1, sy0], [x0, sy1], [x1, sy1]]) {
      ctx.fillRect(cx - 2.5, cy - 2.5, 5, 5);
    }
    ctx.restore();
  }

  /* ---------------- 主循环 ---------------- */
  function loop(now) {
    scrollY = window.scrollY || 0;

    // 已经划过屏幕的块直接给，快速拖到底不会留空白
    for (const job of jobs) {
      if (job.done) continue;
      if (boxOf(job.el).y1 - scrollY < -80) reveal(job);
    }

    // 大幅滚动（拖滚动条 / 按 End）：把闲逛中的光标叫回来，重新盯眼前的内容
    if (Math.abs(scrollY - lastScroll) > 140) {
      for (const c of cursors) {
        c.queue = c.queue.filter(t => !t.idle);
        if (c.task && c.task.idle) c.task = null;
        if (!c.dragging) c.nextThink = 0;
      }
    }
    lastScroll = scrollY;

    for (let i = frames.length - 1; i >= 0; i--) {
      if (now - frames[i].born > frames[i].life) frames.splice(i, 1);
    }
    for (let i = floaters.length - 1; i >= 0; i--) {
      if (now - floaters[i].born > floaters[i].life) floaters.splice(i, 1);
    }

    ctx.clearRect(0, 0, W, H);

    for (const f of frames) drawFrame(f, now, scrollY);
    for (const c of cursors) drawActive(c, scrollY);
    for (const f of floaters) drawFloater(f, now, scrollY);

    // 光标被收进塔里：这一屏还没建好的块直接给，别让页面空着
    if (!auto) {
      for (const job of jobs) {
        if (!job.done && boxOf(job.el).y0 - scrollY < H - 30) reveal(job);
      }
    }

    for (const c of cursors) {
      if (c.fly) advanceFly(c, now);
      else if (auto) { step(c, now); advance(c, now); }
    }

    for (const c of cursors) {
      if (c.alpha < 0.02) continue;
      const sy = c.y - scrollY;
      if (sy < -80 || sy > H + 80) continue;
      ctx.globalAlpha = c.alpha;
      drawArrow(c.x, sy, c.color, c.press);
      if (auto) drawLabel(c.x, sy, c.name, c.color);   // 收放过程中不挂名牌，别挡视野
      ctx.globalAlpha = 1;
    }

    requestAnimationFrame(loop);
  }

  // 首帧：把已经在视口里的先分给光标
  requestAnimationFrame(loop);

  // 兜底：万一脚本中途卡住，视口里的块 12 秒后直接显示，绝不把内容锁死
  setTimeout(() => {
    for (const job of jobs) {
      if (job.done) continue;
      const r = boxOf(job.el);
      if (r.y0 - window.scrollY < H) reveal(job);
    }
  }, 12000);
})();
