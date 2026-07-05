#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
engine.py — 多功能小区间势段信号引擎
======================================
功能：获取数据 → 识别涨势段+跌势段 → 扫描认购+认沽买入信号 → 返回结果
独立模块，供 main.py GUI 调用。
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

MAX_SCAN_DAYS = 200

# ============================================================
# 数据获取
# ============================================================
def fetch_data(symbol="sz399006"):
    """从新浪财经API直接获取创业板日线（无需akshare）。"""
    try:
        import requests, json

        url = 'https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData'
        params = {'symbol': symbol, 'scale': '240', 'ma': 'no', 'datalen': '5000'}
        r = requests.get(url, params=params, timeout=30)
        data = json.loads(r.text)

        if not data or not isinstance(data, list):
            raise RuntimeError('API返回数据为空')

        df = pd.DataFrame(data)
        df['日期'] = pd.to_datetime(df['day'])
        df['指数点'] = df['close'].astype(float)
        df['最高指数点'] = df['high'].astype(float)
        df['最低指数点'] = df['low'].astype(float)
        df = df.sort_values('日期').reset_index(drop=True)
        df['当日涨跌幅%'] = df['指数点'].pct_change() * 100
        df = df.dropna(subset=['当日涨跌幅%']).reset_index(drop=True)
        return df
    except Exception as e:
        raise RuntimeError(f"获取失败: {e}\n请检查网络或防火墙设置")

# ============================================================
# 涨势段识别
# ============================================================
def identify_uptrend_segments(df):
    """识别小区间涨势段"""
    n = len(df)
    segments = []
    i = 0
    while i < n:
        ret_i = df.loc[i, '当日涨跌幅%']
        if pd.isna(ret_i) or ret_i <= 0:
            i += 1; continue
        A_idx = i
        A_low = df.loc[A_idx, '最低指数点']
        found_B = False
        scan_end = min(A_idx + MAX_SCAN_DAYS, n - 1)
        for j in range(A_idx + 2, scan_end + 1):
            ret_j = df.loc[j, '当日涨跌幅%']
            if pd.isna(ret_j): continue
            has_down = any(not pd.isna(df.loc[k,'当日涨跌幅%']) and df.loc[k,'当日涨跌幅%']<0 for k in range(A_idx+1,j))
            if not has_down: continue
            cond_b = (ret_j < -1.5)
            if not cond_b and j >= 2:
                r0=ret_j; r1=df.loc[j-1,'当日涨跌幅%']; r2=df.loc[j-2,'当日涨跌幅%']
                if not pd.isna(r1) and not pd.isna(r2) and r0<0 and r1<0 and r2<0 and r0+r1+r2<-1.5:
                    cond_b=True
            if not cond_b: continue
            found_B = True
            if df.loc[j,'指数点'] >= A_low * 1.02:
                b_plus1 = min(j+1, n-1)
                segments.append({
                    'A_idx': A_idx, 'B_idx': j,
                    'A日期': df.loc[A_idx,'日期'], 'B日期': df.loc[j,'日期'],
                    '区间最高': round(df.loc[A_idx:b_plus1,'最高指数点'].max(),2),
                    '区间收盘最高': round(df.loc[A_idx:b_plus1,'指数点'].max(),2),
                    '区间最低': round(df.loc[A_idx:b_plus1,'最低指数点'].min(),2),
                    '区间收盘最低': round(df.loc[A_idx:b_plus1,'指数点'].min(),2),
                    '方向': '涨',
                })
            i = j; break
        if not found_B: i += 1
    return segments

