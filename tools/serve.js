/* 零依赖静态服务器。
   预览站点、跑冒烟测试都用它，不用装任何东西。

   用法：
     node tools/serve.js          # 默认 8778 端口
     node tools/serve.js 9000     # 指定端口
     npm run serve

   冒烟测试（test/smoke.test.js）默认也连 8778，两边端口一致才能对上。
*/
const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const PORT = Number(process.argv[2] || process.env.XINYU_PORT || 8778);

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.gif': 'image/gif',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.ttf': 'font/ttf',
  '.mp3': 'audio/mpeg',
  '.csv': 'text/csv; charset=utf-8',
  '.md': 'text/plain; charset=utf-8',
  '.txt': 'text/plain; charset=utf-8',
  '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
};

const server = http.createServer(function (req, res) {
  let urlPath;
  try {
    urlPath = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
  } catch (e) {
    res.writeHead(400, { 'Content-Type': 'text/plain; charset=utf-8' });
    return res.end('Bad Request');
  }

  if (urlPath.endsWith('/')) urlPath += 'index.html';

  // path.normalize 会吃掉 ../，join 之后结果必然落在 ROOT 之内，再兜一道检查
  const file = path.join(ROOT, path.normalize(urlPath));
  if (file !== ROOT && !file.startsWith(ROOT + path.sep)) {
    res.writeHead(403, { 'Content-Type': 'text/plain; charset=utf-8' });
    return res.end('Forbidden');
  }

  fs.stat(file, function (err, st) {
    if (err || !st.isFile()) {
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
      return res.end('Not Found: ' + urlPath);
    }
    res.writeHead(200, {
      'Content-Type': MIME[path.extname(file).toLowerCase()] || 'application/octet-stream',
      'Content-Length': st.size,
      // 开发用，别缓存，改完刷新就能看到
      'Cache-Control': 'no-cache, no-store, must-revalidate'
    });
    fs.createReadStream(file).pipe(res);
  });
});

server.on('error', function (e) {
  if (e.code === 'EADDRINUSE') {
    console.error('端口 ' + PORT + ' 已被占用。换一个：node tools/serve.js 9000');
    process.exit(1);
  }
  throw e;
});

server.listen(PORT, '127.0.0.1', function () {
  console.log('心屿 · 本地服务已启动');
  console.log('  http://127.0.0.1:' + PORT + '/index.html');
  console.log('  Ctrl+C 停止');
});
