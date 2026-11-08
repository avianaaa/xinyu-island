#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合成数据生成器 —— 心屿情绪记录 · N-of-1 纵向数据集
=====================================================

⚠️ 这个脚本生成的是**合成数据**，不来自任何真实个体。
   用途：在没有长期真实记录的情况下，验证「指标设计 → 分级规则 → 结论边界」
   这套分析流程是否成立。所有下游分析都必须标注这一点。

设计原则：不是「随机数 + 噪声」，而是先写死一个**生成机制**，再从机制采样。
这样数据里存在可被真实发现的模式，分析结论才能被反向验证（见 verify-synthetic.py）。

生成机制（真值参数见 PARAMS）
    心情 = 基线 + 星期效应 + 学期事件 + 低谷日冲击 + 个体噪声
    精力 = 基线 + 心情的线性映射 + 独立噪声        ← 同涨同落，但不同步到 1:1
    睡眠 = 精力驱动 + 噪声
    漏记 = 与当天状态相关（MNAR）                   ← 最容易分析的「坏」数据
"""
import json
import os
from datetime import date, timedelta

import numpy as np

# ---------------------------------------------------------------- 真值参数
PARAMS = {
    'seed': 20261103,
    'date_start': '2025-11-01',
    'date_end': '2026-10-31',

    # 心情（1–5 自评）
    'valence_base': 3.5,          # 平常日子
    'valence_noise_sd': 0.50,

    # 精力（1–5 自评）
    'energy_base': 2.15,           # 「人长期没电」是这个数据集的核心特征
    'energy_from_valence': 0.72,  # 心情每高 1 分，精力高 0.72 分 → 强正相关但非恒等
    'energy_noise_sd': 0.45,

    # 星期效应（周一=0）
    'weekday_effect': [-0.10, -0.02, 0.02, 0.06, 0.16, 0.20, 0.10],

    # 学期节奏事件：日期区间 → 心情偏移
    'events': [
        ['2025-11-10', '2025-11-21', -0.80, '秋季期中'],
        ['2026-01-05', '2026-01-20', -1.05, '期末周'],
        ['2026-01-21', '2026-02-22', 0.45, '寒假'],
        ['2026-04-20', '2026-05-02', -0.90, '春季期中'],
        ['2026-06-15', '2026-06-30', -1.05, '期末周'],
        ['2026-07-06', '2026-08-20', 0.35, '暑假'],
    ],

    # 低谷日：每周 1–2 天，心情 -1.15、精力 -0.75
    'low_days_per_week': {'1': 0.60, '2': 0.40},
    'low_valence_drop': -1.15,
    'low_energy_drop': -0.75,

    # 漏记机制（MNAR：状态越差越容易忘）
    'miss_base': 0.02,
    'miss_if_low_day': 0.30,
    'miss_if_event': 0.12,

    # 辅助字段
    'sleep_base': 6.4,
    'sleep_from_energy': 0.55,
    'sleep_noise_sd': 0.55,
}

NEG_TAGS = ['疲惫', '烦躁', '麻木', '睡不着', '孤单', '委屈', '头痛']
POS_TAGS = ['平静', '安心', '开心', '有活力', '身体轻松', '感激', '期待']
SCENE_LOW = ['学习', '工作', '独处']
SCENE_OK = ['朋友', '出门', '休息', '家人', '运动']

NOTES = {
    'low': ['今天不太行', '有点撑不住', '睡了很久还是累', '什么都没做', '不想说话'],
    'mid': ['还行吧', '就那样', '普通的一天', '没什么特别的'],
    'high': ['今天挺好的', '睡够了', '出去走了一圈', '有点力气了'],
}


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def _event_offset(d, events):
    """当天的学期事件偏移（可能叠加，取和）。"""
    total = 0.0
    for start, end, offset, _name in events:
        if date.fromisoformat(start) <= d <= date.fromisoformat(end):
            total += offset
    return total


def _pick_low_days(dates, rng, params):
    """每周抽 1–2 天作为低谷日。按 ISO 周分组。"""
    weeks = {}
    for i, d in enumerate(dates):
        weeks.setdefault(d.isocalendar()[:2], []).append(i)

    low = set()
    p = params['low_days_per_week']
    for _k, idxs in weeks.items():
        n = 2 if rng.random() < p['2'] else 1
        n = min(n, len(idxs))
        low.update(rng.choice(idxs, size=n, replace=False).tolist())
    return low


def generate(params=PARAMS):
    rng = np.random.default_rng(params['seed'])

    start = date.fromisoformat(params['date_start'])
    end = date.fromisoformat(params['date_end'])
    dates = [start + timedelta(days=i) for i in range((end - start).days + 1)]

    low_days = _pick_low_days(dates, rng, params)

    rows = []
    truth = []          # 未取整、未截断的连续真值，用于回收验证
    for i, d in enumerate(dates):
        wd = d.weekday()
        ev = _event_offset(d, params['events'])
        is_low = i in low_days

        v = params['valence_base'] + params['weekday_effect'][wd] + ev
        e_extra = 0.0
        if is_low:
            v += params['low_valence_drop']
            e_extra = params['low_energy_drop']
        v += rng.normal(0, params['valence_noise_sd'])

        e = (params['energy_base']
             + params['energy_from_valence'] * (v - params['valence_base'])
             + e_extra
             + rng.normal(0, params['energy_noise_sd']))

        truth.append({'date': d.isoformat(), 'valence_cont': round(v, 4), 'energy_cont': round(e, 4)})

        # 自评是整数，且会被截断在 1–5
        v_int = int(np.clip(round(v), 1, 5))
        e_int = int(np.clip(round(e), 1, 5))

        # 漏记：状态越差越容易忘
        p_miss = params['miss_base']
        if is_low:
            p_miss += params['miss_if_low_day']
        if ev < -0.5:
            p_miss += params['miss_if_event']
        if rng.random() < p_miss:
            continue

        # 睡眠与运动
        sleep = params['sleep_base'] + params['sleep_from_energy'] * (e - params['energy_base'])
        sleep = float(np.clip(sleep + rng.normal(0, params['sleep_noise_sd']), 4.0, 9.5))
        p_sport = _sigmoid(0.60 * (v - params['valence_base']) + 0.40 * (e - params['energy_base']) - 0.90)
        sport = int(rng.random() < p_sport)

        # 标签：与状态相关，但不会 100% 一致（真实的人也不会）
        tags = []
        if v_int <= 2:
            pool, scene, note_pool = NEG_TAGS, SCENE_LOW, NOTES['low']
        elif v_int >= 4:
            pool, scene, note_pool = POS_TAGS, SCENE_OK, NOTES['high']
        else:
            pool, scene, note_pool = NEG_TAGS + POS_TAGS, SCENE_LOW + SCENE_OK, NOTES['mid']

        tags = rng.choice(pool, size=int(rng.integers(1, 3)), replace=False).tolist()
        if rng.random() < 0.55:
            tags.append(str(rng.choice(scene)))

        note = str(rng.choice(note_pool)) if rng.random() < 0.15 else ''

        rows.append({
            '日期': d.isoformat(),
            '心情': v_int,
            '心情描述': ['很差', '有点低', '还行', '挺好', '很好'][v_int - 1],
            '力气': e_int,
            '力气描述': ['没力气', '有点累', '一般', '还行', '有劲'][e_int - 1],
            '睡眠时长': round(sleep, 1),
            '是否运动': sport,
            '标签': '|'.join(str(t) for t in tags),
            '备注': note,
        })

    return rows, truth, dates, low_days


def main():
    rows, truth, dates, low_days = generate()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(root, 'data')
    os.makedirs(data_dir, exist_ok=True)

    csv_path = os.path.join(data_dir, 'synthetic_entries.csv')
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        header = ['日期', '心情', '心情描述', '力气', '力气描述', '睡眠时长', '是否运动', '标签', '备注']
        f.write(','.join(header) + '\r\n')
        for r in rows:
            cells = []
            for k in header:
                s = str(r[k])
                if ',' in s or '"' in s or '\n' in s:
                    s = '"' + s.replace('"', '""') + '"'
                cells.append(s)
            f.write(','.join(cells) + '\r\n')

    # 真值：包括观测不到的那部分，用于量化漏记偏差
    obs_dates = {r['日期'] for r in rows}
    missed = [t for t in truth if t['date'] not in obs_dates]
    all_v = [t['valence_cont'] for t in truth]
    obs_v = [t['valence_cont'] for t in truth if t['date'] in obs_dates]

    gt = {
        'note': '合成数据真值参数。分析时应先隐藏本文件，用数据反推，再与本文件比对。',
        'params': PARAMS,
        'summary': {
            'days_total': len(truth),
            'days_recorded': len(obs_dates),
            'days_missed': len(missed),
            'miss_rate': round(len(missed) / len(truth), 4),
            'true_valence_mean_all_days': round(float(np.mean(all_v)), 4),
            'true_valence_mean_recorded': round(float(np.mean(obs_v)), 4),
            'missed_days_valence_mean': round(float(np.mean([t['valence_cont'] for t in missed])), 4) if missed else None,
            'low_day_count': len(low_days),
        },
        'truth_series': truth,
    }
    with open(os.path.join(data_dir, 'ground_truth.json'), 'w', encoding='utf-8') as f:
        json.dump(gt, f, ensure_ascii=False, indent=2)

    s = gt['summary']
    print('已生成 %s' % csv_path)
    print('  天数 %d，记录 %d，漏记 %d（%.1f%%）' % (
        s['days_total'], s['days_recorded'], s['days_missed'], s['miss_rate'] * 100))
    print('  漏记日的心情均值 %.2f vs 已记录日 %.2f' % (
        s['missed_days_valence_mean'], s['true_valence_mean_recorded']))
    print('  真值均值（全部日子）%.2f，只算记录日 %.2f' % (
        s['true_valence_mean_all_days'], s['true_valence_mean_recorded']))


if __name__ == '__main__':
    main()
