#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
心屿 · N-of-1 情绪数据分析
==========================

输入：data/synthetic_entries.csv（合成数据，由 tools/gen-synthetic.py 生成）
输出：analysis/figures/*.png + 控制台统计

⚠️ 数据是合成的。这个脚本演示的是**方法**：指标怎么定义、口径怎么写、
   结论能推到哪、不能推到哪。真实的 N-of-1 分析流程与此完全一致。

分析结构
    1  数据质量
    2  描述统计
    3  时间趋势
    4  星期效应
    5  双维关系
    6  低落期的特征
    7  漏记偏差（MNAR）
    8  参数回收验证（用真值）
"""
import json
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.facecolor'] = '#FBF6EC'
plt.rcParams['axes.facecolor'] = '#FBF6EC'
plt.rcParams['axes.edgecolor'] = '#C9BFA0'
plt.rcParams['axes.labelcolor'] = '#6E6353'
plt.rcParams['text.color'] = '#4A4237'
plt.rcParams['xtick.color'] = '#8B7E6C'
plt.rcParams['ytick.color'] = '#8B7E6C'
plt.rcParams['font.size'] = 10

INK = '#4A4237'
BROWN = '#8B6F52'
MOOD = ['#9DB3C6', '#A9B48F', '#CFC29B', '#E7AC94', '#E08A5C']   # 与产品同一套色阶

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(ROOT, 'analysis', 'figures')


def load():
    df = pd.read_csv(os.path.join(ROOT, 'data', 'synthetic_entries.csv'),
                     encoding='utf-8-sig', parse_dates=['日期'])
    df = df.sort_values('日期').reset_index(drop=True)
    df['weekday'] = df['日期'].dt.day_of_week
    df['month'] = df['日期'].dt.to_period('M').astype(str)
    return df


def section(title):
    print('\n' + '=' * 62)
    print(title)
    print('=' * 62)


# --------------------------------------------------------------- 1 数据质量
def quality(df, start, end):
    section('1  数据质量')
    full = pd.date_range(start, end, freq='D')
    recorded = set(df['日期'])
    missing = [d for d in full if d not in recorded]

    print('覆盖区间      %s → %s（%d 天）' % (start.date(), end.date(), len(full)))
    print('实际记录      %d 天' % len(df))
    print('缺失          %d 天（%.1f%%）' % (len(missing), len(missing) / len(full) * 100))
    print('重复日期      %d 条' % df['日期'].duplicated().sum())

    gaps = df['日期'].diff().dt.days.dropna()
    print('记录间隔      中位数 %d 天，最长 %.0f 天' % (gaps.median(), gaps.max()))

    miss = pd.Series(1, index=pd.DatetimeIndex(missing))
    by_month = miss.groupby(miss.index.to_period('M')).size() if len(miss) else pd.Series(dtype=int)
    if len(by_month):
        top = by_month.sort_values(ascending=False).head(3)
        print('缺失最多的月份 ' + '，'.join('%s（%d 天）' % (k, v) for k, v in top.items()))

    out_of_range = df[~df['心情'].between(1, 5) | ~df['力气'].between(1, 5)]
    print('越界取值      %d 条' % len(out_of_range))
    return missing


# --------------------------------------------------------------- 2 描述统计
def describe(df):
    section('2  描述统计')
    for col in ['心情', '力气']:
        s = df[col]
        print('%s  均值 %.2f  标准差 %.2f  中位数 %.0f  最低 %d  最高 %d  振幅 %d' % (
            col, s.mean(), s.std(), s.median(), s.min(), s.max(), s.max() - s.min()))
        dist = s.value_counts().sort_index()
        print('     分布 ' + '  '.join('%d分:%d(%.0f%%)' % (k, v, v / len(s) * 100)
                                      for k, v in dist.items()))
    print('\n睡眠时长  均值 %.1f h  标准差 %.2f' % (df['睡眠时长'].mean(), df['睡眠时长'].std()))
    print('运动天数  %d / %d（%.0f%%）' % (df['是否运动'].sum(), len(df),
                                          df['是否运动'].mean() * 100))
    gap = df['心情'].mean() - df['力气'].mean()
    print('\n心情与力气均值差  %.2f 分  ← 这个落差本身就是可分析的信号' % gap)


# --------------------------------------------------------------- 3 时间趋势
def trend(df, start, end):
    section('3  时间趋势')
    full = pd.date_range(start, end, freq='D')
    s = df.set_index('日期')['心情'].reindex(full)

    x = np.arange(len(s))
    mask = s.notna().values
    res = stats.linregress(x[mask], s.values[mask])
    print('线性趋势  斜率 %+.4f 分/天（%+.2f 分/年）  p = %.3f' % (
        res.slope, res.slope * 365, res.pvalue))
    print('          判定 ' + ('显著' if res.pvalue < 0.05 else '不显著——一年内没有整体恶化或改善'))

    roll = s.rolling(7, min_periods=3).mean()
    valid = roll.dropna()
    print('7 日滚动均值  最低 %.2f（%s）  最高 %.2f（%s）' % (
        valid.min(), valid.idxmin().date(), valid.max(), valid.idxmax().date()))

    vol = valid.std()
    print('滚动均值波动  %.2f 分  「走向」比「单日」稳定得多' % vol)
    return s, roll


# --------------------------------------------------------------- 4 星期效应
def weekday_effect(df):
    section('4  星期效应')
    names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    groups = [df.loc[df['weekday'] == i, '心情'].values for i in range(7)]
    for i, g in enumerate(groups):
        print('%s  n=%3d  均值 %.2f  标准差 %.2f' % (names[i], len(g), g.mean(), g.std()))
    f, p = stats.f_oneway(*groups)
    print('\n单因素方差分析  F = %.2f  p = %.3f  → %s' % (
        f, p, '星期之间存在差异' if p < 0.05 else '没有足够证据说明星期之间有差异'))
    return groups, f, p


# --------------------------------------------------------------- 5 双维关系
def correlation(df):
    section('5  心情与力气的关系')
    r, p = stats.pearsonr(df['心情'], df['力气'])
    n = len(df)
    z = np.arctanh(r)
    se = 1 / np.sqrt(n - 3)
    lo, hi = np.tanh(z - 1.96 * se), np.tanh(z + 1.96 * se)
    print('Pearson r = %.3f   95%% CI [%.3f, %.3f]   p = %.2e   n = %d' % (r, lo, hi, p, n))
    print('决定系数 R² = %.3f  → 心情能解释力气 %.0f%% 的方差' % (r ** 2, r ** 2 * 100))

    d = df['心情'] - df['力气']
    diverge = df[(df['心情'] >= 4) & (df['力气'] <= 2)]
    print('\n「心情不低但人没电」的天数  %d（%.1f%%）' % (len(diverge), len(diverge) / n * 100))
    print('平均落差 %.2f 分' % d.mean())
    return r, lo, hi


# --------------------------------------------------------------- 6 低落期
def low_periods(df):
    section('6  低落期与平稳期的特征差异')
    v = df['心情'].values
    in_low = np.zeros(len(v), dtype=bool)
    run = 0
    for i, val in enumerate(v):
        run = run + 1 if val <= 2 else 0
        if run >= 2:
            in_low[max(0, i - run + 1):i + 1] = True

    low = df[in_low]
    calm = df[~in_low]
    print('低落段天数  %d（%.1f%%）   平稳段 %d' % (len(low), len(low) / len(df) * 100, len(calm)))
    if len(low) > 3:
        print('低落段  心情 %.2f / 力气 %.2f / 睡眠 %.1fh / 运动率 %.0f%%' % (
            low['心情'].mean(), low['力气'].mean(), low['睡眠时长'].mean(), low['是否运动'].mean() * 100))
        print('平稳段  心情 %.2f / 力气 %.2f / 睡眠 %.1fh / 运动率 %.0f%%' % (
            calm['心情'].mean(), calm['力气'].mean(), calm['睡眠时长'].mean(), calm['是否运动'].mean() * 100))

        t, p = stats.ttest_ind(low['睡眠时长'], calm['睡眠时长'], equal_var=False)
        print('\n睡眠时长差异  t = %.2f  p = %.3f' % (t, p))
        table = pd.crosstab(in_low, df['是否运动'])
        if table.shape == (2, 2):
            chi2, pc, _, _ = stats.chi2_contingency(table)
            print('运动比例差异  χ² = %.2f  p = %.3f' % (chi2, pc))
    return low, calm


# --------------------------------------------------------------- 7 漏记偏差
def missing_bias(df, truth, start, end):
    section('7  漏记偏差（MNAR 检验）')
    full = pd.date_range(start, end, freq='D')
    recorded = set(df['日期'])
    t = pd.DataFrame(truth)
    t['日期'] = pd.to_datetime(t['date'])
    t = t.set_index('日期')
    t['recorded'] = t.index.isin(recorded)

    obs = t[t['recorded']]['valence_cont']
    mis = t[~t['recorded']]['valence_cont']
    print('记录日      n=%d  真值心情 %.3f' % (len(obs), obs.mean()))
    print('漏记日      n=%d  真值心情 %.3f' % (len(mis), mis.mean()))
    if len(mis) > 2:
        u, p = stats.mannwhitneyu(obs, mis, alternative='greater')
        print('漏记日是否更差  p = %.4f  → %s' % (p, '是，且方向明显' if p < 0.05 else '证据不足'))
    print('\n偏差量化  观测均值 %.3f  真值均值 %.3f  高估 %+.3f 分（%+.1f%%）' % (
        obs.mean(), t['valence_cont'].mean(), obs.mean() - t['valence_cont'].mean(),
        (obs.mean() / t['valence_cont'].mean() - 1) * 100))
    print('\n结论：缺失不是随机的（MNAR）。越难受越不想记，于是记录下来的自己比真实的自己好一些。')
    print('      任何基于这份数据的「平均心情」都应注明这个方向上的偏差。')
    return t


# --------------------------------------------------------------- 8 参数回收
def recovery(df, gt):
    section('8  参数回收验证（用真值比对估计值）')
    p = gt['params']
    got = {
        '心情基线（估计）': df['心情'].mean(),
        '心情基线（设定）': p['valence_base'],
        '力气基线（估计）': df['力气'].mean(),
        '力气基线（设定）': p['energy_base'],
        '双维相关（估计）': df['心情'].corr(df['力气']),
        '双维相关（设定）': p['energy_from_valence'],
    }
    for k, v in got.items():
        print('%-18s %.3f' % (k, v))
    print('\n注意：「设定」的是连续真值上的斜率，观测到的是取整并截断后的相关系数，')
    print('      两者不必相等；这里看的是方向和量级是否吻合，而不是精确复现。')


# --------------------------------------------------------------- 图
def figures(df, s, roll, groups, f, p_val, r, miss_monthly, obs_v, miss_v):
    os.makedirs(FIG, exist_ok=True)

    # 1 分布
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
    for ax, col in zip(axes, ['心情', '力气']):
        d = df[col].value_counts().sort_index()
        ax.bar(d.index, d.values, color=MOOD, edgecolor='#C9BFA0', linewidth=.6, width=.66)
        for x, y in zip(d.index, d.values):
            ax.text(x, y + 2, str(y), ha='center', fontsize=9, color=INK)
        ax.set_title(col + '分布', fontsize=11, pad=8)
        ax.set_xticks([1, 2, 3, 4, 5])
        ax.set_xlabel('自评分数')
        ax.set_ylim(0, d.max() * 1.18)
        ax.grid(axis='y', linestyle=':', alpha=.45)
        ax.set_axisbelow(True)
        for sp in ['top', 'right']:
            ax.spines[sp].set_visible(False)
    fig.suptitle('两个维度都不是正态分布：集中在中间档，两端稀少', fontsize=11, y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, '01_distribution.png'), dpi=150, bbox_inches='tight')
    plt.close(fig)

    # 2 时间序列
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(s.index, s.values, '.', ms=3.2, color='#B9AC9A', alpha=.75, label='单日自评')
    ax.plot(roll.index, roll.values, '-', lw=1.9, color=BROWN, label='7 日滚动均值')
    for start, end, _o, name in [
        ('2025-11-10', '2025-11-21', 0, '秋期中'), ('2026-01-05', '2026-01-20', 0, '期末'),
        ('2026-04-20', '2026-05-02', 0, '春期中'), ('2026-06-15', '2026-06-30', 0, '期末')]:
        ax.axvspan(pd.Timestamp(start), pd.Timestamp(end), color='#E7AC94', alpha=.28, lw=0)
    ax.set_ylim(0.6, 5.4)
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.set_ylabel('心情')
    ax.set_title('一年的心情轨迹：起伏密集，但整体没有单向变化（橙色带为学期高压期）', fontsize=11, pad=10)
    ax.legend(frameon=False, loc='lower right', fontsize=9)
    ax.grid(axis='y', linestyle=':', alpha=.4)
    ax.set_axisbelow(True)
    for sp in ['top', 'right']:
        ax.spines[sp].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, '02_series.png'), dpi=150, bbox_inches='tight')
    plt.close(fig)

    # 3 星期效应
    names = ['一', '二', '三', '四', '五', '六', '日']
    means = [g.mean() for g in groups]
    sems = [g.std(ddof=1) / np.sqrt(len(g)) for g in groups]
    fig, ax = plt.subplots(figsize=(8, 3.8))
    ax.axhline(np.mean(means), color='#C9BFA0', ls='--', lw=1, label='全周均值')
    ax.errorbar(range(7), means, yerr=sems, fmt='o', ms=9, color=BROWN, capsize=5, lw=1.1,
                mfc='#A8C09A', mec=BROWN, mew=1.2, ecolor=BROWN, label='均值 ± 标准误')
    ax.set_xticks(range(7))
    ax.set_xticklabels(['周' + n for n in names])
    ax.set_xlim(-0.6, 6.6)
    ax.set_ylim(2.7, 3.85)
    ax.set_ylabel('心情均值')
    ax.set_title('星期效应：F = %.2f，p = %.3f（%s）' % (
        f, p_val, '差异显著' if p_val < 0.05 else '差异不显著'), fontsize=11, pad=10)
    ax.legend(frameon=False, fontsize=9, loc='upper left')
    ax.grid(axis='y', linestyle=':', alpha=.4)
    ax.set_axisbelow(True)
    for sp in ['top', 'right']:
        ax.spines[sp].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, '03_weekday.png'), dpi=150, bbox_inches='tight')
    plt.close(fig)

    # 4 散点
    fig, ax = plt.subplots(figsize=(5.4, 4.4))
    jitter = np.random.default_rng(7).normal(0, .09, size=(len(df), 2))
    ax.scatter(df['心情'] + jitter[:, 0], df['力气'] + jitter[:, 1], s=22,
               color='#A8C8DC', edgecolor='#8B6F52', linewidth=.4, alpha=.85)
    k, b = np.polyfit(df['心情'], df['力气'], 1)
    xs = np.array([1, 5])
    ax.plot(xs, k * xs + b, color=BROWN, lw=1.6, label='拟合 y = %.2fx %+.2f' % (k, b))
    ax.plot(xs, xs, '--', color='#C9BFA0', lw=1, label='y = x（同涨同落）')
    ax.set_xlabel('心情')
    ax.set_ylabel('力气')
    ax.set_xticks([1, 2, 3, 4, 5])
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.set_title('r = %.2f：同步，但力气始终低于心情' % r, fontsize=11, pad=10)
    ax.legend(frameon=False, fontsize=9, loc='upper left')
    ax.grid(linestyle=':', alpha=.35)
    ax.set_axisbelow(True)
    for sp in ['top', 'right']:
        ax.spines[sp].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, '04_scatter.png'), dpi=150, bbox_inches='tight')
    plt.close(fig)

    # 5 漏记偏差
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), gridspec_kw={'width_ratios': [1.4, 1]})
    ax = axes[0]
    ax.bar(range(len(miss_monthly)), miss_monthly.values, color='#E7AC94',
           edgecolor='#8B6F52', linewidth=.5, width=.6)
    ax.set_xticks(range(len(miss_monthly)))
    ax.set_xticklabels([str(t)[2:] for t in miss_monthly.index], rotation=45, ha='right', fontsize=8)
    ax.set_ylabel('漏记天数')
    ax.set_title('按月漏记分布', fontsize=10.5, pad=8)
    ax.grid(axis='y', linestyle=':', alpha=.4)
    ax.set_axisbelow(True)
    for sp in ['top', 'right']:
        ax.spines[sp].set_visible(False)

    ax = axes[1]
    ax.bar(['记录的\n日子', '漏掉的\n日子'], [obs_v, miss_v], color=['#A8C09A', '#9DB3C6'],
           edgecolor='#8B6F52', linewidth=.5, width=.5)
    for i, v in enumerate([obs_v, miss_v]):
        ax.text(i, v + 0.08, '%.2f' % v, ha='center', fontsize=10, color=INK)
    ax.set_ylim(0, 4)
    ax.set_ylabel('心情（连续真值）')
    ax.set_title('漏掉的日子更差', fontsize=10.5, pad=8)
    ax.grid(axis='y', linestyle=':', alpha=.4)
    ax.set_axisbelow(True)
    for sp in ['top', 'right']:
        ax.spines[sp].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, '05_missing.png'), dpi=150, bbox_inches='tight')
    plt.close(fig)

    print('\n图已输出到 analysis/figures/')


def main():
    df = load()
    with open(os.path.join(ROOT, 'data', 'ground_truth.json'), encoding='utf-8') as f:
        gt = json.load(f)
    start = pd.Timestamp(gt['params']['date_start'])
    end = pd.Timestamp(gt['params']['date_end'])

    quality(df, start, end)
    describe(df)
    s, roll = trend(df, start, end)
    groups, f, p_val = weekday_effect(df)
    r, _lo, _hi = correlation(df)
    low_periods(df)
    mb = missing_bias(df, gt['truth_series'], start, end)
    recovery(df, gt)

    months = pd.period_range(start, end, freq='M')
    miss_monthly = (mb[~mb['recorded']]
                    .groupby(mb[~mb['recorded']].index.to_period('M'))
                    .size().reindex(months).fillna(0).astype(int))
    obs_v = mb[mb['recorded']]['valence_cont'].mean()
    miss_v = mb[~mb['recorded']]['valence_cont'].mean()

    figures(df, s, roll, groups, f, p_val, r, miss_monthly, obs_v, miss_v)


if __name__ == '__main__':
    main()
