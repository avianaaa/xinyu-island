/* ===========================================================
   store.js —— 数据层
   目前写 localStorage；接口刻意做成异步，将来换成 Supabase 只改这里。
   结构里带 user_id，不写死单例。
   =========================================================== */
(function (global) {
  'use strict';

  var KEY = 'xinyu.v1';
  var USER_ID = 'local-user';

  /* ---------- 演示模式 ----------
     ?demo=1 时用 scripts/demo-data.js 里那份模拟数据，且：
       · 只活在内存里，从不读写 localStorage
       · 所以访客可以随便点、随便记，关掉页面就干净了
       · 也不会污染他自己这台机器上以后真用时的数据
     接口和真实模式一模一样，上层代码不需要知道自己在演示模式里。 */
  var DEMO = false;
  try {
    DEMO = /(?:^\?|&)demo=1(?:&|$)/.test(String(location.search || ''));
  } catch (e) { DEMO = false; }

  var DEFAULT_SETTINGS = {
    weather: 'auto',      // auto | sunny | rainy | night
    motion: true,
    sound: false,
    animal: 'fox',
    reminded: {}          // 记录「今天是否已经主动表达过一次」
  };

  var state = null;

  /* ---------- 日期工具 ---------- */
  function pad(n) { return (n < 10 ? '0' : '') + n; }

  function keyOf(d) {
    d = d || new Date();
    return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
  }

  function parseKey(k) {
    var p = k.split('-');
    return new Date(+p[0], +p[1] - 1, +p[2]);
  }

  function daysAgo(n) {
    var d = new Date();
    d.setHours(0, 0, 0, 0);
    d.setDate(d.getDate() - n);
    return d;
  }

  function diffDays(a, b) {
    return Math.round((parseKey(b) - parseKey(a)) / 86400000);
  }

  /* ---------- 读写 ---------- */
  function blank() {
    return {
      version: 1,
      user_id: USER_ID,
      entries: [],
      settings: Object.assign({}, DEFAULT_SETTINGS)
    };
  }

  function load() {
    if (state) return state;
    if (DEMO) { state = buildDemo(); return state; }
    try {
      var raw = localStorage.getItem(KEY);
      state = raw ? JSON.parse(raw) : blank();
    } catch (e) {
      state = blank();
    }
    if (!state || !Array.isArray(state.entries)) state = blank();
    state.settings = Object.assign({}, DEFAULT_SETTINGS, state.settings || {});
    state.entries.sort(function (a, b) { return a.date < b.date ? -1 : 1; });
    return state;
  }

  /* 把 demo-data.js 的「距今天数」换算成真实日期。
     最后一条落在昨天：今天空着，访客才能自己走一遍记录流程。 */
  function buildDemo() {
    var s = blank();
    var src = (global.App && global.App.demoEntries) || [];
    src.forEach(function (row) {
      var k = keyOf(daysAgo(row[0]));
      s.entries.push({
        id: 'demo_' + k.replace(/-/g, ''),
        user_id: s.user_id,
        date: k,
        valence: row[1],
        energy: row[2],
        tags: row[3] ? String(row[3]).split('|').filter(Boolean) : [],
        note: row[4] || '',
        createdAt: 0,
        updatedAt: 0,
        demo: true
      });
    });
    s.entries.sort(function (a, b) { return a.date < b.date ? -1 : 1; });
    return s;
  }

  function persist() {
    if (DEMO) return;                      // 演示模式不落盘
    try {
      localStorage.setItem(KEY, JSON.stringify(state));
    } catch (e) {
      console.warn('[心屿] 本地存储写入失败', e);
    }
  }

  /* ---------- 对外 ---------- */
  var api = {
    todayKey: function () { return keyOf(new Date()); },
    keyOf: keyOf,
    parseKey: parseKey,
    daysAgo: daysAgo,
    diffDays: diffDays,

    all: function () {
      return load().entries.slice();
    },

    /** 按日期升序，取最近 n 天（含今天） */
    recent: function (n) {
      var list = load().entries;
      var from = keyOf(daysAgo(n - 1));
      return list.filter(function (e) { return e.date >= from; });
    },

    /** 某一段日期之间的记录 */
    between: function (fromKey, toKey) {
      return load().entries.filter(function (e) {
        return e.date >= fromKey && e.date <= toKey;
      });
    },

    get: function (dateKey) {
      var list = load().entries;
      for (var i = 0; i < list.length; i++) {
        if (list[i].date === dateKey) return list[i];
      }
      return null;
    },

    today: function () { return api.get(keyOf(new Date())); },

    hasToday: function () { return !!api.today(); },

    /** 一天一条：同一天再记就是覆盖 */
    save: function (data) {
      var s = load();
      var date = data.date || keyOf(new Date());
      var found = null;
      for (var i = 0; i < s.entries.length; i++) {
        if (s.entries[i].date === date) { found = s.entries[i]; break; }
      }
      if (found) {
        found.valence = data.valence;
        found.energy = data.energy;
        found.tags = data.tags || [];
        found.note = data.note || '';
        found.updatedAt = Date.now();
      } else {
        s.entries.push({
          id: 'e_' + date.replace(/-/g, '') + '_' + Math.random().toString(36).slice(2, 7),
          user_id: s.user_id,
          date: date,
          valence: data.valence,
          energy: data.energy,
          tags: data.tags || [],
          note: data.note || '',
          createdAt: Date.now(),
          updatedAt: Date.now()
        });
      }
      s.entries.sort(function (a, b) { return a.date < b.date ? -1 : 1; });
      persist();
      return api.get(date);
    },

    remove: function (dateKey) {
      var s = load();
      s.entries = s.entries.filter(function (e) { return e.date !== dateKey; });
      persist();
    },

    /* ---- 设置 ---- */
    settings: function () { return load().settings; },
    set: function (k, v) {
      load().settings[k] = v;
      persist();
    },

    /* ---- 连续记录天数（今天没记则从昨天算起）---- */
    streak: function () {
      var list = load().entries;
      if (!list.length) return 0;
      var set = {};
      list.forEach(function (e) { set[e.date] = 1; });
      var n = 0, d = new Date();
      d.setHours(0, 0, 0, 0);
      if (!set[keyOf(d)]) d.setDate(d.getDate() - 1);
      while (set[keyOf(d)]) {
        n++;
        d.setDate(d.getDate() - 1);
      }
      return n;
    },

    /* ---- 导入导出 ---- */
    dump: function () {
      return JSON.stringify(load(), null, 2);
    },

    wipe: function () {
      if (DEMO) { state = buildDemo(); return; }   // 演示模式下「清空」= 重置成初始样子
      var keep = load().settings;
      state = blank();
      state.settings = keep;
      persist();
    },

    /** 当前是否是演示模式（只读） */
    isDemo: function () { return DEMO; },

    /* ---- 示例数据（只为让人先看见效果，随时可清）---- */
    seedDemo: function () {
      var s = load();
      var tagPool = {
        1: ['疲惫', '孤单', '麻木', '睡不着', '工作'],
        2: ['疲惫', '焦躁', '工作', '独处', '头痛'],
        3: ['平静', '休息', '学习', '朋友', '身体轻松'],
        4: ['开心', '期待', '朋友', '出门', '有活力'],
        5: ['开心', '感激', '运动', '有活力', '期待']
      };
      var notes = [
        '', '', '今天有点撑不住，但还是过完了。', '', '路上看到一只很胖的猫。',
        '', '开完会觉得空空的。', '', '', '和朋友吃了饭，笑了好几次。',
        '', '睡不好，脑子一直在转。', '', '', '今天什么都没做，也没关系。'
      ];
      // 造一段有起伏的两周 + 一段平稳的，便于看分析效果
      var plan = [2, 3, 2, 1, 2, 3, 3, 4, 3, 2, 2, 3, 4, 5, 4, 3, 4, 5, 4, 4, 3, 3, 4, 5, 4, 3, 3, 4, 3, 4];
      plan.forEach(function (v, i) {
        var idx = plan.length - 1 - i;        // 0 = 今天
        if (idx === 0) return;                // 今天留给用户自己记
        var d = daysAgo(idx);
        var k = keyOf(d);
        if (api.get(k)) return;
        var val = v;
        var energy = Math.max(1, Math.min(5, val === 1 ? 2 : val === 5 ? 4 : val + (i % 3 === 0 ? -1 : 0)));
        s.entries.push({
          id: 'demo_' + k.replace(/-/g, ''),
          user_id: s.user_id,
          date: k,
          valence: val,
          energy: energy,
          tags: (tagPool[val] || []).slice(0, 2 + (i % 2)),
          note: notes[i % notes.length],
          createdAt: Date.now(),
          updatedAt: Date.now(),
          demo: true
        });
      });
      s.entries.sort(function (a, b) { return a.date < b.date ? -1 : 1; });
      persist();
    }
  };

  global.App = global.App || {};
  global.App.store = api;
})(window);
