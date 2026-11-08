/* ===========================================================
   sound.js —— 声音
   全部用 WebAudio 现场合成，不加载任何音频文件：
   一来省体积（assets 已经够重了），二来这几个声音本来就简单得很。
   默认是关的，只有在小木屋里打开才开始响；浏览器要求有用户手势才能出声，
   所以 AudioContext 是懒创建的，第一次触发时才建。

   声音清单：
     chime  记完一天的那一下，两个音，短的
     tick   点物件/翻页的轻响
     step   狐狸走路，很低很轻，几乎只是气声
     rain   雨天的环境底噪，循环，淡入淡出
   =========================================================== */
(function (global) {
  'use strict';

  var S = {
    ctx: null,
    master: null,
    on: false,
    buf: null,        // 复用的噪声缓冲
    rain: null        // { src, gain }
  };

  function ensure() {
    if (S.ctx) {
      if (S.ctx.state === 'suspended') S.ctx.resume();
      return S.ctx;
    }
    var AC = global.AudioContext || global.webkitAudioContext;
    if (!AC) return null;
    try { S.ctx = new AC(); } catch (e) { return null; }
    S.master = S.ctx.createGain();
    S.master.gain.value = 0.9;
    S.master.connect(S.ctx.destination);
    return S.ctx;
  }

  /* 布朗噪声：比白噪闷，更像远处的水声、脚步和纸的摩擦 */
  function noise(dur) {
    var len = Math.max(1, Math.floor(S.ctx.sampleRate * dur));
    var buf = S.ctx.createBuffer(1, len, S.ctx.sampleRate);
    var d = buf.getChannelData(0);
    var last = 0;
    for (var i = 0; i < len; i++) {
      last = (last + 0.02 * (Math.random() * 2 - 1)) / 1.02;
      d[i] = Math.max(-1, Math.min(1, last * 3.2));
    }
    return buf;
  }

  function buffer() {
    if (!S.buf) S.buf = noise(0.5);
    return S.buf;
  }

  /* 一段很短的气声，filter 决定它是"咔"还是"沙" */
  function puff(type, freq, q, peak, dur, rate) {
    if (!S.on || !ensure()) return;
    var t = S.ctx.currentTime;
    var src = S.ctx.createBufferSource();
    src.buffer = buffer();
    if (rate) src.playbackRate.value = rate;
    var f = S.ctx.createBiquadFilter();
    f.type = type;
    f.frequency.value = freq;
    f.Q.value = q;
    var g = S.ctx.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.linearRampToValueAtTime(peak, t + 0.012);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    src.connect(f); f.connect(g); g.connect(S.master);
    src.start(t); src.stop(t + dur + 0.05);
  }

  function chime() {
    if (!S.on || !ensure()) return;
    var t0 = S.ctx.currentTime + 0.01;
    [523.25, 783.99].forEach(function (f, i) {
      var t = t0 + i * 0.11;
      var o = S.ctx.createOscillator();
      var g = S.ctx.createGain();
      o.type = 'triangle';
      o.frequency.value = f;
      g.gain.setValueAtTime(0.0001, t);
      g.gain.linearRampToValueAtTime(0.09, t + 0.02);
      g.gain.exponentialRampToValueAtTime(0.0008, t + 1.1);
      o.connect(g); g.connect(S.master);
      o.start(t); o.stop(t + 1.2);
    });
  }

  function tick() { puff('bandpass', 1500, 1.2, 0.05, 0.16); }

  function step() { puff('lowpass', 700, 0.7, 0.026, 0.12, 0.8); }

  function rain(on) {
    if (!ensure()) return;
    if (on && S.on) {
      if (S.rain) return;
      var t = S.ctx.currentTime;
      var src = S.ctx.createBufferSource();
      src.buffer = noise(4);
      src.loop = true;
      var hp = S.ctx.createBiquadFilter();
      hp.type = 'highpass'; hp.frequency.value = 280;
      var lp = S.ctx.createBiquadFilter();
      lp.type = 'lowpass'; lp.frequency.value = 1500;
      var g = S.ctx.createGain();
      g.gain.setValueAtTime(0.0001, t);
      g.gain.linearRampToValueAtTime(0.04, t + 2.5);
      src.connect(hp); hp.connect(lp); lp.connect(g); g.connect(S.master);
      src.start(t);
      S.rain = { src: src, gain: g };
    } else if (S.rain) {
      var r = S.rain;
      S.rain = null;
      try {
        var now = S.ctx.currentTime;
        r.gain.gain.cancelScheduledValues(now);
        r.gain.gain.setValueAtTime(r.gain.gain.value || 0.0001, now);
        r.gain.gain.linearRampToValueAtTime(0.0001, now + 1.2);
        r.src.stop(now + 1.4);
      } catch (e) { /* 已经停了就算了 */ }
    }
  }

  function setEnabled(v) {
    S.on = !!v;
    if (!S.on) rain(false);
  }

  global.App = global.App || {};
  global.App.sound = {
    setEnabled: setEnabled,
    isOn: function () { return S.on; },
    chime: chime,
    tick: tick,
    step: step,
    rain: rain
  };
})(window);
