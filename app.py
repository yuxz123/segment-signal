#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
小区间势段信号系统 — 手机Web版
================================
在电脑上启动此服务器，手机连同一WiFi即可浏览器访问。
"""

import json, threading, time, os
from datetime import datetime, timedelta
from flask import Flask, render_template_string, jsonify, request

app = Flask(__name__)

# ============================================================
# 引擎逻辑（从 engine.py 移植）
# ============================================================
import pandas as pd
import numpy as np
import requests as req

MAX_SCAN = 200
DATA_CACHE = None
RESULT_CACHE = None
LAST_FETCH = None
FETCH_LOCK = threading.Lock()

def fetch_data(symbol="sz399006"):
    global DATA_CACHE, LAST_FETCH
    with FETCH_LOCK:
        if DATA_CACHE is not None and LAST_FETCH and (datetime.now() - LAST_FETCH).seconds < 300:
            return DATA_CACHE.copy()
        try:
            url = 'https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData'
            params = {'symbol': symbol, 'scale': '240', 'ma': 'no', 'datalen': '5000'}
            r = req.get(url, params=params, timeout=30)
            data = json.loads(r.text)
            if not data: raise RuntimeError('API返回空')
            df = pd.DataFrame(data)
            df['日期'] = pd.to_datetime(df['day'])
            df['指数点'] = df['close'].astype(float)
            df['最高指数点'] = df['high'].astype(float)
            df['最低指数点'] = df['low'].astype(float)
            df = df.sort_values('日期').reset_index(drop=True)
            df['当日涨跌幅%'] = df['指数点'].pct_change() * 100
            df = df.dropna(subset=['当日涨跌幅%']).reset_index(drop=True)
            DATA_CACHE = df.copy()
            LAST_FETCH = datetime.now()
            return df
        except Exception as e:
            if DATA_CACHE is not None:
                return DATA_CACHE.copy()
            raise RuntimeError(f"获取数据失败: {e}")

def identify_uptrend_segments(df):
    n = len(df)
    segments, used = [], set()
    i = 0
    while i < n:
        ret_i = df.loc[i, '当日涨跌幅%']
        if pd.isna(ret_i) or ret_i <= 0:
            i += 1; continue
        A_idx = i; A_close = df.loc[A_idx, '指数点']
        found_B = False
        scan_end = min(A_idx + MAX_SCAN, n - 1)
        for j in range(A_idx + 2, scan_end + 1):
            ret_j = df.loc[j, '当日涨跌幅%']
            if pd.isna(ret_j): continue
            has_down = any(not pd.isna(df.loc[k, '当日涨跌幅%']) and df.loc[k, '当日涨跌幅%'] < 0
                          for k in range(A_idx + 1, j))
            if not has_down: continue
            cond_b = (ret_j < -1.5)
            if not cond_b:
                cum = ret_j; cnt = 1
                for k in range(j - 1, A_idx, -1):
                    rk = df.loc[k, '当日涨跌幅%']
                    if pd.isna(rk) or rk >= 0: break
                    cum += rk; cnt += 1
                    if cum < -1.5: cond_b = True; break
            if not cond_b: continue
            found_B = True
            if df.loc[j, '指数点'] >= A_close * 1.02:
                b1 = min(j + 1, n - 1)
                segments.append({
                    'A_idx': A_idx, 'B_idx': j,
                    'A日期': df.loc[A_idx, '日期'].strftime('%Y-%m-%d'),
                    'B日期': df.loc[j, '日期'].strftime('%Y-%m-%d'),
                    '区间最高': round(df.loc[A_idx:b1 + 1, '最高指数点'].max(), 2) if b1 + 1 < n else round(df.loc[A_idx:b1, '最高指数点'].max(), 2),
                    '区间收盘最高': round(df.loc[A_idx:b1 + 1, '指数点'].max(), 2) if b1 + 1 < n else round(df.loc[A_idx:b1, '指数点'].max(), 2),
                    '区间最低': round(df.loc[A_idx:b1 + 1, '最低指数点'].min(), 2) if b1 + 1 < n else round(df.loc[A_idx:b1, '最低指数点'].min(), 2),
                    '区间收盘最低': round(df.loc[A_idx:b1 + 1, '指数点'].min(), 2) if b1 + 1 < n else round(df.loc[A_idx:b1, '指数点'].min(), 2),
                    '方向': '涨', '类型': '主段',
                })
                for x in range(A_idx, j + 1): used.add(x)
            i = j; break
        if not found_B: i += 1

    # 增补段
    unused = sorted(set(range(n)) - used)
    if unused:
        runs = []; start = unused[0]; prev = unused[0]
        for x in unused[1:]:
            if x == prev + 1: prev = x
            else: runs.append((start, prev)); start = x; prev = x
        runs.append((start, prev))
        for s, e in runs:
            if e - s + 1 < 4: continue
            for a in range(s, e - 2):
                for b in range(a + 3, e + 1):
                    returns = [df.loc[k, '当日涨跌幅%'] for k in range(a, b + 1)]
                    if all(not pd.isna(r) and r >= -0.25 for r in returns):
                        cum = sum(r for r in returns if not pd.isna(r))
                        if cum > 3:
                            b1p = min(b + 1, n - 1)
                            segments.append({
                                'A_idx': a, 'B_idx': b,
                                'A日期': df.loc[a, '日期'].strftime('%Y-%m-%d'),
                                'B日期': df.loc[b, '日期'].strftime('%Y-%m-%d'),
                                '区间最高': round(df.loc[a:b1p + 1, '最高指数点'].max(), 2) if b1p + 1 < n else round(df.loc[a:b1p, '最高指数点'].max(), 2),
                                '区间收盘最高': round(df.loc[a:b1p + 1, '指数点'].max(), 2) if b1p + 1 < n else round(df.loc[a:b1p, '指数点'].max(), 2),
                                '区间最低': round(df.loc[a:b1p + 1, '最低指数点'].min(), 2) if b1p + 1 < n else round(df.loc[a:b1p, '最低指数点'].min(), 2),
                                '区间收盘最低': round(df.loc[a:b1p + 1, '指数点'].min(), 2) if b1p + 1 < n else round(df.loc[a:b1p, '指数点'].min(), 2),
                                '方向': '涨', '类型': '增补',
                            })
                            for x in range(a, b + 1): used.add(x)
                            break
    segments.sort(key=lambda s: s['A_idx'])
    return segments

def scan_call_signal(df, up_segments):
    n = len(df)
    seg_df = pd.DataFrame(up_segments) if up_segments else pd.DataFrame()
    if len(seg_df) < 2:
        return None
    c_idx = n - 1
    segs_before = seg_df[seg_df['B_idx'] <= c_idx].sort_values('B_idx')
    if len(segs_before) < 2:
        return None
    seg1 = segs_before.iloc[-1]; seg2 = segs_before.iloc[-2]
    if seg1['区间收盘最高'] <= seg2['区间最高']:
        return None
    C_return = df.loc[c_idx, '当日涨跌幅%']
    if pd.isna(C_return) or C_return >= 0:
        return None
    seg1_B = int(seg1['B_idx'])
    has_down = any(not pd.isna(df.loc[k, '当日涨跌幅%']) and df.loc[k, '当日涨跌幅%'] < 0
                  for k in range(seg1_B + 1, c_idx + 1))
    if not has_down: return None
    D_idx = None; D_close = None
    for k in range(c_idx - 1, 0, -1):
        r = df.loc[k, '当日涨跌幅%']
        if not pd.isna(r) and r >= 1.5: D_idx = k; D_close = df.loc[k, '指数点']; break
    if D_idx is None: return None
    C_close = df.loc[c_idx, '指数点']
    drop = (C_close - D_close) / D_close * 100
    if drop >= -3.0: return None
    C_date = df.loc[c_idx, '日期']; M_date = C_date + timedelta(days=1)
    while M_date.weekday() >= 5: M_date += timedelta(days=1)
    return {
        '方向': '认购(做多)',
        'M日期': M_date.strftime('%Y-%m-%d'),
        'C日期': C_date.strftime('%Y-%m-%d'),
        'C收盘': round(C_close, 2),
        'C涨跌幅': round(C_return, 2),
        'D日期': df.loc[D_idx, '日期'].strftime('%Y-%m-%d'),
        'D到C跌幅': round(drop, 2),
        '止盈价': round(C_close * 1.04, 2),
        '加仓条件': 'M日涨跌<0 且 M+1日涨跌<0 → M+1收盘加仓50%',
        '仓位': '50%头寸',
    }

def scan_put_signal(df, down_segments):
    # 这里只做认购方向，与原系统一致的结构
    return None

def run_analysis():
    global RESULT_CACHE
    df = fetch_data()
    n = len(df)
    up_seg = identify_uptrend_segments(df)
    call_sig = scan_call_signal(df, up_seg)

    # 趋势判断
    trend_up = False; trend_detail = ''
    if len(up_seg) >= 2:
        s1, s2 = up_seg[-1], up_seg[-2]
        if s1['区间收盘最高'] > s2['区间最高']:
            trend_up = True
            trend_detail = f"段{s1['A日期']}→{s1['B日期']}收盘最高{s1['区间收盘最高']:.0f} > 前段最高{s2['区间最高']:.0f}"

    last_date = df.loc[n - 1, '日期']

    # 距上次信号
    all_sigs = []
    seg_df = pd.DataFrame(up_seg)
    if len(seg_df) >= 2:
        for m_idx in range(3, n):
            c_idx = m_idx - 1
            sb = seg_df[seg_df['B_idx'] < m_idx].sort_values('B_idx')
            if len(sb) < 2: continue
            s1, s2 = sb.iloc[-1], sb.iloc[-2]
            if s1['区间收盘最高'] <= s2['区间最高']: continue
            cr = df.loc[c_idx, '当日涨跌幅%']
            if pd.isna(cr) or cr >= 0: continue
            if not any(not pd.isna(df.loc[k, '当日涨跌幅%']) and df.loc[k, '当日涨跌幅%'] < 0
                      for k in range(int(s1['B_idx']) + 1, c_idx + 1)): continue
            D_idx = None
            for k in range(c_idx - 1, 0, -1):
                r = df.loc[k, '当日涨跌幅%']
                if not pd.isna(r) and r >= 1.5: D_idx = k; break
            if D_idx is None: continue
            cc = df.loc[c_idx, '指数点']; dc = df.loc[D_idx, '指数点']
            if (cc - dc) / dc * 100 >= -3.0: continue
            all_sigs.append({'M_idx': m_idx, 'M日期': df.loc[m_idx, '日期'], 'C收盘': cc})
    all_sigs.sort(key=lambda x: x['M_idx'])

    days_since = None
    last_sig = all_sigs[-1] if all_sigs else None
    if last_sig:
        days_since = (last_date - last_sig['M日期']).days

    # 模拟最近完结信号盈亏
    last_pnl = None
    for s in reversed(all_sigs):
        m_idx = s['M_idx']; C_close = s['C收盘']
        max_hold = min(m_idx + 10, n - 1)
        if max_hold >= n - 1: continue
        tp1_f = False; tp1_p = None; tp2_f = False; tp2_p = None
        time_s = False; stop_f = False; peak = None; crash_days = set()
        c_low = df.loc[m_idx - 1, '最低指数点']
        m_low = df.loc[m_idx, '最低指数点']
        stop_th = min(c_low, m_low) * 0.96
        for day in range(m_idx, max_hold + 1):
            dc = df.loc[day, '指数点']; dr = df.loc[day, '当日涨跌幅%']
            if not pd.isna(dr) and dr > 2.0: crash_days.add(day)
            if not tp1_f and not stop_f and day == min(m_idx + 9, n - 1):
                if dc < C_close: time_s = True; tp1_f = True; tp1_p = dc; break
            if not tp1_f and dc > C_close * 1.04:
                tp1_f = True; tp1_p = dc; peak = dc
            if tp1_f and not tp2_f and not stop_f:
                if dc > peak: peak = dc
                if (not pd.isna(dr) and dr < -0.5) or dc < peak * 0.98:
                    tp2_f = True; tp2_p = dc; break
            if not stop_f and not tp2_f and not time_s:
                if len(crash_days) > 0 and day >= m_idx + 2 and dc < stop_th:
                    stop_f = True; break
        if not tp1_f and not stop_f: tp1_p = df.loc[max_hold, '指数点']
        elif tp1_f and not tp2_f and not stop_f: tp2_p = df.loc[max_hold, '指数点']
        entry_p = C_close
        if stop_f:
            pnl = -50.0
            exit_lbl = '硬止损'
        elif time_s:
            pnl = (tp1_p / entry_p - 1) * 100
            exit_lbl = f'时间止损'
        elif tp2_f:
            if tp1_f:
                pnl = ((tp1_p / entry_p - 1) * 0.5 + (tp2_p / entry_p - 1) * 0.5) * 100
            else:
                pnl = (tp2_p / entry_p - 1) * 100
            exit_lbl = 'TP2' if tp2_f else '到期'
        else:
            pnl = (tp1_p / entry_p - 1) * 100
            exit_lbl = '到期'
        held_days = (day if tp2_f or stop_f or time_s else max_hold) - m_idx + 1
        last_pnl = {'收益率': round(pnl, 1), '退出': exit_lbl, '持仓天数': held_days,
                     'M日期': df.loc[m_idx, '日期'].strftime('%Y-%m-%d')}
        break

    RESULT_CACHE = {
        '更新时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        '数据日期': last_date.strftime('%Y-%m-%d'),
        '交易日数': n,
        '涨势段数': len(up_seg),
        '上涨趋势': trend_up,
        '趋势详情': trend_detail,
        '认购信号': call_sig,
        '距上次信号': days_since,
        '上次盈亏': last_pnl,
        '最新段': up_seg[-3:] if up_seg else [],
    }
    return RESULT_CACHE


# ============================================================
# HTML 模板（移动端适配）
# ============================================================
HTML_TEMPLATE = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<title>小区间势段信号</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,'Microsoft YaHei',sans-serif;background:#0d1117;color:#c9d1d9;
     min-height:100vh;padding:12px;max-width:500px;margin:0 auto}
.header{text-align:center;padding:12px 0 8px}
.header h1{font-size:20px;color:#58a6ff}
.header .sub{font-size:11px;color:#8b949e;margin-top:2px}
.card{background:#161b22;border:1px solid #21262d;border-radius:8px;padding:14px;margin:10px 0}
.card-title{font-size:12px;color:#8b949e;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px}

/* 信号条 */
.signal-bar{padding:14px;border-radius:8px;margin:10px 0;text-align:center}
.signal-bar.active{background:linear-gradient(135deg,#da3633,#f85149)}
.signal-bar.rest{background:#161b22;border:1px solid #21262d}
.signal-bar .dir{font-size:22px;font-weight:700;color:#fff}
.signal-bar.rest .dir{font-size:18px;color:#484f58}
.signal-bar .desc{font-size:13px;color:#ffc2c2;margin-top:6px;line-height:1.5}
.signal-bar.rest .desc{color:#484f58}

/* 趋势卡片 */
.trend-row{display:flex;align-items:center;gap:8px;padding:6px 0}
.trend-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}
.trend-dot.up{background:#f85149}
.trend-dot.neutral{background:#484f58}
.trend-label{font-size:15px}

/* 表格 */
table{width:100%;font-size:12px;border-collapse:collapse}
th{text-align:left;color:#8b949e;font-weight:400;padding:6px 4px;border-bottom:1px solid #21262d}
td{padding:6px 4px;border-bottom:1px solid #21262d}
.val-up{color:#3fb950}.val-down{color:#f85149}.val-neutral{color:#c9d1d9}

/* 数据行 */
.data-row{display:flex;justify-content:space-between;padding:5px 0;font-size:13px;border-bottom:1px solid #21262d}
.data-row:last-child{border-bottom:none}
.data-row .lbl{color:#8b949e}
.data-row .val{font-weight:600}

.btn{display:block;width:100%;padding:12px;border:none;border-radius:8px;font-size:15px;
     font-weight:600;cursor:pointer;margin:10px 0;text-align:center;background:#238636;color:#fff}
.btn:active{background:#2ea043}
.btn-secondary{background:#21262d;color:#c9d1d9}

.footer{text-align:center;font-size:10px;color:#484f58;padding:16px 0}

.loading{text-align:center;padding:40px 0;color:#8b949e}
.spinner{display:inline-block;width:24px;height:24px;border:2px solid #30363d;border-top:2px solid #58a6ff;
         border-radius:50%;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
</style>
</head>
<body>

<div class="header">
  <h1>📊 小区间势段信号</h1>
  <div class="sub">创业板 · 认购(做多)方向</div>
</div>

<div id="content">
  <div class="loading">
    <div class="spinner"></div>
    <p style="margin-top:10px">正在获取数据...</p>
  </div>
</div>

<button class="btn" onclick="refresh()">🔄 刷新数据</button>
<button class="btn btn-secondary" onclick="window.location.reload()">📋 查看操作清单</button>

<div class="footer">
  <div>数据来源: 新浪财经 · 创业板指 sz399006</div>
  <div>更新时间: <span id="updateTime">--</span></div>
</div>

<script>
async function refresh(){
  document.getElementById('content').innerHTML = '<div class="loading"><div class="spinner"></div><p>正在获取...</p></div>';
  await loadData();
}
async function loadData(){
  try{
    const r = await fetch('/api/data');
    const d = await r.json();
    if(d.error){document.getElementById('content').innerHTML=`<div class="card"><p style="color:#f85149">❌ ${d.error}</p></div>`;return}
    document.getElementById('updateTime').textContent = d.更新时间;

    let html = '';

    // 信号条
    if(d.认购信号){
      const s = d.认购信号;
      html += `<div class="signal-bar active">
        <div class="dir">🔴 ${s.方向}信号触发！</div>
        <div class="desc">
          C日: ${s.C日期} | 收盘 ${s.C收盘} | 涨跌 ${s.C涨跌幅}%<br>
          D日: ${s.D日期} | D→C跌幅 ${s.D到C跌幅}%<br>
          止盈价: ${s.止盈价} | M日: ${s.M日期}<br>
          ${s.仓位} | ${s.加仓条件}
        </div>
      </div>`;
    } else {
      html += `<div class="signal-bar rest"><div class="dir">😴 暂无信号</div>`;
      if(d.上涨趋势) html += `<div class="desc">趋势成立但条件2未满足</div>`;
      else html += `<div class="desc">上涨趋势不成立</div>`;
      html += `</div>`;
    }

    // 趋势
    html += `<div class="card"><div class="card-title">📈 趋势判断</div>`;
    html += `<div class="trend-row"><div class="trend-dot ${d.上涨趋势?'up':'neutral'}"></div>
             <span class="trend-label">上涨趋势: <b>${d.上涨趋势?'是':'否'}</b></span></div>`;
    if(d.趋势详情) html += `<div style="font-size:11px;color:#8b949e;margin-top:4px">${d.趋势详情}</div>`;
    html += `</div>`;

    // 辅助信息
    html += `<div class="card"><div class="card-title">ℹ 辅助信息</div>`;
    html += `<div class="data-row"><span class="lbl">数据截止</span><span class="val">${d.数据日期}</span></div>`;
    html += `<div class="data-row"><span class="lbl">交易日数</span><span class="val">${d.交易日数}</span></div>`;
    html += `<div class="data-row"><span class="lbl">涨势段数</span><span class="val">${d.涨势段数}</span></div>`;
    html += `<div class="data-row"><span class="lbl">距上次信号</span><span class="val">${d.距上次信号!=null?d.距上次信号+'天':'--'}</span></div>`;
    if(d.上次盈亏){
      const p = d.上次盈亏;
      const cls = p.收益率>0?'val-up':'val-down';
      html += `<div class="data-row"><span class="lbl">上次信号盈亏</span><span class="val ${cls}">
        ${p.收益率>0?'+':''}${p.收益率}%（${p.退出},${p.持仓天数}天）</span></div>`;
    }
    html += `</div>`;

    // 最新段
    if(d.最新段 && d.最新段.length>0){
      html += `<div class="card"><div class="card-title">📋 最近的涨势段</div>`;
      html += `<table><tr><th>开始日</th><th>结束日</th><th>收盘最高</th><th>最高</th><th>类型</th></tr>`;
      for(const seg of d.最新段.reverse()){
        html += `<tr><td>${seg.A日期}</td><td>${seg.B日期}</td>
          <td class="val-up">${seg.区间收盘最高}</td><td>${seg.区间最高}</td>
          <td style="font-size:10px;color:#8b949e">${seg.类型}</td></tr>`;
      }
      html += `</table></div>`;
    }

    document.getElementById('content').innerHTML = html;
  }catch(e){
    document.getElementById('content').innerHTML = `<div class="card"><p style="color:#f85149">❌ 加载失败: ${e.message}</p></div>`;
  }
}
loadData();
</script>
</body>
</html>'''


# ============================================================
# Flask 路由
# ============================================================
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/data')
def api_data():
    try:
        result = run_analysis()
        # 把numpy类型转成原生Python
        def convert(obj):
            if isinstance(obj, (np.integer,)): return int(obj)
            if isinstance(obj, (np.floating,)): return float(obj)
            if isinstance(obj, np.ndarray): return obj.tolist()
            if isinstance(obj, dict): return {k: convert(v) for k, v in obj.items()}
            if isinstance(obj, list): return [convert(v) for v in obj]
            return obj
        return jsonify(convert(result))
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/checklist')
def checklist():
    try:
        result = RESULT_CACHE or run_analysis()
        sig = result.get('认购信号')
        if not sig:
            return jsonify({'error': '当前无信号'})
        lines = []
        lines.append("╔══════════════════════════════╗")
        lines.append("║      📋 完整操作清单          ║")
        lines.append("╚══════════════════════════════╝")
        lines.append("")
        lines.append(f"策略: {sig['方向']}  |  仓位: {sig['仓位']}")
        lines.append(f"C日: {sig['C日期']}  |  M日: {sig['M日期']}")
        lines.append("")
        lines.append("━━━ 关键价位 ━━━")
        lines.append(f"C日收盘(基准): {sig['C收盘']:.2f}")
        lines.append(f"止盈价(TP1):   {sig['止盈价']:.2f}")
        lines.append(f"D→C跌幅: {sig['D到C跌幅']:+.2f}%")
        lines.append("")
        lines.append("━━━ 操作步骤 ━━━")
        lines.append(f"1. 明日({sig['M日期']})盘中，在低于{sig['C收盘']:.0f}的日内低点买入ETF/认购期权，50%仓位")
        lines.append(f"2. 止盈1: 收盘 > {sig['C收盘']*1.04:.0f} 时平一半")
        lines.append(f"3. 止盈2: 剩余在日跌>0.5%或从高点回落2%时清仓")
        lines.append(f"4. 时间止损: 第9个交易日收盘未触发止盈1 → 全平")
        lines.append(f"5. 最晚持有至 M+10个交易日")
        lines.append("")
        lines.append("━━━ 风控提示 ━━━")
        lines.append("• 每笔固定金额，独立资金池")
        lines.append("• 第9个交易日收盘未触发止盈1 → 时间止损全平")
        lines.append("• 止盈1触发后 → 移动止盈(日反向0.5%或2%回撤)")
        lines.append("• 单笔亏损>30% → 暂停3个交易日")
        return jsonify({'text': '\n'.join(lines)})
    except Exception as e:
        return jsonify({'error': str(e)})


# ============================================================
# 启动
# ============================================================
def get_local_ip():
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return '127.0.0.1'

if __name__ == '__main__':
    ip = get_local_ip()
    port = 5000
    print("=" * 55)
    print("   [小区间势段信号系统] 手机Web版")
    print("=" * 55)
    print()
    print("   [OK] 服务器已启动!")
    print()
    print("   [手机] 浏览器打开 (需连同一WiFi):")
    print(f"     http://{ip}:{port}")
    print()
    print("   [电脑] 本机浏览器打开:")
    print(f"     http://127.0.0.1:{port}")
    print()
    print("   按 Ctrl+C 停止服务器")
    print("=" * 55)
    app.run(host='0.0.0.0', port=port, debug=False)
