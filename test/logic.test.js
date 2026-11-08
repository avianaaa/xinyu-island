/* 分析引擎 / 存储层逻辑测试（node test/logic.test.js） */
const path = require('path');

// ---- 环境模拟 ----
global.window = global;
const LS = {};
global.localStorage = {
  getItem(k) { return Object.prototype.hasOwnProperty.call(LS, k) ? LS[k] : null; },
  setItem(k, v) { LS[k] = String(v); },
  removeItem(k) { delete LS[k]; }
};

require(path.join(__dirname, '..', 'scripts/store.js'));
require(path.join(__dirname, '..', 'scripts/analysis.js'));
require(path.join(__dirname, '..', 'scripts/plant.js'));

const store = App.store;
const A = App.analysis;

let pass = 0, fail = 0;
function ok(name, cond, extra) {
  if (cond) { pass++; console.log('  ok   ' + name); }
  else { fail++; console.log('  FAIL ' + name + (extra ? '  → ' + extra : '')); }
}
function reset() { store.wipe(); }

function put(daysAgo, valence, energy, note, tags) {
  const d = store.daysAgo(daysAgo);
  store.save({ date: store.keyOf(d), valence, energy, note: note || '', tags: tags || [] });
}

console.log('\n[1] 空数据');
reset();
let r = A.report('week');
ok('无记录时 level = 0', r.level === 0, 'got ' + r.level);
ok('无记录时不出卡', r.cards.length === 0);

console.log('\n[2] 平稳 7 天');
reset();
for (let i = 0; i < 7; i++) put(i, 3, 3);
r = A.report('week');
ok('平稳 → level 1', r.level === 1, 'got ' + r.level);
ok('周视图平稳不出卡', r.cards.length === 0, 'got ' + r.cards.length);
ok('平均心情 3', r.stats.avgValence === 3, 'got ' + r.stats.avgValence);

console.log('\n[3] 波动大');
reset();
[1, 5, 2, 4, 1, 5, 3].forEach((v, i) => put(i, v, 3));
r = A.report('week');
ok('振幅 4 → level 2', r.level === 2, 'got ' + r.level + ' amp=' + r.stats.amplitude);
ok('给出建议卡', r.cards.length === 1, 'got ' + r.cards.length);
ok('卡有四个字段', r.cards[0] && !!r.cards[0].seen && !!r.cards[0].maybe && !!r.cards[0].tryIt && !!r.cards[0].here);
const len = A.joinCard(r.cards[0]).join('').length;
ok('文案 ≤ 120 字 (' + len + ')', len <= 120, len);

console.log('\n[4] 持续低落 6 天');
reset();
for (let i = 0; i < 6; i++) put(i, 1, 2);
r = A.report('month');
ok('连续低落 6 天 → level 3', r.level === 3, 'got ' + r.level + ' cons=' + r.consLow);
ok('care = gentle', r.care === 'gentle', 'got ' + r.care);

console.log('\n[5] 持续低落 + 风险表达');
reset();
for (let i = 0; i < 10; i++) put(i, 1, 1, i === 3 ? '真的不想活了' : '');
r = A.report('month');
ok('→ level 4', r.level === 4, 'got ' + r.level);
ok('care = strong', r.care === 'strong', 'got ' + r.care);

console.log('\n[6] 单次风险表达但状态平稳');
reset();
for (let i = 0; i < 10; i++) put(i, 3, 3, i === 5 ? '累到不想活了' : '');
r = A.report('month');
ok('不判 L4', r.level < 4, 'got ' + r.level);
ok('仍给关怀', r.care === 'gentle', 'got ' + r.care);

console.log('\n[7] 精力情绪背离');
reset();
[3, 3, 3, 3, 3, 3].forEach((v, i) => put(i, 4, 1));
r = A.report('week');
ok('背离计数 ≥ 2', r.stats.divergence >= 2, 'got ' + r.stats.divergence);
ok('背离 → level 2', r.level === 2, 'got ' + r.level);

console.log('\n[8] 下滑趋势');
reset();
[5, 5, 4, 4, 3, 3, 2, 2].forEach((v, i) => put(7 - i, v, 3));
r = A.report('month');
ok('斜率为负', r.stats.slope < 0, 'slope=' + r.stats.slope.toFixed(3));
ok('→ level 2', r.level === 2, 'got ' + r.level);

console.log('\n[9] 连续天数与中断');
reset();
put(0, 3, 3); put(1, 3, 3); put(3, 3, 3);
ok('streak = 2（中间断了一天）', store.streak() === 2, 'got ' + store.streak());

console.log('\n[10] 一天一条');
reset();
put(0, 1, 1); put(0, 5, 5);
ok('同一天覆盖不新增', store.all().length === 1, 'got ' + store.all().length);
ok('保留最后一次', store.all()[0].valence === 5);
ok('带 user_id', !!store.all()[0].user_id);

console.log('\n[11] 示例数据');
reset();
store.seedDemo();
const demo = store.all();
ok('填入 29 天', demo.length === 29, 'got ' + demo.length);
ok('不含今天', !store.hasToday());
r = A.report('month');
ok('示例能产出报告', r.n > 10, 'n=' + r.n);
ok('示例有图数据', r.series.length > 10, 'series=' + r.series.length);

console.log('\n[12] 植物 SVG');
const svg = App.plant.svg({ valence: 5, energy: 5 }, 0);
ok('生成 svg', svg.indexOf('<svg') === 0);
ok('含花头', svg.indexOf('<ellipse') > 0);
const svg1 = App.plant.svg({ valence: 1, energy: 1 }, 3);
ok('低分是花苞不是花', svg1.indexOf('<circle') > 0);

console.log('\n[13] 年份视图');
reset();
store.seedDemo();
r = A.report('year');
ok('年视图有月份聚合', r.months.length >= 1, 'got ' + r.months.length);
ok('年视图不报错', typeof r.stats.avgValence === 'number');

// 一年必须是 12 个自然月固定骨架：365 天会横跨 13 个月，出现两个 11 月
ok('年视图固定 12 格', r.months.length === 12, 'got ' + r.months.length);
ok('月份键连续且不重复', (function () {
  var ks = r.months.map(function (m) { return m.key; });
  if (new Set(ks).size !== 12) return false;
  for (var i = 1; i < ks.length; i++) {
    var a = ks[i - 1].split('-').map(Number), b = ks[i].split('-').map(Number);
    var idx = function (y, m) { return y * 12 + (m - 1); };
    if (idx(b[0], b[1]) - idx(a[0], a[1]) !== 1) return false;
  }
  return true;
})(), r.months.map(function (m) { return m.key; }).join(','));
ok('最后一个月份是本月', r.months[11].key === store.todayKey().slice(0, 7));
ok('没记的月份留空 avg=null', r.months.some(function (m) { return m.avg === null; }));
ok('年视图曲线按周聚合', r.series.length <= 54 && r.series.length > 0, 'series=' + r.series.length);
ok('周粒度有 valence/energy', r.series.every(function (s) {
  return typeof s.valence === 'number' && typeof s.energy === 'number' && /^\d{4}-\d{2}-\d{2}$/.test(s.date);
}));
ok('年视图口径写清楚了', r.span === '近 12 个月', r.span);
ok('月视图不带月份表', A.report('month').months.length === 0);

console.log('\n---------------------------------');
console.log('通过 ' + pass + ' / 失败 ' + fail);
process.exit(fail ? 1 : 0);