# ============================================================
# 跌势段识别
# ============================================================
def identify_downtrend_segments(df):
    """识别小区间跌势段"""
    n = len(df)
    segments = []
    i = 0
    while i < n:
        ret_i = df.loc[i, '当日涨跌幅%']
        if pd.isna(ret_i) or ret_i >= 0:
            i += 1; continue
        A_idx = i
        A_high = df.loc[A_idx, '最高指数点']
        found_B = False
        scan_end = min(A_idx + MAX_SCAN_DAYS, n - 1)
        for j in range(A_idx + 2, scan_end + 1):
            ret_j = df.loc[j, '当日涨跌幅%']
            if pd.isna(ret_j): continue
            has_up = any(not pd.isna(df.loc[k,'当日涨跌幅%']) and df.loc[k,'当日涨跌幅%']>0 for k in range(A_idx+1,j))
            if not has_up: continue
            cond_b = (ret_j > 1.5)
            if not cond_b and j >= 2:
                r0=ret_j; r1=df.loc[j-1,'当日涨跌幅%']; r2=df.loc[j-2,'当日涨跌幅%']
                if not pd.isna(r1) and not pd.isna(r2) and r0>0 and r1>0 and r2>0 and r0+r1+r2>1.5:
                    cond_b=True
            if not cond_b: continue
            found_B = True
            if df.loc[j,'指数点'] <= A_high * 0.98:
                b_plus1 = min(j+1, n-1)
                segments.append({
                    'A_idx': A_idx, 'B_idx': j,
                    'A日期': df.loc[A_idx,'日期'], 'B日期': df.loc[j,'日期'],
                    '区间最高': round(df.loc[A_idx:b_plus1,'最高指数点'].max(),2),
                    '区间收盘最高': round(df.loc[A_idx:b_plus1,'指数点'].max(),2),
                    '区间最低': round(df.loc[A_idx:b_plus1,'最低指数点'].min(),2),
                    '区间收盘最低': round(df.loc[A_idx:b_plus1,'指数点'].min(),2),
                    '方向': '跌',
                })
            i = j; break
        if not found_B: i += 1
    return segments

# ============================================================
# 认购信号扫描
# ============================================================
def scan_call_signals(df, up_segments):
    """扫描认购(做多)买入信号，返回最新一个信号或None"""
    n = len(df)
    seg_df = pd.DataFrame(up_segments) if up_segments else pd.DataFrame()
    if len(seg_df) < 2:
        return None

    # C日 = 最新交易日（数据最后一行），满足条件则 M日=明日
    c_idx = n - 1
    segs_before = seg_df[seg_df['B_idx'] <= c_idx].sort_values('B_idx')
    if len(segs_before) < 2:
        return None
    seg1 = segs_before.iloc[-1]
    seg2 = segs_before.iloc[-2]
    if seg1['区间收盘最高'] <= seg2['区间最高']:
        return None

    C_return = df.loc[c_idx, '当日涨跌幅%']
    if pd.isna(C_return) or C_return >= 0:
        return None

    seg1_B = int(seg1['B_idx'])
    has_down = any(not pd.isna(df.loc[k,'当日涨跌幅%']) and df.loc[k,'当日涨跌幅%']<0 for k in range(seg1_B+1, c_idx+1))
    if not has_down:
        return None

    D_idx = None; D_close = None
    for k in range(c_idx-1, 0, -1):
        r = df.loc[k,'当日涨跌幅%']
        if not pd.isna(r) and r >= 1.5:
            D_idx = k; D_close = df.loc[k,'指数点']; break
    if D_idx is None:
        return None

    C_close = df.loc[c_idx,'指数点']
    drop = (C_close - D_close) / D_close * 100
    if drop >= -3.0:
        return None

    # 信号成立！C=今日, M=明日
    C_date = df.loc[c_idx, '日期']
    M_date = C_date + timedelta(days=1)
    while M_date.weekday() >= 5:
        M_date += timedelta(days=1)

    stop_ref = df.loc[c_idx, '最低指数点']
    return {
        '方向': '认购(做多)',
        'M日期': M_date,
        'C日期': C_date,
        'C收盘': round(C_close, 2),
        'C涨跌幅': round(C_return, 2),
        'D日期': df.loc[D_idx,'日期'],
        'D收盘': round(D_close, 2),
        'D到C跌幅': round(drop, 2),
        '入场描述': f"明日在低于今日收盘价（{C_close:.0f}）的日内低点买入认购期权",
        '止盈价': round(C_close * 1.04, 2),
        '止损参考价': round(stop_ref * 0.96, 2),
        '最晚持有日': M_date + timedelta(days=14),
        '加仓条件': 'M日涨跌<0 且 M+1日涨跌<0 → M+1收盘加仓50%',
        '仓位': '50%头寸',
        '操作步骤': [
            f'1. 明日({M_date.strftime("%Y-%m-%d")})盘中，在低于{C_close:.0f}的日内低点买入认购期权，50%仓位',
            f'2. 止盈1: 收盘 > {C_close*1.04:.0f} 时平一半（约10倍杠杆）',
            f'3. 止盈2: 剩余在日跌>0.5%或从高点回落2%时清仓（约15倍杠杆）',
            f'4. 时间止损: 第9个交易日收盘未触发止盈1 → 全平',
            f'5. 最晚持有至约 M+10个交易日',
        ],
    }

