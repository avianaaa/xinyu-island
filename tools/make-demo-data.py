# -*- coding: utf-8 -*-
"""
make-demo-data.py —— 从合成数据生成站点的演示数据

为什么不是直接把 CSV 丢进 dist：
    演示数据必须"永远新鲜"。如果写死真实日期，过两周打开就只剩半张空图。
    所以这里只存「距今天多少天」，由 store.js 在运行时换算成真实日期。

为什么最后一条是「昨天」而不是「今天」：
    今天空着，访客才能完整体验一次「写信 → 仪式 → 花园长出来」的闭环；
    同时观测台 / 花园 / 日历里已经有 365 天的数据可看。

用法：python tools/make-demo-data.py
输出：scripts/demo-data.js
"""
import csv
import io
import json
import os
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'data', 'synthetic_entries.csv')
OUT = os.path.join(ROOT, 'scripts', 'demo-data.js')


def main():
    with io.open(SRC, encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    rows.sort(key=lambda r: r['日期'])
    last = date.fromisoformat(rows[-1]['日期'])

    lines = []
    for r in rows:
        # offset：今天 = 0，昨天 = 1……末条正好落在昨天
        off = (last - date.fromisoformat(r['日期'])).days + 1
        tags = (r.get('标签') or '').strip()
        note = (r.get('备注') or '').strip()
        lines.append('[%d,%d,%d,%s,%s]' % (
            off,
            int(r['心情']),
            int(r['力气']),
            json.dumps(tags, ensure_ascii=False),
            json.dumps(note, ensure_ascii=False),
        ))

    head = (
        '/* ===========================================================\n'
        '   demo-data.js —— 演示模式的数据（?demo=1 时使用）\n'
        '   由 tools/make-demo-data.py 从 data/synthetic_entries.csv 生成，不要手改。\n'
        '\n'
        '   每行 = [距今天数, 心情1-5, 力气1-5, "标签|标签", "备注"]\n'
        '   存的是「距今天数」而不是日期，运行时才换算 —— 所以这份数据不会过期。\n'
        '\n'
        '   它不是真实用户数据：来自一份设定了生成机制的模拟数据集\n'
        '   （平常 3.5 / 力气 2 / 一周差一两天 / 状态差的时候会漏记），\n'
        '   用来展示观测台、花园、日历在长周期下的表现。\n'
        '   =========================================================== */\n'
        '(function (global) {\n'
        "  'use strict';\n"
        '  global.App = global.App || {};\n'
        '  global.App.demoEntries = [\n'
    )
    body = ',\n'.join('    ' + ln for ln in lines)
    tail = '\n  ];\n})(window);\n'

    with io.open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write(head + body + tail)

    size = os.path.getsize(OUT)
    print('记录 %d 条 → %s（%.1f KB）' % (len(lines), OUT, size / 1024.0))
    print('日期范围：今天-%d 天 ~ 昨天（%s ~ %s）' % (
        int(lines[0][1:].split(',')[0]), '今天-%d' % int(lines[0][1:].split(',')[0]), '昨天'))


if __name__ == '__main__':
    main()
