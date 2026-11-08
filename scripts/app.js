/* ===========================================================
   app.js —— 路由、天气、问候、仪式
   =========================================================== */
(function (global) {
  'use strict';

  var store = global.App.store;
  var fox = global.App.fox;
  var views = global.App.views;
  var sound = global.App.sound;

  var el = {};
  var current = null;          // 当前打开的页面名
  var closing = false;
  var closeTimer = null;
  var toastTimer = null;

  /* ---------------- 工具 ---------------- */
  function $(s) { return document.querySelector(s); }

  function parseHash() {
    var h = (location.hash || '').replace(/^#\/?/, '');
    var parts = h.split('?');
    var name = parts[0] || '';
    var params = {};
    if (parts[1]) {
      parts[1].split('&').forEach(function (kv) {
        var p = kv.split('=');
        if (p[0]) params[decodeURIComponent(p[0])] = decodeURIComponent(p[1] || '');
      });
    }
    return { name: name, params: params };
  }

  function toast(msg) {
    el.toast.textContent = msg;
    el.toast.classList.add('on');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { el.toast.classList.remove('on'); }, 2000);
  }

  /* ---------------- 天气 ---------------- */
  function resolveWeather() {
    var s = store.settings();
    if (s.weather && s.weather !== 'auto') return s.weather;
    var h = new Date().getHours();
    if (h >= 19 || h < 6) return 'night';
    var t = store.today();
    if (t && t.valence <= 2) return 'rainy';
    return 'sunny';
  }

  function paintWeather(w) {
    el.scene.dataset.weather = w;
    el.tint.dataset.weather = w;
    Array.prototype.forEach.call(el.weatherSwitch.children, function (b) {
      b.classList.toggle('on', b.dataset.w === w);
    });
    // 夜晚时把首页文字调亮
    document.body.classList.toggle('night-mode', w === 'night');
  }

  /* ---------------- 问候 ---------------- */
  function greetText() {
    var t = store.today();
    var h = new Date().getHours();
    var night = h >= 19 || h < 6;

    if (!t) {
      if (night) return ['今天岛上很安静。', '还没记今天。不急，想起来再来。'];
      return ['今天岛上没什么风。', '要不要去信箱说说今天。'];
    }
    var v = t.valence;
    if (v >= 4) return night
      ? ['今天岛上星星很多。', '这一天已经收好了。']
      : ['今天岛上太阳很好。', '这一天已经收好了。'];
    if (v === 3) return night
      ? ['今天夜里云很淡。', '记下了，普通的一天也算一天。']
      : ['今天云淡淡的。', '记下了，普通的一天也算一天。'];
    if (v === 2) return night
      ? ['今天夜里下了点雨。', '记下了。不必今天就变好。']
      : ['今天有点阴。', '记下了。不必今天就变好。'];
    return night
      ? ['今天岛上一直在下雨。', '记下了。我在这儿待着。']
      : ['今天岛上在下雨。', '记下了。我在这儿待着。'];
  }

  /* ---------------- 今日状态 ---------------- */
  function applyToday() {
    var t = store.today();
    var g = greetText();
    el.greetLine.textContent = g[0];
    el.greetSub.textContent = g[1];
    el.mailBadge.hidden = !!t;
    paintWeather(resolveWeather());
    document.body.classList.toggle('has-today', !!t);
  }

  function applySettings() {
    var s = store.settings();
    document.body.classList.toggle('no-motion', !s.motion);
    paintWeather(resolveWeather());
    var sd = sound;
    if (sd) {
      sd.setEnabled(s.sound);
      // 雨声跟着天气走，但只有开了声音才响
      sd.rain(!!s.sound && resolveWeather() === 'rainy');
    }
  }

  /* ---------------- 仪式 ---------------- */
  function ritual(v) {
    return new Promise(function (resolve) {
      el.ritualImg.src = 'assets/moods/sprites/mood-' + v + '-t.png';
      var lines = {
        1: '今天很沉。我收好了。',
        2: '不太好的一天，也记下了。',
        3: '普通的一天，也值得留着。',
        4: '今天还不错。存进花园了。',
        5: '今天很好。我替你记着。'
      };
      el.ritualText.textContent = lines[v] || '记下了。';
      el.ritual.hidden = false;
      setTimeout(function () {
        el.ritual.hidden = true;
        resolve();
      }, 1750);
    });
  }

  function afterSave(entry) {
    if (sound) sound.chime();
    ritual(entry.valence).then(function () {
      // 先把地址清回岛上，再关纸卡，否则刷新会重新打开记录页
      if (!setUrlNoHash('replace')) {
        try { location.hash = ''; } catch (e) {}
      }
      closeSheet(true);
      applyToday();
      var happy = ['收好了', '存进花园了', '记下了', '今天也算数'];
      setTimeout(function () {
        fox.react('happy');
        fox.say(happy[(Math.random() * happy.length) | 0], 2000);
      }, 320);
    });
  }

  /* ---------------- 路由 ---------------- */
  var TITLES = {
    record: '写今天',
    garden: '情绪花园',
    analysis: '观测台',
    calendar: '公告板',
    cabin: '小木屋'
  };

  function openSheet(name, params) {
    if (!views[name]) { go('#/'); return; }
    // 上一张纸卡可能还在关场动画里：把它挂着的定时器取消，
    // 否则它会在 230ms 后把刚打开的这张一起清掉（点了物件却看到空岛）
    clearTimeout(closeTimer);
    closing = false;
    el.sheet.hidden = false;
    el.sheet.classList.remove('closing');
    el.sheetBody.innerHTML = '';
    el.sheetBody.scrollTop = 0;
    views[name](el.sheetBody, params);
    current = name;
    fox.pause();
  }

  function closeSheet(immediate) {
    clearTimeout(closeTimer);
    if (el.sheet.hidden) { closing = false; return; }
    if (immediate) {
      el.sheet.hidden = true;
      el.sheet.classList.remove('closing');
      el.sheetBody.innerHTML = '';
      current = null;
      closing = false;
      safeResume();
      return;
    }
    closing = true;
    el.sheet.classList.add('closing');
    closeTimer = setTimeout(function () {
      el.sheet.hidden = true;
      el.sheet.classList.remove('closing');
      el.sheetBody.innerHTML = '';
      current = null;
      closing = false;
      safeResume();
    }, 230);
  }

  /* 狐狸动了动不了都不该拦住"回岛上" */
  function safeResume() {
    try { fox.resume(); } catch (e) { if (global.console) console.error(e); }
  }

  function route() {
    var r = parseHash();
    if (!r.name) {
      closeSheet(true);
      applyToday();
      return;
    }
    openSheet(r.name, r.params);
  }

  function go(hash) {
    if (location.hash === hash) { route(); return; }
    location.hash = hash;
  }

  /* ---------------- 地址栏 ----------------
     地址栏里的 #/xxx 只是"现在开着哪张纸卡"的记号。清它有两种写法：
     优先 history API（不产生历史记录、不触发 hashchange）；
     但 file:// 直开、以及某些预览面板的沙箱 iframe 里 pushState/replaceState
     会抛 SecurityError，所以一定要有退路 —— 退成改 hash，
     它一定会触发 hashchange，route() 会把纸卡关掉。 */
  function setUrlNoHash(mode) {
    try {
      var fn = mode === 'replace' ? history.replaceState : history.pushState;
      fn.call(history, '', document.title, location.pathname + location.search);
      return true;
    } catch (e) {
      return false;
    }
  }

  function clearHash() {
    if (!location.hash) return;
    if (setUrlNoHash('push')) return;
    try { location.hash = ''; } catch (e) {}
  }

  function backToIsland() {
    // 先关纸卡，再做地址栏的事：地址栏出任何问题都不该让按钮看起来是坏的
    closeSheet();
    clearHash();
    try { applyToday(); } catch (e) { if (global.console) console.error(e); }
    if (document.activeElement && document.activeElement.blur) document.activeElement.blur();
  }

  /* ---------------- 初始化 ---------------- */
  function init() {
    el = {
      scene: $('#scene'),
      tint: $('#sceneTint'),
      greetLine: $('#greetLine'),
      greetSub: $('#greetSub'),
      mailBadge: $('#mailBadge'),
      weatherSwitch: $('#weatherSwitch'),
      sheet: $('#sheet'),
      sheetBody: $('#sheetBody'),
      ritual: $('#ritual'),
      ritualImg: $('#ritualImg'),
      ritualText: $('#ritualText'),
      toast: $('#toast'),
      footHint: $('#footHint'),
      demoChip: $('#demoChip')
    };

    // 演示模式：告诉来访的人这是示例数据，而不是他的记录
    if (store.isDemo && store.isDemo()) {
      if (el.demoChip) el.demoChip.hidden = false;
      if (el.footHint) el.footHint.textContent = '演示数据 · 记一天，看花园长出来';
    }

    applyToday();
    applySettings();

    // 物件跳转
    Array.prototype.forEach.call(document.querySelectorAll('.item'), function (b) {
      b.addEventListener('click', function () {
        if (sound) sound.tick();
        go(b.dataset.go);
      });
    });

    $('#btnSettings').addEventListener('click', function () { go('#/cabin'); });

    // 天气手动切换
    Array.prototype.forEach.call(el.weatherSwitch.children, function (b) {
      b.addEventListener('click', function () {
        store.set('weather', b.dataset.w);
        paintWeather(b.dataset.w);
      });
    });

    // 返回：绑在 document 上，纸卡内容怎么重建都不会丢这个事件。
    // 顺手让"点纸卡外面的暗底"也能回岛上。
    document.addEventListener('click', function (e) {
      var t = e.target;
      if (!t || !t.closest) return;
      if (t.closest('.sheet-back')) {
        e.preventDefault();
        backToIsland();
        return;
      }
      if (t === el.sheet) backToIsland();
    });

    // 岛民
    fox.init({
      root: $('#fox'),
      flip: $('#foxFlip'),
      body: $('#foxBody'),
      layerA: $('#foxLayerA'),
      layerB: $('#foxLayerB'),
      bubble: $('#foxBubble'),
      shadow: $('#foxShadow')
    });

    // 没记录时，狐狸过一会儿提一句（一天最多一次）
    if (!store.hasToday()) {
      var s = store.settings();
      var todayKey = store.todayKey();
      if (!s.reminded || s.reminded.date !== todayKey) {
        setTimeout(function () {
          if (current) return;
          fox.say('信箱在那边', 2400);
          store.set('reminded', { date: todayKey });
        }, 6000);
      }
    }

    window.addEventListener('hashchange', route);
    window.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && current) backToIsland();
    });

    // 手机返回手势
    window.addEventListener('popstate', function () {
      if (!parseHash().name && current) closeSheet();
    });

    route();

    // 跨过零点后刷新问候
    setInterval(function () {
      if (!current) applyToday();
    }, 60000);
  }

  global.App = global.App || {};
  global.App.app = {
    init: init,
    go: go,
    toast: toast,
    applyToday: applyToday,
    applySettings: applySettings,
    afterSave: afterSave,
    onPetFox: function () {}
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})(window);