# ============================================================
# 认沽信号扫描
# ============================================================
def scan_put_signals(df, down_segments):
    """扫描认沽(做空)买入信号，返回最新一个信号或None"""
    n = len(df)
    seg_df = pd.DataFrame(down_segments) if down_segments else pd.DataFrame()
    if len(seg_df) < 2:
        return None

    # C日 = 最新交易日，满足条件则 M日=明日
    c_idx = n - 1
    segs_before = seg_df[seg_df['B_idx'] <= c_idx].sort_values('B_idx')
    if len(segs_before) < 2:
        return None
    seg1 = segs_before.iloc[-1]
    seg2 = segs_before.iloc[-2]
    if seg1['区间收盘最低'] >= seg2['区间最低']:
        return None

    C_return = df.loc[c_idx, '当日涨跌幅%']
    if pd.isna(C_return) or C_return <= 0:
        return None

    seg1_B = int(seg1['B_idx'])
    has_up = any(not pd.isna(df.loc[k,'当日涨跌幅%']) and df.loc[k,'当日涨跌幅%']>0 for k in range(seg1_B+1, c_idx+1))
    if not has_up:
        return None

    D_idx = None; D_close = None
    for k in range(c_idx-1, 0, -1):
        r = df.loc[k,'当日涨跌幅%']
        if not pd.isna(r) and r <= -1.5:
            D_idx = k; D_close = df.loc[k,'指数点']; break
    if D_idx is None:
        return None

    C_close = df.loc[c_idx,'指数点']
    rise = (C_close - D_close) / D_close * 100
    if rise <= 3.0:
        return None

    C_date = df.loc[c_idx, '日期']
    M_date = C_date + timedelta(days=1)
    while M_date.weekday() >= 5:
        M_date += timedelta(days=1)

    stop_ref = df.loc[c_idx, '最高指数点']
    return {
        '方向': '认沽(做空)',
        'M日期': M_date,
        'C日期': C_date,
        'C收盘': round(C_close, 2),
        'C涨跌幅': round(C_return, 2),
        'D日期': df.loc[D_idx,'日期'],
        'D收盘': round(D_close, 2),
        'D到C涨幅': round(rise, 2),
        '入场描述': f"明日在高于今日收盘价（{C_close:.0f}）的日内高点买入认沽期权",
        '止盈价': round(C_close * 0.96, 2),
        '止损参考价': round(stop_ref * 1.04, 2),
        '最晚持有日': M_date + timedelta(days=14),
        '加仓条件': 'M日涨跌>0 且 M+1日涨跌>0 → M+1收盘加仓50%',
        '仓位': '50%头寸',
        '操作步骤': [
            f'1. 明日({M_date.strftime("%Y-%m-%d")})盘中，在高于{C_close:.0f}的日内高点买入认沽期权，50%仓位',
            f'2. 止盈1: 收盘 < {C_close*0.96:.0f} 时平一半（约10倍杠杆）',
            f'3. 止盈2: 剩余在日涨>0.5%或从低点反弹2%时清仓（约15倍杠杆）',
            f'4. 时间止损: 第9个交易日收盘未触发止盈1 → 全平',
            f'5. 最晚持有至约 M+10个交易日',
        ],
    }

