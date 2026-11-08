/* ===========================================================
   fox.js —— 岛民（小狐狸）行为
   会自己在草地上走、停、坐、睡；安静是默认状态
   一天最多主动来找你一次，其余时间只做自己的事

   ── 关于朝向的约定 ──────────────────────────────
   走路素材是侧视图，画的时候头朝【左】。
   所以在往右走（dir = +1）时必须镜像，往左走时不镜像。
   之前这里写反了，狐狸一直在"倒着走"。
   =========================================================== */
(function (global) {
  'use strict';

  var BASE = 'assets/animals/watercolor/sprites/fox-';
  var snd = global.App && global.App.sound;   // 没开声音时这里的调用全是空转

  // walk: 标记哪些姿势属于走路循环
  var POSES = {
    idle:    { src: BASE + 'idle-t.png' },
    blink:   { src: BASE + 'blink-t.png' },
    happy:   { src: BASE + 'happy-t.png' },
    sit:     { src: BASE + 'sit-t.png' },
    sleep:   { src: BASE + 'sleep-t.png' },
    'walk-a': { src: BASE + 'walk-a-t.png', walk: true },
    'walk-b': { src: BASE + 'walk-b-t.png', walk: true }
  };

  var WALK_FRAMES = ['walk-a', 'walk-b'];
  var STEP_MS = 165;              // 每帧时长：一秒约 3 组步态，接近真实小动物的节奏

  // 草地安全区（百分比，指脚底落点）= 画面下方那片空草地，就是留给狐狸走的
  // y0 压在 73 是有意的：物件最低的脚在 72（盆栽），再往上走狐狸就钻到房子后面去了
  // y1 收在 91：底下 9% 要留给落地阴影和那行小字
  var AREA = { x0: 16, x1: 84, y0: 73, y1: 91 };

  var el = {};
  var W = 0, H = 0;

  var S = {
    x: 50, y: 80,
    tx: 50, ty: 80,
    speed: 3.1,                 // 百分比 / 秒
    state: 'idle',              // idle | walk | sit | sleep
    pose: 'idle',
    dir: -1,                    // +1 向右，-1 向左
    sinceInteract: 0,
    blinkClock: 3,
    blinking: false,
    lastStep: -1,               // 上一帧是走路的哪一张，变了才出声
    layerA: true,               // 当前显示 A 还是 B
    token: 0,                   // 图层切换令牌，防止迟到的 onload 打乱顺序
    moodToken: 0,
    bubbleTimer: 0,
    pauseTimer: 1.2,
    stepClock: 0,
    dash: false,
    running: true
  };

  var last = 0;
  var raf = null;

  /* ---------- 图层切换 ---------- */
  function show(pose, opts) {
    opts = opts || {};
    if (S.pose === pose && !opts.force) return;
    var def = POSES[pose] || POSES.idle;
    var src = def.src;

    S.pose = pose;
    if (el.body) el.body.classList.toggle('stepping', !!def.walk);

    var incoming = S.layerA ? el.layerB : el.layerA;
    var outgoing = S.layerA ? el.layerA : el.layerB;
    var token = ++S.token;

    function commit() {
      // 已经有人换了更新的姿势，这次切换作废
      if (token !== S.token) return;
      if (el.body) el.body.classList.toggle('stepping', !!def.walk);
      incoming.classList.add('on');
      outgoing.classList.remove('on');
      S.layerA = !S.layerA;
    }

    // 同一张图已经在位（缓存命中）：直接提交，不再等 onload，
    // 否则会走到 onload 里二次提交，两个图层来回错位。
    if (incoming.getAttribute('src') === src && incoming.complete && incoming.naturalWidth) {
      incoming.onload = null;
      commit();
      return;
    }

    incoming.onload = function () {
      incoming.onload = null;
      commit();
    };
    incoming.setAttribute('src', src);
  }

  function setBody(cls, on) {
    if (!el.body) return;
    el.body.classList.toggle(cls, !!on);
  }

  /* ---------- 说话 ---------- */
  function say(text, ms) {
    if (!el.bubble) return;
    el.bubble.textContent = text;
    el.bubble.classList.add('on');
    S.bubbleTimer = (ms || 2200) / 1000;
  }

  function hush() {
    if (el.bubble) el.bubble.classList.remove('on');
    S.bubbleTimer = 0;
  }

  /* ---------- 回到"待着"的姿势 ---------- */
  function restPose() {
    if (S.state === 'sleep') { show('sleep', { force: true }); return; }
    if (S.state === 'sit') { show('sit', { force: true }); return; }
    if (S.state === 'walk') { show('walk-a', { force: true }); return; }
    show('idle', { force: true });
  }

  /* ---------- 反应 ---------- */
  function react(kind) {
    if (S.state === 'sleep') { S.state = 'idle'; S.pauseTimer = 1.6; }
    S.sinceInteract = 0;
    var my = ++S.moodToken;

    if (kind === 'happy') {
      show('happy', { force: true });
      setBody('breathing', false);
      setTimeout(function () {
        if (my !== S.moodToken) return;     // 期间又被摸了一次，让新的那次接管
        restPose();
        setBody('breathing', S.state === 'idle');
      }, 1000);
    }
    if (kind === 'wake') {
      show('blink', { force: true });
      say('唔…', 1200);
      setTimeout(function () {
        if (my !== S.moodToken) return;
        restPose();
      }, 800);
    }
  }

  function wake() {
    S.state = 'idle';
    S.pauseTimer = 1.6;
    S.sinceInteract = 0;
    react('wake');
  }

  /* ---------- 目标与移动 ---------- */
  function pickTarget() {
    var cx = (AREA.x0 + AREA.x1) / 2;
    var cy = (AREA.y0 + AREA.y1) / 2;
    // 一半概率在附近晃，一半概率横穿一段，这样不会是匀速巡逻
    var near = Math.random() < 0.58;
    var rx = near ? (AREA.x1 - AREA.x0) * 0.24 : (AREA.x1 - AREA.x0) * 0.46;
    var ry = near ? (AREA.y1 - AREA.y0) * 0.20 : (AREA.y1 - AREA.y0) * 0.40;
    S.tx = Math.max(AREA.x0, Math.min(AREA.x1, cx + (Math.random() * 2 - 1) * rx));
    S.ty = Math.max(AREA.y0, Math.min(AREA.y1, cy + (Math.random() * 2 - 1) * ry));
    S.dash = Math.random() < 0.16;
    S.state = 'walk';
    S.stepClock = 0;
    S.dir = S.tx < S.x ? -1 : 1;
  }

  /** 停下来的时长：多数很短，偶尔很长（真实的动物是一阵一阵的） */
  function pauseLength() {
    var r = Math.random();
    if (r < 0.45) return 0.8 + Math.random() * 1.2;     // 停一下就再走
    if (r < 0.82) return 2.4 + Math.random() * 2.6;     // 正常发呆
    return 6 + Math.random() * 6;                       // 长时间放空 / 坐下
  }

  function arrive() {
    S.state = 'idle';
    S.lastStep = -1;            // 下次起步从头数步，不会漏掉第一步
    setBody('bobbing', false);
    setBody('breathing', true);
    show('idle', { force: true });
    S.pauseTimer = pauseLength();
    // 有概率坐下
    if (Math.random() < 0.32) {
      var wait = 600 + Math.random() * 500;
      setTimeout(function () {
        if (S.state === 'idle' && S.pauseTimer > 1.5) {
          S.state = 'sit';
          setBody('breathing', false);
          show('sit', { force: true });
        }
      }, wait);
    }
  }

  /* ---------- 渲染 ---------- */
  function render() {
    if (!el.root) return;
    var px = (S.x / 100) * W;
    var py = (S.y / 100) * H;
    el.root.style.transform = 'translate3d(' + px.toFixed(2) + 'px,' + py.toFixed(2) + 'px,0) translate(-50%,-100%)';
    el.root.style.zIndex = String(Math.round(S.y));
    if (el.flip) {
      // 走路素材头朝左 → 向右走时镜像；正面姿势镜像只是换个朝向，无副作用
      var sx = S.dir > 0 ? -1 : 1;
      el.flip.style.transform = 'scaleX(' + sx + ')';
    }
  }

  function measure() {
    W = el.root ? el.root.parentNode.clientWidth : global.innerWidth;
    H = el.root ? el.root.parentNode.clientHeight : global.innerHeight;
    if (!W) W = global.innerWidth;
    if (!H) H = global.innerHeight;
  }

  /* ---------- 主循环 ---------- */
  function loop(now) {
    if (!S.running) { raf = null; return; }
    if (!last) last = now;
    var dt = Math.min(0.08, (now - last) / 1000);
    last = now;

    S.sinceInteract += dt;
    S.blinkClock -= dt;

    // 眨眼
    if (S.blinkClock <= 0 && (S.state === 'idle' || S.state === 'sit')) {
      S.blinkClock = 3 + Math.random() * 5;
      if (!S.blinking && S.pose !== 'happy') {
        S.blinking = true;
        var wasSit = S.state === 'sit';
        show('blink', { force: true });
        setTimeout(function () {
          S.blinking = false;
          if (S.state === 'sit' || wasSit) show('sit', { force: true });
          else if (S.state === 'idle') show('idle', { force: true });
        }, 130);
      }
    }

    // 气泡计时
    if (S.bubbleTimer > 0) {
      S.bubbleTimer -= dt;
      if (S.bubbleTimer <= 0) hush();
    }

    if (S.state === 'walk') {
      var dx = S.tx - S.x, dy = S.ty - S.y;
      var dist = Math.hypot(dx, dy);
      if (dist < 0.9) {
        arrive();
      } else {
        var v = (S.dash ? S.speed * 1.85 : S.speed) * dt;
        S.x += (dx / dist) * v;
        S.y += (dy / dist) * v;
        setBody('breathing', false);
        setBody('bobbing', true);
        S.stepClock += dt * 1000;
        var idx = ((S.stepClock / STEP_MS) | 0) % 2;
        if (idx !== S.lastStep) {
          S.lastStep = idx;
          if (snd) snd.step();          // 一步一声，很低很轻
        }
        show(WALK_FRAMES[idx]);
      }
    } else {
      S.pauseTimer -= dt;

      // 睡够了自己醒
      if (S.state === 'sleep') {
        if (S.pauseTimer <= 0) {
          S.state = 'idle';
          S.sinceInteract = 0;      // 关键：自己醒过来也要重置，否则睡醒又立刻睡回去
          S.pauseTimer = pauseLength();
          setBody('breathing', true);
          show('idle', { force: true });
        }
      } else {
        if (S.pauseTimer <= 0) pickTarget();
        // 呆着太久没人理 → 睡一会儿
        if (S.sinceInteract > 46) {
          S.state = 'sleep';
          S.sinceInteract = 0;
          S.pauseTimer = 26 + Math.random() * 40;
          setBody('breathing', false);
          setBody('bobbing', false);
          show('sleep', { force: true });
        }
      }
    }

    render();
    raf = requestAnimationFrame(loop);
  }

  /* ---------- 初始化 ---------- */
  function init(refs) {
    el = refs;
    if (!el.root) return;

    Object.keys(POSES).forEach(function (k) {
      var im = new Image();
      im.src = POSES[k].src;
    });

    measure();
    S.x = S.tx = 50;
    S.y = S.ty = 80;
    render();

    show('idle', { force: true });
    setBody('breathing', true);

    el.root.addEventListener('click', function () {
      react('happy');
      var lines = ['嘿', '嗯？', '舒服', '再摸一下', '我在呢'];
      setTimeout(function () {
        say(lines[(Math.random() * lines.length) | 0], 1800);
      }, 220);
      if (global.App && App.app && App.app.onPetFox) App.app.onPetFox();
    });

    // role="button" 就得能用键盘按
    el.root.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        el.root.click();
      }
    });

    el.root.addEventListener('mouseenter', function () {
      S.sinceInteract = 0;
      if (S.state === 'sleep') { wake(); return; }
      if (el.body) el.body.classList.add('near');
      // 转头看你
      if (S.state !== 'walk') S.dir = Math.random() < 0.5 ? 1 : -1;
    });
    el.root.addEventListener('mouseleave', function () {
      if (el.body) el.body.classList.remove('near');
    });

    global.addEventListener('resize', measure);
    global.addEventListener('orientationchange', measure);

    if (!raf) raf = requestAnimationFrame(loop);
  }

  function pause() {
    S.running = false;
    if (raf) cancelAnimationFrame(raf);
    raf = null;
    last = 0;
  }

  function resume() {
    if (S.running) return;
    S.running = true;
    last = 0;
    measure();
    raf = requestAnimationFrame(loop);
  }

  global.App = global.App || {};
  global.App.fox = {
    init: init,
    say: say,
    hush: hush,
    react: react,
    pause: pause,
    resume: resume,
    state: S
  };
})(window);
