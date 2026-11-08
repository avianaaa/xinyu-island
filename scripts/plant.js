/* ===========================================================
   plant.js —— 情绪花园的植物
   一条记录 = 一株植物
   情绪值决定颜色与花形，精力值决定高度与叶片数
   =========================================================== */
(function (global) {
  'use strict';

  // 五档颜色：雾蓝 → 灰绿 → 奶油 → 蜜桃 → 暖橙
  var COLORS = {
    1: { petal: '#9DB3C6', core: '#7E97AD', leaf: '#8FA3A8' },
    2: { petal: '#A9B48F', core: '#8B9A72', leaf: '#93A57E' },
    3: { petal: '#CFC29B', core: '#B5A67C', leaf: '#9DAA8A' },
    4: { petal: '#E7AC94', core: '#D18C71', leaf: '#9DAE8C' },
    5: { petal: '#E08A5C', core: '#C5703F', leaf: '#96A882' }
  };

  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }

  /**
   * @param {object} e  记录 { date, valence, energy }
   * @param {number} i  序号，用来做轻微的不规则
   */
  function plantSVG(e, i) {
    var v = clamp(e.valence || 3, 1, 5);
    var en = clamp(e.energy || 3, 1, 5);
    var c = COLORS[v];
    var seed = (i * 37) % 11;
    var wob = ((seed % 5) - 2) * 0.7;                       // 轻微左右偏，让一片不呆板

    var top = 58 - (20 + en * 6);                            // 茎顶 y
    var baseX = 20 + wob;
    var tipX = baseX + ((seed % 3) - 1) * 2.2;
    var midX = (baseX + tipX) / 2 + ((seed % 4) - 1.5) * 1.4;

    // 茎
    var stem = 'M' + baseX + ' 58 Q' + midX + ' ' + ((58 + top) / 2) + ' ' + tipX + ' ' + top;

    // 叶：精力越高叶片越多
    var leafN = en <= 2 ? 1 : en <= 4 ? 2 : 3;
    var leaves = '';
    for (var k = 0; k < leafN; k++) {
      var t = 0.38 + k * 0.19;
      var ly = 58 - (58 - top) * t;
      var lx = baseX + (midX - baseX) * t;
      var side = k % 2 === 0 ? -1 : 1;
      var len = 7.5 + (seed % 3) * 0.8 - k * 0.6;
      leaves += '<path d="M' + lx + ' ' + ly +
        ' q' + (side * len) + ' ' + (-len * 0.62) + ' ' + (side * len * 1.82) + ' ' + (-len * 0.18) +
        ' q' + (-side * len * 0.72) + ' ' + (len * 0.62) + ' ' + (-side * len * 1.82) + ' ' + (len * 0.18) +
        ' Z" fill="' + c.leaf + '" opacity="' + (0.82 - k * 0.08).toFixed(2) + '"/>';
    }

    // 花头：低分是下垂的花苞，中段是小花，高分开花
    var head = '';
    if (v <= 2) {
      head = '<path d="M' + tipX + ' ' + top +
        ' q3 6 -2 9 q-4 2 -4 -3 q0 -4 6 -6 Z" fill="' + c.petal + '" opacity=".95"/>' +
        '<circle cx="' + (tipX - 1) + '" cy="' + (top + 7) + '" r="1.5" fill="' + c.core + '" opacity=".8"/>';
    } else if (v === 3) {
      head = '<circle cx="' + tipX + '" cy="' + top + '" r="4.2" fill="' + c.petal + '" opacity=".95"/>' +
        '<circle cx="' + tipX + '" cy="' + top + '" r="1.7" fill="' + c.core + '" opacity=".85"/>';
    } else {
      var R = v === 5 ? 6.4 : 5.4;
      var petals = '';
      var cnt = v === 5 ? 6 : 5;
      for (var p = 0; p < cnt; p++) {
        var ang = (Math.PI * 2 / cnt) * p - Math.PI / 2;
        var px = tipX + Math.cos(ang) * R * 0.72;
        var py = top + Math.sin(ang) * R * 0.72;
        petals += '<ellipse cx="' + px.toFixed(1) + '" cy="' + py.toFixed(1) +
          '" rx="' + (R * 0.52).toFixed(1) + '" ry="' + (R * 0.4).toFixed(1) +
          '" fill="' + c.petal + '" opacity=".92" transform="rotate(' +
          (ang * 180 / Math.PI + 90).toFixed(0) + ' ' + px.toFixed(1) + ' ' + py.toFixed(1) + ')"/>';
      }
      head = petals + '<circle cx="' + tipX + '" cy="' + top + '" r="2.2" fill="' + c.core + '"/>';
    }

    return '<svg viewBox="0 0 40 62" aria-hidden="true">' +
      '<ellipse cx="' + baseX + '" cy="58.5" rx="6.5" ry="1.6" fill="#5E6B4C" opacity=".16"/>' +
      '<path d="' + stem + '" stroke="' + c.leaf + '" stroke-width="1.7" fill="none" stroke-linecap="round"/>' +
      leaves + head +
      '</svg>';
  }

  global.App = global.App || {};
  global.App.plant = { svg: plantSVG, COLORS: COLORS };
})(window);