# ============================================================
# 趋势判断
# ============================================================
def check_trend(df, up_segments, down_segments):
    """判断当前是否处于上涨/下跌趋势"""
    n = len(df)
    result = {'上涨趋势': False, '下跌趋势': False, '上涨详情': '', '下跌详情': ''}

    if len(up_segments) >= 2:
        s1 = up_segments[-1]
        s2 = up_segments[-2]
        if s1['区间收盘最高'] > s2['区间最高']:
            result['上涨趋势'] = True
            result['上涨详情'] = f"段{s1['A日期'].strftime('%m/%d')}→{s1['B日期'].strftime('%m/%d')}收盘最高{s1['区间收盘最高']:.0f} > 前段最高{s2['区间最高']:.0f}"

    if len(down_segments) >= 2:
        s1 = down_segments[-1]
        s2 = down_segments[-2]
        if s1['区间收盘最低'] < s2['区间最低']:
            result['下跌趋势'] = True
            result['下跌详情'] = f"段{s1['A日期'].strftime('%m/%d')}→{s1['B日期'].strftime('%m/%d')}收盘最低{s1['区间收盘最低']:.0f} < 前段最低{s2['区间最低']:.0f}"

    return result

# ============================================================
# 信号历史追踪 & 盈亏模拟
# ============================================================
def get_signal_history(df, up_segments, down_segments):
    """扫描所有历史信号，返回列表"""
    n = len(df)
    all_sigs = []
    seg_up = pd.DataFrame(up_segments) if up_segments else pd.DataFrame()
    seg_dn = pd.DataFrame(down_segments) if down_segments else pd.DataFrame()

    # 认购信号
    if len(seg_up) >= 2:
        for m_idx in range(3, n):   # 含最后一个交易日
            c_idx = m_idx - 1
            sb = seg_up[seg_up['B_idx'] < m_idx].sort_values('B_idx')
            if len(sb) < 2: continue
            s1, s2 = sb.iloc[-1], sb.iloc[-2]
            if s1['区间收盘最高'] <= s2['区间最高']: continue
            cr = df.loc[c_idx,'当日涨跌幅%']
            if pd.isna(cr) or cr >= 0: continue
            if not any(not pd.isna(df.loc[k,'当日涨跌幅%']) and df.loc[k,'当日涨跌幅%']<0 for k in range(int(s1['B_idx'])+1, c_idx+1)): continue
            D_idx = None
            for k in range(c_idx-1,0,-1):
                r = df.loc[k,'当日涨跌幅%']
                if not pd.isna(r) and r >= 1.5: D_idx = k; break
            if D_idx is None: continue
            cc = df.loc[c_idx,'指数点']; dc = df.loc[D_idx,'指数点']
            if (cc-dc)/dc*100 >= -3.0: continue
            all_sigs.append({'方向':'call','M_idx':m_idx,'M日期':df.loc[m_idx,'日期'],'C收盘':cc})

    # 认沽信号
    if len(seg_dn) >= 2:
        for m_idx in range(3, n):   # 含最后一个交易日
            c_idx = m_idx - 1
            sb = seg_dn[seg_dn['B_idx'] < m_idx].sort_values('B_idx')
            if len(sb) < 2: continue
            s1, s2 = sb.iloc[-1], sb.iloc[-2]
            if s1['区间收盘最低'] >= s2['区间最低']: continue
            cr = df.loc[c_idx,'当日涨跌幅%']
            if pd.isna(cr) or cr <= 0: continue
            if not any(not pd.isna(df.loc[k,'当日涨跌幅%']) and df.loc[k,'当日涨跌幅%']>0 for k in range(int(s1['B_idx'])+1, c_idx+1)): continue
            D_idx = None
            for k in range(c_idx-1,0,-1):
                r = df.loc[k,'当日涨跌幅%']
                if not pd.isna(r) and r <= -1.5: D_idx = k; break
            if D_idx is None: continue
            cc = df.loc[c_idx,'指数点']; dc = df.loc[D_idx,'指数点']
            if (cc-dc)/dc*100 <= 3.0: continue
            all_sigs.append({'方向':'put','M_idx':m_idx,'M日期':df.loc[m_idx,'日期'],'C收盘':cc})

    all_sigs.sort(key=lambda x: x['M_idx'])
    return all_sigs

