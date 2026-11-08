/* 一条命令跑完整测试：先跑纯逻辑，再起本地服务跑冒烟测试，最后收尾。
   用法：npm run verify
   退出码 0 = 全部通过，1 = 有失败项（方便接 CI）。
*/
const { spawn } = require('child_process');
const path = require('path');
const http = require('http');

const ROOT = path.join(__dirname, '..');
const PORT = process.env.XINYU_PORT || '8778';
const NODE = process.execPath;

function runTest(relPath, extraEnv) {
  return new Promise(function (resolve) {
    const child = spawn(NODE, [path.join(ROOT, relPath)], {
      cwd: ROOT,
      env: Object.assign({}, process.env, extraEnv || {}),
      stdio: 'inherit'
    });
    child.on('exit', function (code) { resolve(code === 0); });
    child.on('error', function (e) {
      console.error('  启动失败：' + e.message);
      resolve(false);
    });
  });
}

function waitForServer(url, tries) {
  return new Promise(function (resolve, reject) {
    let left = tries;
    const tick = function () {
      const req = http.get(url, function (res) {
        res.resume();
        resolve(true);
      });
      req.on('error', function () {
        if (--left <= 0) return reject(new Error('服务在 ' + tries + ' 次重试后仍未就绪'));
        setTimeout(tick, 150);
      });
    };
    tick();
  });
}

(async function main() {
  console.log('\n▸ 逻辑测试（不需要浏览器）');
  const logicOk = await runTest('test/logic.test.js');

  console.log('\n▸ 启动本地服务 127.0.0.1:' + PORT);
  const server = spawn(NODE, [path.join(ROOT, 'tools/serve.js'), PORT], {
    cwd: ROOT,
    stdio: ['ignore', 'ignore', 'inherit'],
    env: Object.assign({}, process.env, { XINYU_PORT: PORT })
  });

  let smokeOk = false;
  try {
    await waitForServer('http://127.0.0.1:' + PORT + '/index.html', 40);
    console.log('▸ 冒烟测试（jsdom 走真实交互链）');
    smokeOk = await runTest('test/smoke.test.js', { XINYU_PORT: PORT });
  } catch (e) {
    console.error('  ' + e.message);
  } finally {
    server.kill();
  }

  const allOk = logicOk && smokeOk;
  console.log('\n' + (allOk ? '✓ 全部通过' : '✗ 有失败项'));
  process.exit(allOk ? 0 : 1);
})();
