/* 真实 DOM 冒烟测试：从本地服务器加载页面，走一遍完整交互链
   运行前需先起静态服务，默认 http://127.0.0.1:8778
   端口可用环境变量覆盖：XINYU_PORT=8791 node test/smoke.test.js
   NODE_PATH=<workspace>/node_modules node test/smoke.test.js
*/
const { JSDOM, VirtualConsole } = require('jsdom');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const PORT = process.env.XINYU_PORT || '8778';
const BASE = 'http://127.0.0.1:' + PORT + '/index.html';
let pass = 0, fail = 0;
function ok(name, cond, extra) {
  if (cond) { pass++; console.log('  ok   ' + name); }
  else { fail++; console.log('  FAIL ' + name + (extra ? '  → ' + extra : '')); }
}
const wait = (ms) => new Promise(r => setTimeout(r, ms));

(async () => {
  const errors = [];
  const vc = new VirtualConsole();
  vc.on('jsdomError', e => errors.push(e.message));
  vc.on('error', (...a) => errors.push(a.join(' ')));

  const dom = await JSDOM.fromURL(BASE, {
    runScripts: 'dangerously',
    resources: 'usable',
    pretendToBeVisual: true,
    virtualConsole: vc
  });
  const { window } = dom;
  const doc = window.document;

  await new Promise(res => {
    if (doc.readyState === 'complete') return res();
    window.addEventListener('load', res);
    setTimeout(res, 4000);
  });
  await wait(300);

  console.log('\n[1] 启动');
  ok('没有脚本错误', errors.length === 0, JSON.stringify(errors).slice(0, 260));
  ok('App 已挂载', !!window.App && !!window.App.app);
  ok('store 可用', !!window.App.store);
  ok('问候语有内容', (doc.querySelector('#greetLine').textContent || '').length > 0);
  ok('天气已设置', !!doc.querySelector('#scene').dataset.weather);

  console.log('\n[2] 首页结构');
  const items = doc.querySelectorAll('.item');
  ok('5 个物件', items.length === 5, 'got ' + items.length);
  // 坐标现在在 main.css 的类里，行内只留 class
  const css = fs.readFileSync(path.join(ROOT, 'styles/main.css'), 'utf8');
  const placed = Array.from(items).every(b => {
    const c = Array.from(b.classList).find(x => /^it-/.test(x));
    return !!c && new RegExp('\\.' + c + '\\s*\\{[^}]*--x:').test(css);
  });
  ok('物件坐标在样式表里', placed);
  ok('植被层存在', doc.querySelectorAll('.d-obj').length >= 4, 'got ' + doc.querySelectorAll('.d-obj').length);
  ok('岛民存在', !!doc.querySelector('#fox'));
  ok('信箱有新记录角标', doc.querySelector('#mailBadge').hidden === false);

  console.log('\n[3] 进入记录页');
  window.location.hash = '#/record';
  await wait(400);
  ok('纸卡打开', doc.querySelector('#sheet').hidden === false);
  const moods = doc.querySelectorAll('.mood-pick');
  ok('五档心情', moods.length === 5, 'got ' + moods.length);
  ok('五档用 sprite', (moods[0].querySelector('img').getAttribute('src') || '').includes('mood-1-t.png'));
  ok('能量五档', doc.querySelectorAll('.energy-dot').length === 5);
  ok('标签分组 3 组', doc.querySelectorAll('.tag-group-name').length === 3);
  ok('未选心情时按钮禁用', doc.querySelector('#saveBtn').disabled === true);

  console.log('\n[4] 完成一次记录');
  moods[3].dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  doc.querySelectorAll('.energy-dot')[2].dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  doc.querySelectorAll('.tag')[0].dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  const note = doc.querySelector('#noteInput');
  note.value = '测试写的一句话';
  note.dispatchEvent(new window.Event('input', { bubbles: true }));
  ok('选后可提交', doc.querySelector('#saveBtn').disabled === false);
  doc.querySelector('#saveBtn').dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  await wait(150);
  ok('出现提交仪式', doc.querySelector('#ritual').hidden === false);
  await wait(2000);
  ok('仪式结束后关闭纸卡', doc.querySelector('#sheet').hidden === true);
  const saved = window.App.store.today();
  ok('已写入今天一条', !!saved, 'today=' + JSON.stringify(saved));
  if (saved) {
    ok('心情为 4', saved.valence === 4, 'got ' + saved.valence);
    ok('精力为 3', saved.energy === 3, 'got ' + saved.energy);
    ok('标签已存', saved.tags.length === 1, JSON.stringify(saved.tags));
    ok('笔记已存', saved.note === '测试写的一句话', saved.note);
    ok('带 user_id', !!saved.user_id);
  }
  ok('角标已消失', doc.querySelector('#mailBadge').hidden === true);
  ok('地址已回到岛上', window.location.hash === '', 'hash=' + window.location.hash);

  console.log('\n[5] 情绪花园');
  window.App.app.go('#/garden');
  await wait(400);
  ok('长出 1 株植物', doc.querySelectorAll('.plant').length === 1, 'got ' + doc.querySelectorAll('.plant').length);
  ok('植物是 svg', !!doc.querySelector('.plant svg'));

  console.log('\n[6] 观测台');
  window.App.app.go('#/analysis?range=week');
  await wait(400);
  const t = doc.querySelector('#sheetBody').textContent;
  ok('显示标题', t.includes('观测台'));
  ok('记录不足时给出提示', t.includes('线还连不起来') || t.includes('还没有可分析的东西'), t.slice(0, 80));

  // 填示例数据后再看
  window.App.store.seedDemo();
  window.App.app.go('#/analysis?range=month');
  await wait(500);
  const body = doc.querySelector('#sheetBody');
  ok('周/月/年切换存在', body.querySelectorAll('#rangeTabs button').length === 3);
  ok('统计卡渲染', body.querySelectorAll('.stat').length === 4);
  ok('曲线图渲染', body.querySelectorAll('svg').length >= 1, 'svg=' + body.querySelectorAll('svg').length);
  ok('没有出现诊断词',
    !/抑郁症|焦虑症|诊断|病情|风险等级/.test(body.textContent),
    '发现疑似诊断词');
  const monthTab = body.querySelector('[data-range="month"]');
  ok('月视图高亮', monthTab && monthTab.className === 'on', monthTab && monthTab.className);

  // 年视图：12 根柱子（含空月份），月份标签不能重复
  window.App.app.go('#/analysis?range=year');
  await wait(500);
  const yBody = doc.querySelector('#sheetBody');
  const mLabels = Array.from(yBody.querySelectorAll('svg text'))
    .map(t => t.textContent).filter(s => /^\d{1,2}月$/.test(s));
  ok('年视图 12 个月份标签', mLabels.length === 12, 'got ' + mLabels.length + ' → ' + mLabels.join(','));
  ok('年视图月份不重复', new Set(mLabels).size === mLabels.length, mLabels.join(','));
  ok('年视图写清了区间', /个月有记录/.test(yBody.textContent));

  console.log('\n[7] 公告板');
  window.App.app.go('#/calendar');
  await wait(400);
  ok('日历渲染 7 列', doc.querySelectorAll('.cal-dow').length === 7);
  ok('有记录的日子可点', doc.querySelectorAll('.cal-cell.has').length >= 2,
    'got ' + doc.querySelectorAll('.cal-cell.has').length);
  const firstHas = doc.querySelector('.cal-cell.has');
  firstHas.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  await wait(200);
  ok('点开某天出现详情', !!doc.querySelector('.cal-detail'));

  console.log('\n[8] 小木屋');
  window.App.app.go('#/cabin');
  await wait(400);
  const cabin = doc.querySelector('#sheetBody');
  ok('开关渲染', cabin.querySelectorAll('.switch').length >= 2);
  ok('导出按钮存在', !!cabin.querySelector('#btnExport'));
  ok('清空按钮存在', !!cabin.querySelector('#btnWipe'));
  ok('有热线说明', cabin.textContent.includes('12356'));

  const sw = cabin.querySelector('.switch');
  const before = sw.className;
  sw.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  await wait(100);
  ok('开关能切换', sw.className !== before, before + ' → ' + sw.className);

  // CSV：表头中文、带 BOM（Excel 打开不乱码）、逗号/换行/引号要转义、能原样读回来
  console.log('\n[8b] 导出 CSV');
  const V = window.App.views;
  const tricky = [{
    date: '2026-11-01', valence: 4, energy: 3, tags: ['平静', '朋友'],
    note: '有点累,但还是笑了\n第二行 "引用"',
    createdAt: new Date(2026, 10, 1, 9, 5, 0).getTime()
  }];
  const csv = V.csvToText(tricky);
  ok('CSV 带 BOM', csv.charCodeAt(0) === 0xFEFF);
  ok('CSV 有中文表头', csv.indexOf('日期,心情,心情描述,力气,力气描述,标签,备注') > 0, csv.slice(1, 40));
  ok('引号包裹含逗号/换行的备注', csv.indexOf('"有点累,但还是笑了') > 0);
  ok('内部引号成对转义', csv.indexOf('""引用""') > 0);
  ok('时间戳是 YYYY-MM-DD HH:mm', csv.indexOf(',2026-11-01 09:05') > 0, csv.split('\r\n')[1]);
  const back = V.csvFromText(csv);
  ok('CSV 能读回来', back.length === 1 && back[0].date === '2026-11-01' && back[0].valence === 4);
  ok('备注原样还原', back[0].note === tricky[0].note, JSON.stringify(back[0].note));
  ok('标签还原', back[0].tags.join('|') === '平静|朋友', back[0].tags.join('|'));
  ok('坏行会被跳过', V.csvFromText('\ufeff日期,心情\n2026-11-02,9\nxxx,3\n2026-11-03,2').length === 1);

  console.log('\n[9] 返回岛上');
  doc.querySelector('#sheetBack').dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  await wait(400);
  ok('纸卡已关闭', doc.querySelector('#sheet').hidden === true);
  ok('没有新的脚本错误', errors.length === 0, JSON.stringify(errors).slice(0, 260));

  // file:// 直开、或预览面板的沙箱 iframe 里，history.pushState / replaceState 会抛
  // SecurityError。以前这两处一旦抛错，"回岛上"就彻底点不动了。
  console.log('\n[10] 地址栏接口抛错时也要能回岛上');
  const realPush = window.history.pushState;
  const realReplace = window.history.replaceState;
  window.history.pushState = function () { throw new Error('SecurityError'); };
  window.history.replaceState = function () { throw new Error('SecurityError'); };
  window.App.app.go('#/cabin');
  await wait(400);
  ok('纸卡能打开', doc.querySelector('#sheet').hidden === false);
  doc.querySelector('#sheetBack').dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  await wait(400);
  ok('pushState 抛错也能关掉', doc.querySelector('#sheet').hidden === true);
  ok('兜底后地址栏已清空', !/^#\/?[a-z]/.test(window.location.hash), window.location.hash);
  window.history.pushState = realPush;
  window.history.replaceState = realReplace;

  // 关场动画（230ms）还没走完就点开另一个物件时，旧定时器不能把新纸卡清掉
  console.log('\n[11] 快速切换物件');
  window.App.app.go('#/cabin');
  await wait(300);
  doc.querySelector('#sheetBack').dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  await wait(60);
  window.App.app.go('#/record');
  await wait(600);
  ok('新纸卡还在', doc.querySelector('#sheet').hidden === false);
  ok('新纸卡有内容', doc.querySelector('#sheetBody').children.length > 0);
  window.App.app.go('#/');
  await wait(400);
  ok('最后仍能回岛上', doc.querySelector('#sheet').hidden === true);
  ok('全程没有脚本错误', errors.length === 0, JSON.stringify(errors).slice(0, 260));

  console.log('\n---------------------------------');
  console.log('通过 ' + pass + ' / 失败 ' + fail);
  dom.window.close();
  process.exit(fail ? 1 : 0);
})().catch(e => {
  console.error('测试崩溃:', e);
  process.exit(1);
});
