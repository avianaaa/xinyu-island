/* ===========================================================
   views.js —— 五个子页面的渲染
   记录 / 花园 / 分析 / 日历 / 小木屋
   =========================================================== */
(function (global) {
  'use strict';

  var store = global.App.store;
  var A = global.App.analysis;
  var PLANT = global.App.plant;

  var MOOD_WORDS = ['很差', '有点低', '还行', '挺好', '很好'];
  var ENERGY_WORDS = ['没力气', '有点累', '一般', '还行', '有劲'];

  var TAG_GROUPS = [
    { name: '感受', tags: ['平静', '安心', '开心', '期待', '烦躁', '焦虑', '委屈', '孤单', '麻木', '生气', '内疚', '感激'] },
    { name: '身体', tags: ['疲惫', '睡不着', '头痛', '胃不舒服', '身体轻松', '有活力'] },
    { name: '场景', tags: ['工作', '学习', '家人', '朋友', '独处', '出门', '运动', '休息'] }
  ];

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function moodImg(v) {
    return 'assets/moods/sprites/mood-' + v + '-t.png';
  }

  /* ---------- CSV（导出 / 导回来都用它）----------
     给 Excel 看的表：一行一天，列名中文，UTF-8 带 BOM，
     不然 Excel 打开是乱码。备注里的逗号、换行、引号都要转义。 */
  function csvCell(v) {
    var s = (v == null ? '' : String(v));
    return /[",\n\r]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  }

  /* 时间戳自己拼，不用 toLocaleString：
     有些环境没有 zh-CN 的语言数据，会退回 en-US 变成 "10/2/2025, 3:45 AM"，
     既带逗号又是英文顺序，Excel 里没法按时间排。 */
  function csvTime(ms) {
    if (!ms) return '';
    var d = new Date(ms);
    function p2(n) { return (n < 10 ? '0' : '') + n; }
    return d.getFullYear() + '-' + p2(d.getMonth() + 1) + '-' + p2(d.getDate()) +
      ' ' + p2(d.getHours()) + ':' + p2(d.getMinutes());
  }

  function entriesToCsv(entries) {
    var rows = [['日期', '心情', '心情描述', '力气', '力气描述', '标签', '备注', '记录时间'].join(',')];
    entries.forEach(function (e) {
      rows.push([
        e.date,
        e.valence,
        MOOD_WORDS[e.valence - 1] || '',
        e.energy,
        ENERGY_WORDS[e.energy - 1] || '',
        (e.tags || []).join('|'),
        e.note || '',
        csvTime(e.updatedAt || e.createdAt)
      ].map(csvCell).join(','));
    });
    return '\ufeff' + rows.join('\r\n') + '\r\n';
  }

  /** 极简 CSV 解析：支持双引号包裹、"" 转义、CRLF */
  function parseCsv(text) {
    text = String(text).replace(/^\ufeff/, '');
    var rows = [], row = [], cell = '', quoted = false;
    for (var i = 0; i < text.length; i++) {
      var c = text.charAt(i);
      if (quoted) {
        if (c === '"') {
          if (text.charAt(i + 1) === '"') { cell += '"'; i++; }
          else quoted = false;
        } else cell += c;
        continue;
      }
      if (c === '"') quoted = true;
      else if (c === ',') { row.push(cell); cell = ''; }
      else if (c === '\n') { row.push(cell); rows.push(row); row = []; cell = ''; }
      else if (c !== '\r') cell += c;
    }
    if (cell !== '' || row.length) { row.push(cell); rows.push(row); }
    return rows.filter(function (r) {
      return r.some(function (x) { return String(x).trim() !== ''; });
    });
  }

  /** 认列名，不认位置 —— 用户可能在 Excel 里删过/挪过列 */
  function csvToEntries(text) {
    var rows = parseCsv(text);
    if (rows.length < 2) throw new Error('空表');
    var head = rows[0].map(function (h) { return String(h).trim(); });
    function col() {
      for (var i = 0; i < arguments.length; i++) {
        var k = head.indexOf(arguments[i]);
        if (k >= 0) return k;
      }
      return -1;
    }
    var iDate = col('日期', 'date'), iV = col('心情', 'valence'), iE = col('力气', 'energy'),
        iT = col('标签', 'tags'), iN = col('备注', 'note');
    if (iDate < 0 || iV < 0) throw new Error('缺少日期或心情列');

    var out = [];
    rows.slice(1).forEach(function (r) {
      var date = String(r[iDate] || '').trim();
      var v = parseInt(r[iV], 10);
      if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || !(v >= 1 && v <= 5)) return;
      var en = iE >= 0 ? parseInt(r[iE], 10) : 3;
      if (!(en >= 1 && en <= 5)) en = 3;
      var tags = iT >= 0 ? String(r[iT] || '').split(/[|、;；]+/).filter(function (t) { return t.trim(); })
        .map(function (t) { return t.trim(); }) : [];
      out.push({ date: date, valence: v, energy: en, tags: tags, note: iN >= 0 ? String(r[iN] || '') : '' });
    });
    return out;
  }

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $$(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }

  /* ==========================================================
     1. 记录页
     ========================================================== */
  var recordState = null;

  function renderRecord(root) {
    var today = store.today();
    recordState = {
      valence: today ? today.valence : 0,
      energy: today ? today.energy : 0,
      tags: today ? today.tags.slice() : [],
      note: today ? today.note : ''
    };

    var moodCells = MOOD_WORDS.map(function (w, i) {
      var v = i + 1;
      return '<button class="mood-pick' + (recordState.valence === v ? ' on' : '') + '" data-v="' + v + '">' +
        '<img src="' + moodImg(v) + '" alt="' + w + '">' +
        '<span>' + w + '</span></button>';
    }).join('');

    var energyCells = ENERGY_WORDS.map(function (w, i) {
      var v = i + 1;
      return '<button class="energy-dot' + (recordState.energy === v ? ' on' : '') + '" data-e="' + v + '">' +
        '<i></i><span>' + w + '</span></button>';
    }).join('');

    var tagHtml = TAG_GROUPS.map(function (g) {
      return '<div><div class="tag-group-name">' + g.name + '</div><div class="tags">' +
        g.tags.map(function (t) {
          var on = recordState.tags.indexOf(t) >= 0;
          return '<button class="tag' + (on ? ' on' : '') + '" data-t="' + esc(t) + '">' + esc(t) + '</button>';
        }).join('') + '</div></div>';
    }).join('');

    root.innerHTML =
      '<h1 class="page-title">' + (today ? '今天的岛，要不要改一下' : '今天岛上天气如何') + '</h1>' +
      '<p class="page-sub">' + (today ? '你已经记过一次，改完会覆盖今天这一条。' : '三步，十秒。所有项都能跳过。') + '</p>' +

      '<div class="rec-step">' +
        '<div class="rec-step-head"><span class="rec-step-num">一</span>' +
        '<span class="rec-step-title">今天感觉怎么样</span></div>' +
        '<div class="mood-row">' + moodCells + '</div>' +
      '</div>' +

      '<div class="rec-step">' +
        '<div class="rec-step-head"><span class="rec-step-num">二</span>' +
        '<span class="rec-step-title">身上有多少力气</span>' +
        '<span class="rec-step-hint">和心情是两件事</span></div>' +
        '<div class="energy-row">' + energyCells + '</div>' +
      '</div>' +

      '<div class="rec-step">' +
        '<div class="rec-step-head"><span class="rec-step-num">三</span>' +
        '<span class="rec-step-title">贴几个词</span>' +
        '<span class="rec-step-hint">可以不贴</span></div>' +
        '<div class="tag-groups">' + tagHtml + '</div>' +
      '</div>' +

      '<div class="rec-step">' +
        '<div class="rec-step-head"><span class="rec-step-num">四</span>' +
        '<span class="rec-step-title">留一句话</span>' +
        '<span class="rec-step-hint">也可以不写</span></div>' +
        '<div class="note-wrap">' +
          '<textarea class="note-input" id="noteInput" maxlength="300" ' +
          'placeholder="今天发生了什么，或者什么都不用说。">' + esc(recordState.note) + '</textarea>' +
          '<span class="note-count" id="noteCount">' + recordState.note.length + '/300</span>' +
        '</div>' +
      '</div>' +

      '<button class="btn-primary" id="saveBtn"' + (recordState.valence ? '' : ' disabled') + '>' +
        (today ? '改好了' : '记下今天') + '</button>';

    // ---- 绑定 ----
    $$('.mood-pick', root).forEach(function (b) {
      b.addEventListener('click', function () {
        recordState.valence = +b.dataset.v;
        $$('.mood-pick', root).forEach(function (x) { x.classList.toggle('on', x === b); });
        $('#saveBtn', root).disabled = false;
      });
    });

    $$('.energy-dot', root).forEach(function (b) {
      b.addEventListener('click', function () {
        recordState.energy = +b.dataset.e;
        $$('.energy-dot', root).forEach(function (x) { x.classList.toggle('on', x === b); });
      });
    });

    $$('.tag', root).forEach(function (b) {
      b.addEventListener('click', function () {
        var t = b.dataset.t;
        var i = recordState.tags.indexOf(t);
        if (i >= 0) recordState.tags.splice(i, 1); else recordState.tags.push(t);
        b.classList.toggle('on', i < 0);
      });
    });

    var note = $('#noteInput', root);
    note.addEventListener('input', function () {
      recordState.note = note.value;
      $('#noteCount', root).textContent = note.value.length + '/300';
    });

    $('#saveBtn', root).addEventListener('click', function () {
      if (!recordState.valence) {
        App.app.toast('先选一个今天的感觉吧');
        return;
      }
      var e = store.save({
        valence: recordState.valence,
        energy: recordState.energy || 3,
        tags: recordState.tags,
        note: recordState.note.trim()
      });
      App.app.afterSave(e);
    });
  }

  /* ==========================================================
     2. 情绪花园
     ========================================================== */
  function renderGarden(root) {
    var list = store.all();
    var streak = store.streak();

    if (!list.length) {
      root.innerHTML =
        '<h1 class="page-title">情绪花园</h1>' +
        '<p class="page-sub">每记一天，这里就长出一株。颜色是那天的心情，高矮是那天的力气。</p>' +
        '<div class="empty-state">' +
          '<img src="' + moodImg(3) + '" alt="">' +
          '<h3>这里还是空的</h3>' +
          '<p>去信箱写一次，第一株就长出来了。</p>' +
          '<button class="btn-ghost" data-go="#/record">去写今天</button>' +
        '</div>';
      bindNav(root);
      return;
    }

    // 近 90 天，按日期升序
    var recent = list.slice(-90);
    var plants = recent.map(function (e, i) {
      var d = store.parseKey(e.date);
      var tip = d.getMonth() + 1 + '月' + d.getDate() + '日 · ' + MOOD_WORDS[e.valence - 1] +
        (e.tags && e.tags.length ? ' · ' + e.tags.join('、') : '');
      return '<div class="plant" title="' + esc(tip) + '">' +
        '<div class="plant-sway" style="animation-delay:' + ((i * 0.37) % 3).toFixed(2) + 's">' +
        PLANT.svg(e, i) + '</div></div>';
    }).join('');

    root.innerHTML =
      '<h1 class="page-title">情绪花园</h1>' +
      '<p class="page-sub">共 ' + list.length + ' 株' +
        (streak > 1 ? '，你连着来了 ' + streak + ' 天' : '') +
        '。花开了是那天不错，花苞垂着是那天不太好。</p>' +
      '<div class="garden-stage"><div class="garden-grid">' + plants + '</div></div>' +
      '<div class="garden-legend">' +
        '<span><i style="background:#9DB3C6"></i>很差</span>' +
        '<span><i style="background:#A9B48F"></i>有点低</span>' +
        '<span><i style="background:#CFC29B"></i>还行</span>' +
        '<span><i style="background:#E7AC94"></i>挺好</span>' +
        '<span><i style="background:#E08A5C"></i>很好</span>' +
        '<span>高矮 = 那天有多少力气</span>' +
      '</div>' +
      '<div class="rule"></div>' +
      '<p class="page-sub" style="margin-bottom:0">最近 90 天。更早的记录在公告板里能翻到。</p>';
  }

  /* ==========================================================
     3. 观测台（分析）
     ========================================================== */
  function renderAnalysis(root, params) {
    var range = (params && params.range) || 'week';
    var r = A.report(range);

    if (r.n < 1) {
      root.innerHTML =
        '<h1 class="page-title">观测台</h1>' +
        '<p class="page-sub">这里会把你记下的东西，慢慢摊开给你看。</p>' +
        '<div class="empty-state">' +
          '<img src="assets/items/sprites/item-scope-t.webp" alt="">' +
          '<h3>还没有可分析的东西</h3>' +
          '<p>记满 4 天，这里就会有第一张图。</p>' +
          '<button class="btn-ghost" data-go="#/record">去写今天</button>' +
        '</div>';
      bindNav(root);
      return;
    }

    var tabs = ['week:这周', 'month:这月', 'year:这一年'].map(function (p) {
      var kv = p.split(':');
      return '<button data-range="' + kv[0] + '"' + (kv[0] === range ? ' class="on"' : '') + '>' + kv[1] + '</button>';
    }).join('');

    var html = '<h1 class="page-title">观测台</h1>' +
      '<p class="page-sub">不是打分表，只是把你自己看不见的部分画出来。</p>' +
      '<div class="range-tabs" id="rangeTabs">' + tabs + '</div>';

    if (r.n < 4) {
      html += '<p class="page-sub" style="margin:-10px 0 22px;color:var(--ink-3)">' +
        '才记了 ' + r.n + ' 天，线还连不起来。再记几天，这里会慢慢有东西看。</p>';
    }

    /* --- 关怀卡 --- */
    if (r.care === 'strong') {
      html +=
        '<div class="care-card">' +
          '<h3>我想认真对待你写下的这些</h3>' +
          '<p>最近这段时间，你写的东西里有让我停下来的句子。我不打算在这里分析它，也不想给你一个结论。</p>' +
          '<p>如果这种状态已经持续了一段时间，找个人说一说会比继续一个人扛要好——不一定是专业的人，先是一个具体的人。</p>' +
          '<p>如果某一刻你觉得撑不住，可以直接打这个电话，24 小时有人接：</p>' +
          '<div class="hotline"><b>12356</b><span>全国统一心理援助热线</span></div>' +
        '</div>';
    } else if (r.care === 'gentle') {
      html +=
        '<div class="care-card">' +
          '<h3>有件事想说一下</h3>' +
          '<p>你写下的有些话，比分数本身更值得被听见。数据只能看到你选了第几分，看不到那句话背后的重量。</p>' +
          '<p>如果愿意，找一个能听你说话的人——朋友、家人，或者热线 12356，都算。</p>' +
        '</div>';
    }

    /* --- 建议卡 --- */
    if (r.cards.length) {
      var c = r.cards[0];
      html +=
        '<div class="advice" data-kind="' + c.kind + '">' +
          '<div class="advice-line"><span class="advice-tag">看到</span><span class="advice-text">' + esc(c.seen) + '</span></div>' +
          '<div class="advice-line"><span class="advice-tag">也许</span><span class="advice-text">' + esc(c.maybe) + '</span></div>' +
          '<div class="advice-line"><span class="advice-tag">试试</span><span class="advice-text">' + esc(c.tryIt) + '</span></div>' +
          '<div class="advice-line"><span class="advice-tag">我在</span><span class="advice-text">' + esc(c.here) + '</span></div>' +
          '<div class="advice-foot"><span>这只是根据数据做的猜测，不对的地方请忽略</span>' +
          '<button class="btn-ghost" id="noComfort">今天不想被安慰</button></div>' +
        '</div>';
    }

    /* --- 统计 --- */
    var s = r.stats;
    html +=
      '<div class="stat-grid">' +
        '<div class="stat"><div class="stat-k">记录</div><div class="stat-v">' + s.n + '<small>天</small></div>' +
          '<div class="stat-note">' + r.span + '里</div></div>' +
        '<div class="stat"><div class="stat-k">平均心情</div><div class="stat-v">' + s.avgValence + '<small>/5</small></div>' +
          '<div class="stat-note">' + MOOD_WORDS[Math.round(s.avgValence) - 1] + '</div></div>' +
        '<div class="stat"><div class="stat-k">平均力气</div><div class="stat-v">' + s.avgEnergy + '<small>/5</small></div>' +
          '<div class="stat-note">' + ENERGY_WORDS[Math.round(s.avgEnergy) - 1] + '</div></div>' +
        '<div class="stat"><div class="stat-k">起伏</div><div class="stat-v">' + s.sdValence + '</div>' +
          '<div class="stat-note">' + (s.sdValence >= 1.05 ? '比平常晃' : '还算稳') + '</div></div>' +
      '</div>';

    /* --- 图 1：曲线 --- */
    html +=
      '<div class="chart-card">' +
        '<p class="chart-title">心情的走向</p>' +
        '<p class="chart-desc">' + (range === 'year'
          ? '每周的平均，共 ' + r.series.length + ' 周，线是心情，浅色是力气'
          : '最近 ' + r.series.length + ' 天的记录，线是心情，浅色是力气') + '</p>' +
        lineChart(r.series) +
      '</div>';

    /* --- 图 2：象限 --- */
    html +=
      '<div class="chart-card">' +
        '<p class="chart-title">心情 × 力气</p>' +
        '<p class="chart-desc">同样说「还行」，落在上面和下面其实不一样</p>' +
        quadrantChart(r.series) +
      '</div>';

    /* --- 图 3：星期 --- */
    if (range !== 'week') {
      html +=
        '<div class="chart-card">' +
          '<p class="chart-title">一周里的哪天</p>' +
          '<p class="chart-desc">看看是不是某个固定的日子总在往下掉</p>' +
          weekdayChart(r.weekday) +
        '</div>';
    }

    /* --- 年视图：按月（固定 12 格，没记的月份也占位，不然月份会骗人）--- */
    if (range === 'year' && r.months.length) {
      var filled = r.months.filter(function (m) { return m.n > 0; }).length;
      var firstM = r.months[0], lastM = r.months[r.months.length - 1];
      html +=
        '<div class="chart-card">' +
          '<p class="chart-title">每个月的样子</p>' +
          '<p class="chart-desc">' + firstM.year + ' 年 ' + (+firstM.key.slice(5)) + ' 月 – ' +
            lastM.year + ' 年 ' + (+lastM.key.slice(5)) + ' 月，' +
            filled + ' 个月有记录，柱子上是当月平均</p>' +
          monthChart(r.months) +
        '</div>';
    }

    root.innerHTML = html;

    /* --- 交互 --- */
    $$('#rangeTabs button', root).forEach(function (b) {
      b.addEventListener('click', function () {
        App.app.go('#/analysis?range=' + b.dataset.range);
      });
    });
    var nc = $('#noComfort', root);
    if (nc) {
      nc.addEventListener('click', function () {
        var card = nc.closest('.advice');
        card.style.transition = 'opacity .3s, transform .3s';
        card.style.opacity = '0';
        card.style.transform = 'translateY(-6px)';
        setTimeout(function () { card.remove(); }, 320);
        App.app.toast('好，那就先不说');
      });
    }
    bindNav(root);
  }

  /* ---------- 图表 ---------- */

  function lineChart(series) {
    if (!series.length) return '<p class="chart-desc">这段时间还没有记录。</p>';
    var W = 620, H = 190, PL = 24, PR = 10, PT = 12, PB = 22;
    var n = series.length;
    var iw = W - PL - PR, ih = H - PT - PB;

    function X(i) { return PL + (n === 1 ? iw / 2 : (iw / (n - 1)) * i); }
    function Y(v) { return PT + (1 - (v - 1) / 4) * ih; }

    var pts = series.map(function (e, i) { return [X(i), Y(e.valence)]; });
    var epts = series.map(function (e, i) { return [X(i), Y(e.energy)]; });

    function smooth(p) {
      if (!p.length) return '';
      if (p.length === 1) return 'M' + p[0][0] + ' ' + p[0][1];
      var d = 'M' + p[0][0] + ' ' + p[0][1];
      for (var i = 1; i < p.length; i++) {
        var mx = (p[i - 1][0] + p[i][0]) / 2, my = (p[i - 1][1] + p[i][1]) / 2;
        d += ' Q' + p[i - 1][0] + ' ' + p[i - 1][1] + ' ' + mx + ' ' + my;
      }
      var lp = p[p.length - 1];
      d += ' L' + lp[0] + ' ' + lp[1];
      return d;
    }

    var lineD = smooth(pts);
    var areaD = lineD + ' L' + pts[pts.length - 1][0] + ' ' + (PT + ih) + ' L' + pts[0][0] + ' ' + (PT + ih) + ' Z';

    var grid = '';
    for (var v = 1; v <= 5; v++) {
      grid += '<line x1="' + PL + '" x2="' + (W - PR) + '" y1="' + Y(v) + '" y2="' + Y(v) +
        '" stroke="rgba(139,111,82,' + (v === 3 ? '.18' : '.10') + ')" stroke-width="1"/>';
      grid += '<text x="' + (PL - 6) + '" y="' + (Y(v) + 3.5) + '" text-anchor="end" font-size="9" ' +
        'fill="#96897A">' + v + '</text>';
    }

    var dots = pts.map(function (p, i) {
      var v = series[i].valence;
      var col = PLANT.COLORS[v] ? PLANT.COLORS[v].petal : '#C9BFA0';
      return '<circle cx="' + p[0] + '" cy="' + p[1] + '" r="3.1" fill="' + col + '" stroke="#FBF6EC" stroke-width="1.4"/>';
    }).join('');

    var xl = '';
    var step = Math.max(1, Math.ceil(n / 6));
    for (var i = 0; i < n; i += step) {
      var d = store.parseKey(series[i].date);
      xl += '<text x="' + X(i) + '" y="' + (H - 6) + '" text-anchor="middle" font-size="9" fill="#96897A">' +
        (d.getMonth() + 1) + '/' + d.getDate() + '</text>';
    }

    return '<svg viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="xMidYMid meet">' +
      '<defs><linearGradient id="lgArea" x1="0" y1="0" x2="0" y2="1">' +
      '<stop offset="0%" stop-color="#E7AC94" stop-opacity=".34"/>' +
      '<stop offset="100%" stop-color="#E7AC94" stop-opacity="0"/></linearGradient></defs>' +
      grid +
      '<path d="' + smooth(epts) + '" fill="none" stroke="#A8C09A" stroke-width="1.6" ' +
        'stroke-linecap="round" stroke-dasharray="3 4" opacity=".75"/>' +
      '<path d="' + areaD + '" fill="url(#lgArea)"/>' +
      '<path d="' + lineD + '" fill="none" stroke="#D18C71" stroke-width="2.1" stroke-linecap="round"/>' +
      dots + xl +
      '</svg>';
  }

  function quadrantChart(series) {
    var W = 320, H = 280, PL = 34, PR = 16, PT = 16, PB = 32;
    var iw = W - PL - PR, ih = H - PT - PB;
    function X(v) { return PL + ((v - 1) / 4) * iw; }
    function Y(v) { return PT + (1 - (v - 1) / 4) * ih; }

    var dots = series.map(function (e, i) {
      var col = PLANT.COLORS[e.valence] ? PLANT.COLORS[e.valence].petal : '#C9BFA0';
      return '<circle cx="' + X(e.valence + ((i % 5) - 2) * 0.055) + '" cy="' + Y(e.energy + ((i % 3) - 1) * 0.06) +
        '" r="4.2" fill="' + col + '" fill-opacity=".82" stroke="#FBF6EC" stroke-width="1.1"/>';
    }).join('');

    var quadLabels =
      '<text x="' + (PL + iw * 0.24) + '" y="' + (PT + ih * 0.16) + '" font-size="9.5" fill="#96897A" text-anchor="middle">有劲，但不开心</text>' +
      '<text x="' + (PL + iw * 0.76) + '" y="' + (PT + ih * 0.16) + '" font-size="9.5" fill="#96897A" text-anchor="middle">又开心又有劲</text>' +
      '<text x="' + (PL + iw * 0.24) + '" y="' + (PT + ih * 0.94) + '" font-size="9.5" fill="#96897A" text-anchor="middle">低而且没力气</text>' +
      '<text x="' + (PL + iw * 0.76) + '" y="' + (PT + ih * 0.94) + '" font-size="9.5" fill="#96897A" text-anchor="middle">开心，但很累</text>';

    return '<svg viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="xMidYMid meet">' +
      '<rect x="' + PL + '" y="' + PT + '" width="' + iw + '" height="' + ih + '" rx="10" ' +
        'fill="rgba(255,255,255,.34)" stroke="rgba(139,111,82,.12)"/>' +
      '<line x1="' + X(3) + '" y1="' + PT + '" x2="' + X(3) + '" y2="' + (PT + ih) + '" stroke="rgba(139,111,82,.18)" stroke-dasharray="3 4"/>' +
      '<line x1="' + PL + '" y1="' + Y(3) + '" x2="' + (PL + iw) + '" y2="' + Y(3) + '" stroke="rgba(139,111,82,.18)" stroke-dasharray="3 4"/>' +
      quadLabels + dots +
      '<text x="' + (PL + iw / 2) + '" y="' + (H - 8) + '" text-anchor="middle" font-size="10" fill="#6E6353">心情 →</text>' +
      '<text x="12" y="' + (PT + ih / 2) + '" text-anchor="middle" font-size="10" fill="#6E6353" ' +
        'transform="rotate(-90 12 ' + (PT + ih / 2) + ')">↑ 力气</text>' +
      '</svg>';
  }

  function weekdayChart(arr) {
    var W = 420, H = 150, PL = 26, PR = 10, PT = 12, PB = 24;
    var names = ['日', '一', '二', '三', '四', '五', '六'];
    var iw = W - PL - PR, ih = H - PT - PB;
    var bw = iw / 7 * 0.52;
    var bars = '', labels = '';
    for (var i = 0; i < 7; i++) {
      var cx = PL + (iw / 7) * (i + 0.5);
      var v = arr[i];
      labels += '<text x="' + cx + '" y="' + (H - 8) + '" text-anchor="middle" font-size="10" fill="#96897A">' + names[i] + '</text>';
      if (v == null) {
        labels += '<text x="' + cx + '" y="' + (PT + ih - 4) + '" text-anchor="middle" font-size="9" fill="rgba(150,137,122,.5)">—</text>';
        continue;
      }
      var h = ((v - 1) / 4) * ih;
      var y = PT + ih - h;
      var col = PLANT.COLORS[Math.round(v)] ? PLANT.COLORS[Math.round(v)].petal : '#C9BFA0';
      bars += '<rect x="' + (cx - bw / 2) + '" y="' + y + '" width="' + bw + '" height="' + Math.max(3, h) +
        '" rx="' + (bw / 2) + '" fill="' + col + '" opacity=".9"/>';
      bars += '<text x="' + cx + '" y="' + (y - 5) + '" text-anchor="middle" font-size="9.5" fill="#6E6353">' + v + '</text>';
    }
    return '<svg viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="xMidYMid meet">' +
      '<line x1="' + PL + '" x2="' + (W - PR) + '" y1="' + (PT + ih) + '" y2="' + (PT + ih) +
      '" stroke="rgba(139,111,82,.16)"/>' + bars + labels + '</svg>';
  }

  function monthChart(months) {
    var W = 620, H = 170, PL = 26, PR = 10, PT = 16, PB = 30;
    var iw = W - PL - PR, ih = H - PT - PB;
    var n = months.length;
    var bw = Math.min(30, (iw / n) * 0.5);
    var bars = '', labels = '', marks = '';

    months.forEach(function (m, i) {
      var cx = PL + (iw / n) * (i + 0.5);
      labels += '<text x="' + cx + '" y="' + (H - 8) + '" text-anchor="middle" font-size="9" fill="#96897A">' +
        m.label + '</text>';

      // 跨年那根前面画一条淡虚线，标上新年份
      if (m.newYear) {
        var gx = PL + (iw / n) * i;
        marks += '<line x1="' + gx + '" y1="' + PT + '" x2="' + gx + '" y2="' + (PT + ih) +
          '" stroke="rgba(139,111,82,.14)" stroke-dasharray="3 4"/>' +
          '<text x="' + (gx + 4) + '" y="' + (PT - 5) + '" font-size="8.5" fill="#96897A">' + m.year + '</text>';
      }

      // 没记的月份：一条很淡的短横。不能画成矮柱子 —— 那会被读成"1 分"
      if (m.avg == null) {
        bars += '<rect x="' + (cx - bw / 2) + '" y="' + (PT + ih - 3) + '" width="' + bw +
          '" height="3" rx="1.5" fill="rgba(150,137,122,.20)"/>';
        return;
      }

      var h = ((m.avg - 1) / 4) * ih;
      var y = PT + ih - h;
      var col = PLANT.COLORS[Math.round(m.avg)] ? PLANT.COLORS[Math.round(m.avg)].petal : '#C9BFA0';
      bars += '<rect x="' + (cx - bw / 2) + '" y="' + y + '" width="' + bw + '" height="' + Math.max(3, h) +
        '" rx="' + (bw / 2) + '" fill="' + col + '" opacity=".9">' +
        '<title>' + m.label + ' · ' + m.n + ' 天，平均 ' + m.avg + '</title></rect>';
      bars += '<text x="' + cx + '" y="' + (y - 5) + '" text-anchor="middle" font-size="9" fill="#6E6353">' +
        m.avg + '</text>';
    });

    return '<svg viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="xMidYMid meet">' +
      '<line x1="' + PL + '" x2="' + (W - PR) + '" y1="' + (PT + ih) + '" y2="' + (PT + ih) +
      '" stroke="rgba(139,111,82,.16)"/>' + marks + bars + labels + '</svg>';
  }

  /* ==========================================================
     4. 公告板（日历）
     ========================================================== */
  var calState = { y: null, m: null, day: null };

  function renderCalendar(root) {
    if (calState.y === null) {
      // 默认停在最近一次记录所在的月份，不要让人一进来就看到空月
      var all = store.all();
      if (all.length) {
        var lastD = store.parseKey(all[all.length - 1].date);
        calState.y = lastD.getFullYear();
        calState.m = lastD.getMonth();
      } else {
        var now0 = new Date();
        calState.y = now0.getFullYear();
        calState.m = now0.getMonth();
      }
    }
    var y = calState.y, m = calState.m;
    var first = new Date(y, m, 1);
    var startDow = first.getDay();
    var daysIn = new Date(y, m + 1, 0).getDate();
    var todayKey = store.todayKey();

    var cells = '';
    for (var i = 0; i < startDow; i++) cells += '<div class="cal-cell blank"></div>';

    for (var d = 1; d <= daysIn; d++) {
      var k = y + '-' + String(m + 1).padStart(2, '0') + '-' + String(d).padStart(2, '0');
      var e = store.get(k);
      var cls = 'cal-cell';
      var bg = '';
      if (e) {
        cls += ' has';
        var col = PLANT.COLORS[e.valence] ? PLANT.COLORS[e.valence].petal : '#C9BFA0';
        bg = ' style="background:' + col + ';opacity:.88"';
      }
      if (k === todayKey) cls += ' today';
      cells += '<div class="' + cls + '" data-k="' + k + '"' + bg + '>' + d +
        (e && e.note ? '<span class="dot"></span>' : '') + '</div>';
    }

    var detail = '';
    if (calState.day) {
      var de = store.get(calState.day);
      var dd = store.parseKey(calState.day);
      if (de) {
        detail =
          '<div class="cal-detail">' +
            '<h4>' + (dd.getMonth() + 1) + '月' + dd.getDate() + '日</h4>' +
            '<p>心情 ' + de.valence + '／5（' + MOOD_WORDS[de.valence - 1] + '）　' +
              '力气 ' + de.energy + '／5（' + ENERGY_WORDS[de.energy - 1] + '）</p>' +
            (de.note ? '<p>' + esc(de.note) + '</p>' : '<p style="color:#96897A">那天没有留话。</p>') +
            (de.tags && de.tags.length ? '<div class="tag-row">' +
              de.tags.map(function (t) { return '<span>' + esc(t) + '</span>'; }).join('') + '</div>' : '') +
          '</div>';
      } else {
        detail = '<div class="cal-detail"><h4>' + (dd.getMonth() + 1) + '月' + dd.getDate() + '日</h4>' +
          '<p style="color:#96897A">这天岛上什么都没发生。</p></div>';
      }
    }

    var count = store.between(
      y + '-' + String(m + 1).padStart(2, '0') + '-01',
      y + '-' + String(m + 1).padStart(2, '0') + '-31'
    ).length;

    root.innerHTML =
      '<h1 class="page-title">公告板</h1>' +
      '<p class="page-sub">这个月记了 ' + count + ' 天。点任意一天看看那天写了什么。</p>' +
      '<div class="cal-head">' +
        '<div class="cal-month">' + y + ' 年 ' + (m + 1) + ' 月</div>' +
        '<div class="cal-nav">' +
          '<button class="icon-btn" data-mv="-1" style="width:30px;height:30px">‹</button>' +
          '<button class="icon-btn" data-mv="1" style="width:30px;height:30px">›</button>' +
        '</div>' +
      '</div>' +
      '<div class="cal-grid">' +
        ['日', '一', '二', '三', '四', '五', '六'].map(function (n) {
          return '<div class="cal-dow">' + n + '</div>';
        }).join('') + cells +
      '</div>' +
      detail;

    $$('[data-mv]', root).forEach(function (b) {
      b.addEventListener('click', function () {
        calState.m += +b.dataset.mv;
        if (calState.m < 0) { calState.m = 11; calState.y--; }
        if (calState.m > 11) { calState.m = 0; calState.y++; }
        calState.day = null;
        renderCalendar(root);
      });
    });

    $$('.cal-cell.has', root).forEach(function (c) {
      c.addEventListener('click', function () {
        calState.day = c.dataset.k;
        renderCalendar(root);
      });
    });
  }

  /* ==========================================================
     5. 小木屋（设置）
     ========================================================== */
  function renderCabin(root) {
    var s = store.settings();
    var total = store.all().length;

    root.innerHTML =
      '<h1 class="page-title">小木屋</h1>' +
      '<p class="page-sub">东西都存在这台设备上，不上传。共 ' + total + ' 条记录。</p>' +

      '<div class="set-list">' +
        '<div class="set-row">' +
          '<div><div class="set-label">天气跟着心情走</div>' +
            '<div class="set-desc">今天没记录是晴天，心情低会下雨，晚上是夜。</div></div>' +
          '<button class="switch' + (s.weather === 'auto' ? ' on' : '') + '" data-k="weather" data-t="auto"></button>' +
        '</div>' +

        '<div class="set-row">' +
          '<div><div class="set-label">岛上会动</div>' +
            '<div class="set-desc">关掉之后，狐狸不动，植物也不摇。</div></div>' +
          '<button class="switch' + (s.motion ? ' on' : '') + '" data-k="motion"></button>' +
        '</div>' +

        '<div class="set-row">' +
          '<div><div class="set-label">有点声音</div>' +
            '<div class="set-desc">走路、下雨、记完一天的一点轻声。默认是关的。</div></div>' +
          '<button class="switch' + (s.sound ? ' on' : '') + '" data-k="sound"></button>' +
        '</div>' +

        '<div class="set-row">' +
          '<div><div class="set-label">岛民</div>' +
            '<div class="set-desc">现在住着的是小狐狸。</div></div>' +
          '<div class="animal-pick">' +
            '<button class="on" title="小狐狸"><img src="assets/animals/watercolor/sprites/fox-idle-t.png" alt=""></button>' +
          '</div>' +
        '</div>' +
      '</div>' +

      '<div class="rule"></div>' +

      '<div class="set-list">' +
        '<div class="set-row">' +
          '<div><div class="set-label">把数据带走</div>' +
            '<div class="set-desc">导出成 CSV 表格，Excel 里能直接打开。</div></div>' +
          '<button class="btn-ghost" id="btnExport">导出 CSV</button>' +
        '</div>' +
        '<div class="set-row">' +
          '<div><div class="set-label">导回来</div>' +
            '<div class="set-desc">CSV 或 JSON 都行，会合并现有记录，同一天以文件里的为准。</div></div>' +
          '<button class="btn-ghost" id="btnImport">选择文件</button>' +
          '<input type="file" id="fileInput" accept=".csv,.json,text/csv,application/json" hidden>' +
        '</div>' +
      '</div>' +

      '<div class="rule"></div>' +

      '<div class="set-list">' +
        '<div class="set-row">' +
          '<div><div class="set-label">先看看长什么样</div>' +
            '<div class="set-desc">填 29 天示例记录（不含今天），看完可以一键清掉。</div></div>' +
          '<button class="btn-ghost" id="btnDemo">填入示例</button>' +
        '</div>' +
        '<div class="set-row danger-zone">' +
          '<div><div class="set-label">清空所有记录</div>' +
            '<div class="set-desc">这一步不能撤回。设置会保留。</div></div>' +
          '<button class="btn-danger" id="btnWipe">清空</button>' +
        '</div>' +
      '</div>' +

      '<div class="rule"></div>' +
      '<p class="page-sub" style="margin:0;font-size:11.5px;line-height:2;color:#96897A">' +
        '这里是记录和陪伴，不是诊断工具。如果你正处在很难的时候，全国心理援助热线 12356，24 小时有人接。' +
      '</p>';

    function toggle(el, key, getVal) {
      el.addEventListener('click', function () {
        var next = !el.classList.contains('on');
        el.classList.toggle('on', next);
        store.set(key, getVal ? getVal(next) : next);
        App.app.applySettings();
      });
    }

    var wBtn = $('[data-k="weather"]', root);
    toggle(wBtn, 'weather', function (on) { return on ? 'auto' : 'sunny'; });

    var mBtn = $('[data-k="motion"]', root);
    toggle(mBtn, 'motion');

    var sBtn = $('[data-k="sound"]', root);
    toggle(sBtn, 'sound');

    $('#btnExport', root).addEventListener('click', function () {
      var all = store.all();
      if (!all.length) { App.app.toast('还没有记录可以导出'); return; }
      var blob = new Blob([entriesToCsv(all)], { type: 'text/csv;charset=utf-8' });
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = '心屿-' + store.todayKey() + '.csv';
      a.click();
      setTimeout(function () { URL.revokeObjectURL(a.href); }, 2000);
      App.app.toast('表格存好了，' + all.length + ' 天的记录');
    });

    var fi = $('#fileInput', root);
    $('#btnImport', root).addEventListener('click', function () { fi.click(); });
    fi.addEventListener('change', function () {
      var f = fi.files && fi.files[0];
      if (!f) return;
      var fr = new FileReader();
      fr.onload = function () {
        try {
          var text = String(fr.result);
          var list = [];

          if (/^\s*[\{\[]/.test(text)) {
            // 老版本导出的 JSON，还得认
            var data = JSON.parse(text);
            if (!data.entries || !Array.isArray(data.entries)) throw new Error('格式不对');
            list = data.entries.filter(function (e) { return e.date && e.valence; })
              .map(function (e) {
                return { date: e.date, valence: e.valence, energy: e.energy || 3, tags: e.tags || [], note: e.note || '' };
              });
          } else {
            list = csvToEntries(text);
          }

          if (!list.length) throw new Error('没有可导入的行');
          list.forEach(function (e) { store.save(e); });
          App.app.toast('导入了 ' + list.length + ' 条');
          renderCabin(root);
        } catch (err) {
          App.app.toast('这个文件读不了');
        }
      };
      fr.readAsText(f);
    });

    $('#btnDemo', root).addEventListener('click', function () {
      store.seedDemo();
      App.app.toast('填好了，回岛上看看');
      App.app.applyToday();
      renderCabin(root);
    });

    $('#btnWipe', root).addEventListener('click', function () {
      if (!confirm('清空所有记录？这一步不能撤回。')) return;
      store.wipe();
      App.app.applyToday();
      App.app.toast('清空了');
      renderCabin(root);
    });
  }

  /* ---------- 通用 ---------- */
  function bindNav(root) {
    $$('[data-go]', root).forEach(function (b) {
      b.addEventListener('click', function () { App.app.go(b.dataset.go); });
    });
  }

  global.App = global.App || {};
  global.App.views = {
    record: renderRecord,
    garden: renderGarden,
    analysis: renderAnalysis,
    calendar: renderCalendar,
    cabin: renderCabin,
    bindNav: bindNav,
    esc: esc,
    csvToText: entriesToCsv,
    csvFromText: csvToEntries,
    MOOD_WORDS: MOOD_WORDS,
    ENERGY_WORDS: ENERGY_WORDS
  };
})(window);