def simulate_trade_pnl(df, sig):
    """模拟一笔已完结信号的盈亏。M+10未过返回None。"""
    n = len(df); m_idx = sig['M_idx']; direc = sig['方向']; C_close = sig['C收盘']
    max_hold = min(m_idx + 10, n - 1)
    if max_hold >= n - 1: return None  # 未完结

    entry = df.loc[m_idx, '最高指数点'] if direc=='put' else df.loc[m_idx, '最低指数点']
    tp1_f = False; tp1_p = None; tp2_f = False; tp2_p = None
    time_s = False; stop_f = False; peak = None; crash_days = set()

    # 止损计算
    c_low = df.loc[m_idx-1, '最低指数点'] if direc=='call' else df.loc[m_idx-1, '最高指数点']
    m_val = df.loc[m_idx, '最低指数点'] if direc=='call' else df.loc[m_idx, '最高指数点']
    stop_ref = min(c_low, m_val) if direc=='call' else max(c_low, m_val)
    stop_th = stop_ref * 0.96 if direc=='call' else stop_ref * 1.04

    for day in range(m_idx, max_hold+1):
        dc = df.loc[day,'指数点']; dr = df.loc[day,'当日涨跌幅%']

        # 跟踪暴跌/暴涨信号
        if direc=='call' and not pd.isna(dr) and dr > 2.0: crash_days.add(day)
        if direc=='put' and not pd.isna(dr) and dr < -2.0: crash_days.add(day)

        # 时间止损
        if not tp1_f and not stop_f and day == min(m_idx+9, n-1):
            time_s = True; tp1_f = True; tp1_p = dc; break

        # TP1
        if direc == 'call':
            if not tp1_f and dc > C_close*1.04: tp1_f = True; tp1_p = dc; peak = dc
        else:
            if not tp1_f and dc < C_close*0.96: tp1_f = True; tp1_p = dc; peak = dc

        # 移动止盈
        if tp1_f and not tp2_f and not stop_f:
            if direc == 'call':
                if dc > peak: peak = dc
                if (not pd.isna(dr) and dr < -0.5) or dc < peak*0.98: tp2_f = True; tp2_p = dc; break
            else:
                if dc < peak: peak = dc
                if (not pd.isna(dr) and dr > 0.5) or dc > peak*1.02: tp2_f = True; tp2_p = dc; break

        # 硬止损
        if not stop_f and not tp2_f and not time_s:
            if len(crash_days) > 0 and day >= m_idx + 2:
                if (direc=='call' and dc < stop_th) or (direc=='put' and dc > stop_th):
                    stop_f = True; break

    if not tp1_f and not stop_f:
        tp1_f = True; tp1_p = df.loc[max_hold,'指数点']
    elif tp1_f and not tp2_f and not stop_f:
        tp2_f = True; tp2_p = df.loc[max_hold,'指数点']

    cp = 0.50; tr = 0.0
    if stop_f:
        tr = cp * (-0.50)  # 全仓止损，-50%
    else:
        r1 = (tp1_p-entry)/entry if direc=='call' else (entry-tp1_p)/entry
        r2 = (tp2_p-entry)/entry if direc=='call' else (entry-tp2_p)/entry if tp2_f else 0
        tr += cp*0.5*max(r1*10.0, -1.0) + cp*0.5*max(r2*15.0, -1.0)

    held = (day if not (tp1_f and not stop_f) else max_hold) - m_idx + 1
    return {'收益率': round(tr*100,1), '时间止损': time_s, '硬止损': stop_f, '持仓天数': held}

