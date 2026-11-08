/* ===========================================================
   analysis.js —— 情绪分析引擎
   只做描述与推测，不做诊断；所有建议卡必须四段：看到 / 也许 / 试试 / 我在
   理论依据：Russell 效价-唤醒二维模型、情绪粒度、行为激活、CBT 认知重评、自我关怀
   =========================================================== */
(function (global) {
  'use strict';

  var store = global.App.store;

  /* ---------------- 基础统计 ---------------- */
  function mean(a) {
    if (!a.length) return 0;
    var s = 0;
    for (var i = 0; i < a.length; i++) s += a[i];
    return s / a.length;
  }

  function sd(a) {
    if (a.length < 2) return 0;
    var m = mean(a), s = 0;
    for (var i = 0; i < a.length; i++) s += (a[i] - m) * (a[i] - m);
    return Math.sqrt(s / (a.length - 1));
  }

  /** 最小二乘斜率：单位是「每天变化多少分」 */
  function slope(a) {
    var n = a.length;
    if (n < 2) return 0;
    var sx = 0, sy = 0, sxy = 0, sxx = 0;
    for (var i = 0; i < n; i++) {
      sx += i; sy += a[i]; sxy += i * a[i]; sxx += i * i;
    }
    var d = n * sxx - sx * sx;
    if (!d) return 0;
    return (n * sxy - sx * sy) / d;
  }

  function round1(v) { return Math.round(v * 10) / 10; }

  /* ---------------- 指标 ---------------- */
  function buildStats(list) {
    var vals = list.map(function (e) { return e.valence; });
    var engs = list.map(function (e) { return e.energy; });
    var n = list.length;
    if (!n) {
      return {
        n: 0, avgValence: 0, avgEnergy: 0, amplitude: 0, sdValence: 0,
        slope: 0, lowDays: 0, highDays: 0, divergence: 0, coverage: 0
      };
    }
    return {
      n: n,
      avgValence: round1(mean(vals)),
      avgEnergy: round1(mean(engs)),
      amplitude: Math.max.apply(null, vals) - Math.min.apply(null, vals),
      sdValence: round1(sd(vals)),
      slope: slope(vals),                                   // 每天变化
      lowDays: vals.filter(function (v) { return v <= 2; }).length,
      highDays: vals.filter(function (v) { return v >= 4; }).length,
      divergence: list.filter(function (e) {
        return e.energy <= 2 && e.valence >= 4;             // 说自己还好，但人已经没电
      }).length
    };
  }

  /** 从最近一天往前数，连续 <=2 的天数 */
  function consecutiveLow(list) {
    var arr = list.slice().sort(function (a, b) { return a.date < b.date ? 1 : -1; });
    var n = 0, expect = null;
    for (var i = 0; i < arr.length; i++) {
      var e = arr[i];
      if (e.valence > 2) break;
      if (expect === null) expect = e.date;
      else if (store.diffDays(e.date, expect) !== 1) break;   // 中间断了一天就停
      n++;
      expect = e.date;
    }
    return n;
  }

  /** 星期几最容易低 */
  function weekdayAvg(list) {
    var buckets = [[], [], [], [], [], [], []];
    list.forEach(function (e) {
      var d = store.parseKey(e.date);
      buckets[d.getDay()].push(e.valence);
    });
    return buckets.map(function (b) { return b.length ? round1(mean(b)) : null; });
  }

  /** 最近 n 个自然月的月份键（含本月，从旧到新）。12 个月正好是"这一年"的骨架 */
  function monthKeys(n) {
    var now = new Date();
    var keys = [];
    for (var i = n - 1; i >= 0; i--) {
      keys.push(store.keyOf(new Date(now.getFullYear(), now.getMonth() - i, 1)).slice(0, 7));
    }
    return keys;
  }

  /** 按月聚合（年视图用）。固定 12 个骨架，没记的月份 avg=null，不能省掉 ——
      省掉的话「2 月和 11 月」会画成两根挨着的柱子，月份就骗人了 */
  function byMonth(list, keys) {
    var map = {};
    keys.forEach(function (k) { map[k] = []; });
    list.forEach(function (e) {
      var k = e.date.slice(0, 7);
      if (map[k]) map[k].push(e.valence);
    });
    return keys.map(function (k, i) {
      var arr = map[k];
      return {
        key: k,
        label: (+k.slice(5)) + '月',
        year: k.slice(0, 4),
        newYear: i > 0 && k.slice(0, 4) !== keys[i - 1].slice(0, 4),
        avg: arr.length ? round1(mean(arr)) : null,
        n: arr.length
      };
    });
  }

  /** 这一周的周一 */
  function weekStartKey(d) {
    var c = new Date(d.getFullYear(), d.getMonth(), d.getDate());
    c.setDate(c.getDate() - ((c.getDay() + 6) % 7));
    return store.keyOf(c);
  }

  /** 按周聚合。年视图直接按天画 365 个点会糊成一片，按周平均刚好 52 个 */
  function byWeek(list) {
    var map = {}, order = [];
    list.forEach(function (e) {
      var k = weekStartKey(store.parseKey(e.date));
      if (!map[k]) { map[k] = { date: k, v: [], en: [] }; order.push(k); }
      map[k].v.push(e.valence);
      map[k].en.push(e.energy);
    });
    return order.sort().map(function (k) {
      var g = map[k];
      return { date: k, valence: round1(mean(g.v)), energy: round1(mean(g.en)), n: g.v.length };
    });
  }

  /* ---------------- 风险表达检测（只用于决定要不要放一张关怀卡） ---------------- */
  var RISK_WORDS = [
    '不想活', '活不下去', '活着没意思', '活着没有意思', '想消失', '消失掉',
    '结束自己', '自杀', '了结', '撑不下去', '撑不住', '没有意义',
    '没人需要我', '不如死了', '解脱'
  ];

  function hasRiskWords(list) {
    var recent = list.slice(-10);
    for (var i = 0; i < recent.length; i++) {
      var txt = (recent[i].note || '');
      for (var j = 0; j < RISK_WORDS.length; j++) {
        if (txt.indexOf(RISK_WORDS[j]) >= 0) return true;
      }
    }
    return false;
  }

  /* ---------------- 建议卡文案库 ---------------- */
  /* 每一张都是四段式，总长控制在 120 字内；语气规则：不诊断、不命令、不夸奖努力 */
  var LIB = {
    volatile: function (s) {
      var lo = Math.max(1, Math.round(s.avgValence - s.amplitude / 2));
      var hi = Math.min(5, Math.round(s.avgValence + s.amplitude / 2));
      return {
        kind: 'volatile',
        seen: '这段时间你的分在 ' + lo + ' 到 ' + hi + ' 之间来回，起伏比平常密一些。',
        maybe: '不是你不够稳，是这段时间本身事情就很密。',
        tryIt: '今晚睡前把明天最要紧的一件事写下来，只写一件。',
        here: '晃得厉害的时候不用每次都稳住，晃一晃也算过。'
      };
    },
    sustainedLow: function (s, extra) {
      return {
        kind: 'low',
        seen: '最近 14 天里，有 ' + extra.low14 + ' 天你给的分数在 2 分以下。',
        maybe: '这更像是电量一直没充满，不是你想不开。',
        tryIt: '现在去倒一杯水，慢慢喝完。就这一件。',
        here: '不用今天就变好，我在这儿待着。'
      };
    },
    declining: function (s) {
      return {
        kind: 'low',
        seen: '这 ' + s.n + ' 天里，你的分在一点点往下走。',
        maybe: '有些消耗是慢慢攒起来的，自己不太察觉得到。',
        tryIt: '找一件能比昨天早睡 20 分钟的办法，别的先不动。',
        here: '往下走一段也没关系，坡底也有路。'
      };
    },
    divergent: function (s) {
      return {
        kind: 'low',
        seen: '有 ' + s.divergence + ' 天，你心情写得不低，精力却写得很低。',
        maybe: '有时候人是先累垮，情绪还没来得及反应。',
        tryIt: '今天给自己留 10 分钟什么都不做，这不算浪费。',
        here: '说「还好」也没错，累了就是累了。'
      };
    },
    recovering: function (s, extra) {
      return {
        kind: 'calm',
        seen: '前几天低，最近几天回到了 ' + extra.recent3 + ' 分上下。',
        maybe: '往回走通常比掉下去慢，这很正常。',
        tryIt: '把今天让你好一点的那件小事记下来，以后能翻到。',
        here: '走回来这段，是你自己走回来的。'
      };
    },
    steady: function (s) {
      return {
        kind: 'calm',
        seen: '这段时间你的分大多落在 ' + s.avgValence + ' 分上下，起落不大。',
        maybe: '平稳也是一种好状态，不一定非要发生点什么。',
        tryIt: '翻一翻花园里最早的那几株，看看那时候的自己。',
        here: '没什么事的时候，也可以来坐坐。'
      };
    }
  };

  function joinCard(c) {
    return [c.seen, c.maybe, c.tryIt, c.here];
  }

  /* ---------------- 主入口 ---------------- */
  function report(range) {
    range = range || 'week';

    /* 口径 ——
       周：最近 7 天（含今天）
       月：最近 30 天
       年：最近 12 个自然月，从 11 个月前的 1 号到今天。
           不能用 365 天：365 天会横跨 13 个自然月，年表里会出现两个 11 月 */
    var now = new Date();
    var fromKey, days, mkeys = null;

    if (range === 'year') {
      var first = new Date(now.getFullYear(), now.getMonth() - 11, 1);
      fromKey = store.keyOf(first);
      days = Math.round((new Date(now.getFullYear(), now.getMonth(), now.getDate()) - first) / 86400000) + 1;
      mkeys = monthKeys(12);
    } else {
      days = range === 'month' ? 30 : 7;
      fromKey = store.keyOf(store.daysAgo(days - 1));
    }
    var toKey = store.keyOf(now);
    var span = range === 'year' ? '近 12 个月' : '近 ' + days + ' 天';

    var list = store.between(fromKey, toKey);
    var stats = buildStats(list);

    // 风险判定始终看最近 14 天，不受区间影响
    var recent14 = store.recent(14);
    var low14 = recent14.filter(function (e) { return e.valence <= 2; }).length;
    var consLow = consecutiveLow(store.recent(30));
    var risk = hasRiskWords(store.recent(30));

    var last3 = list.slice(-3);
    var recent3 = last3.length ? round1(mean(last3.map(function (e) { return e.valence; }))) : 0;
    var prev3 = list.slice(-6, -3);
    var prev3avg = prev3.length ? round1(mean(prev3.map(function (e) { return e.valence; }))) : null;

    var level = 0;
    var cards = [];
    var care = null;   // 'gentle' | 'strong'

    if (stats.n < 4) {
      level = 0;
    } else {
      // ---- 分级 ----
      if (risk && consLow >= 8) {
        level = 4;
        care = 'strong';
      } else if (consLow >= 5 || (recent14.length >= 7 && low14 / recent14.length >= 0.6)) {
        level = 3;
        care = risk ? 'strong' : 'gentle';
      } else if (stats.sdValence >= 1.05 || stats.amplitude >= 3 ||
                 stats.slope <= -0.09 || stats.divergence >= 3) {
        level = 2;
        if (risk) care = 'gentle';
      } else {
        level = 1;
        if (risk) care = 'gentle';
      }

      // ---- 选卡：一次只给一张，不堆叠 ----
      if (level >= 3) {
        cards.push(LIB.sustainedLow(stats, { low14: low14 }));
      } else if (level === 2) {
        if (stats.slope <= -0.09) cards.push(LIB.declining(stats));
        else if (stats.divergence >= 2 && stats.sdValence < 1.15) cards.push(LIB.divergent(stats));
        else cards.push(LIB.volatile(stats));
      } else {
        // L1：只在明显回升或平稳时给一张轻的，其余不给
        if (prev3avg !== null && recent3 - prev3avg >= 1 && prev3avg <= 2.5) {
          cards.push(LIB.recovering(stats, { recent3: recent3 }));
        } else if (range !== 'week') {
          cards.push(LIB.steady(stats));
        }
      }
    }

    // 图表：周/月用日粒度（最近 30 天，避免周视图太空），年视图按周聚合
    var chartList = range === 'year' ? byWeek(list) : store.recent(30);

    return {
      range: range,
      from: fromKey,
      to: toKey,
      days: days,
      span: span,
      n: stats.n,
      stats: stats,
      level: level,
      cards: cards,
      care: care,
      low14: low14,
      consLow: consLow,
      series: chartList,
      weekday: weekdayAvg(list),
      months: mkeys ? byMonth(list, mkeys) : []
    };
  }

  global.App = global.App || {};
  global.App.analysis = {
    report: report,
    joinCard: joinCard,
    mean: mean,
    sd: sd,
    slope: slope,
    round1: round1,
    consecutiveLow: consecutiveLow
  };
})(window);