def export_segments_excel(df, up_seg, down_seg, out_dir):
    """导出涨势段和跌势段Excel，含A收盘和B收盘"""
    import os; os.makedirs(out_dir, exist_ok=True)
    for segs, fn in [(up_seg, '小区间涨势段.xlsx'), (down_seg, '小区间跌势段.xlsx')]:
        rows = []
        for i, s in enumerate(segs, 1):
            a, b = s['A_idx'], s['B_idx']; b1 = min(b+1, len(df)-1)
            rows.append({
                '序号': i, '开始日A': s['A日期'].strftime('%Y-%m-%d'), '结束日B': s['B日期'].strftime('%Y-%m-%d'),
                'A日收盘': round(df.loc[a,'指数点'],2), 'B日收盘': round(df.loc[b,'指数点'],2),
                '区间最高': s['区间最高'], '区间最低': s['区间最低'],
                '区间收盘最高': s['区间收盘最高'], '区间收盘最低': s['区间收盘最低'],
                '持续天数': b-a+1,
            })
        pd.DataFrame(rows).to_excel(os.path.join(out_dir, fn), index=False)

# ============================================================
# 主入口
# ============================================================
def run_analysis():
    """运行完整分析，返回所有结果"""
    df = fetch_data()
    n = len(df)

    up_seg = identify_uptrend_segments(df)
    down_seg = identify_downtrend_segments(df)
    trend = check_trend(df, up_seg, down_seg)
    call_sig = scan_call_signals(df, up_seg)
    put_sig = scan_put_signals(df, down_seg)

    # 信号历史 & 辅助信息
    all_sigs = get_signal_history(df, up_seg, down_seg)
    last_date = df.loc[n-1, '日期']

    # 距上次信号天数
    last_call = None; last_put = None
    for s in reversed(all_sigs):
        if s['方向'] == 'call' and last_call is None: last_call = s
        if s['方向'] == 'put' and last_put is None: last_put = s
        if last_call and last_put: break

    days_call = (last_date - last_call['M日期']).days if last_call else None
    days_put  = (last_date - last_put['M日期']).days if last_put else None

    # 最近完结信号盈亏
    call_pnl = None; put_pnl = None
    for s in reversed(all_sigs):
        if s['方向'] == 'call' and call_pnl is None:
            call_pnl = simulate_trade_pnl(df, s)
        if s['方向'] == 'put' and put_pnl is None:
            put_pnl = simulate_trade_pnl(df, s)
        if call_pnl and put_pnl: break

    # 自适应暂停状态
    pause_active = False; pause_msg = ''
    for s in reversed(all_sigs):
        pnl = simulate_trade_pnl(df, s)
        if pnl and pnl['收益率'] < -30:
            pause_end_idx = s['M_idx'] + 3
            if pause_end_idx >= n - 1:
                pause_active = True
                pause_msg = f"前次{s['方向']}信号亏损{pnl['收益率']}% > 30%，建议暂停至{df.loc[min(pause_end_idx, n-1), '日期'].strftime('%m/%d')}"
            break

    return {
        '数据日期': df.loc[n-1, '日期'],
        '数据更新': datetime.now().strftime('%Y-%m-%d %H:%M'),
        '总交易日': n,
        '涨势段数': len(up_seg),
        '跌势段数': len(down_seg),
        '趋势': trend,
        '认购信号': call_sig,
        '认沽信号': put_sig,
        '辅助': {
            '距上次认购': days_call,
            '距上次认沽': days_put,
            '上次认购盈亏': call_pnl,
            '上次认沽盈亏': put_pnl,
            '自适应暂停': pause_active,
            '暂停说明': pause_msg,
        },
        '_df': df,
        '_up_seg': up_seg,
        '_down_seg': down_seg,
    }

if __name__ == '__main__':
    print("正在获取数据...")
    result = run_analysis()
    print(f"数据日期: {result['数据日期'].date()}")
    print(f"上涨趋势: {'是' if result['趋势']['上涨趋势'] else '否'}  {result['趋势']['上涨详情']}")
    print(f"下跌趋势: {'是' if result['趋势']['下跌趋势'] else '否'}  {result['趋势']['下跌详情']}")
    if result['认购信号']:
        print(f"\n🔴 认购信号: {result['认购信号']['入场描述']}")
    if result['认沽信号']:
        print(f"\n🟢 认沽信号: {result['认沽信号']['入场描述']}")
    if not result['认购信号'] and not result['认沽信号']:
        print("\n😴 无信号")
