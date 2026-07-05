#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
小区间势段信号系统 — Android版 (Kivy)
=====================================
替换 tkinter GUI，支持桌面 + Android 双平台。
桌面测试: python main.py
APK构建: 在 WSL 中运行 buildozer android debug
"""

import threading
from datetime import datetime

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.utils import get_color_from_hex

# ── 引擎 ──
from engine import run_analysis

# ── 颜色 ──
BG      = get_color_from_hex('#0d1117')
CARD_BG = get_color_from_hex('#161b22')
BORDER  = get_color_from_hex('#21262d')
ACCENT  = get_color_from_hex('#58a6ff')
GREEN   = get_color_from_hex('#3fb950')
RED     = get_color_from_hex('#f85149')
ORANGE  = get_color_from_hex('#d29922')
GRAY    = get_color_from_hex('#8b949e')
DARK_TEXT = get_color_from_hex('#c9d1d9')
WHITE   = (1, 1, 1, 1)

# ── 带圆角背景的卡片 ──
class Card(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = dp(12)
        self.spacing = dp(4)
        with self.canvas.before:
            Color(*CARD_BG)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size


# ── 信号条 ──
class SignalBar(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = dp(14)
        self.spacing = dp(6)
        self.size_hint_y = None
        self.active = False
        with self.canvas.before:
            self.bg_color = Color(*CARD_BG)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def set_active(self, sig):
        self.clear_widgets()
        if sig:
            self.bg_color.rgba = (0.85, 0.22, 0.2, 0.15)
            self.active = True
            lbl = Label(
                text=f'[b][color=#f85149]SIGNAL[/color][/b]  {sig["方向"]}',
                markup=True, font_size=dp(22), halign='center',
                color=WHITE, size_hint_y=None, height=dp(36))
            self.add_widget(lbl)
            desc = (
                f'C: {sig["C日期"]}  close={sig["C收盘"]:.0f}  [{sig["C涨跌幅"]:+.2f}%]\n'
                f'D: {sig["D日期"]}  D->C: {sig["D到C跌幅"]:+.2f}%\n'
                f'止盈(TP1)={sig["止盈价"]:.0f}  |  {sig["仓位"]}\n'
                f'M: {sig["M日期"]}  |  {sig["加仓条件"]}'
            )
            lbl2 = Label(text=desc, font_size=dp(13), halign='left',
                         color=get_color_from_hex('#ffc2c2'), size_hint_y=None, height=dp(80))
            self.add_widget(lbl2)
            self.height = dp(130)
        else:
            self.bg_color.rgba = CARD_BG
            self.active = False
            lbl = Label(text='[b]No Signal[/b]', markup=True,
                        font_size=dp(18), halign='center', color=GRAY,
                        size_hint_y=None, height=dp(36))
            self.add_widget(lbl)
            self.height = dp(60)


# ── 主界面 ──
class MainScreen(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = dp(12)
        self.spacing = dp(8)
        self.result = None

        # ── 标题 ──
        title = Label(
            text='[b]Signal Monitor[/b]\n[size=12sp]ChiNext | Call Direction[/size]',
            markup=True, font_size=dp(20), halign='center',
            color=ACCENT, size_hint_y=None, height=dp(55))
        self.add_widget(title)

        # ── 信号条 ──
        self.signal_bar = SignalBar()
        self.add_widget(self.signal_bar)

        # ── 趋势卡片 ──
        self.trend_card = Card(size_hint_y=None, height=dp(70))
        self.trend_label = Label(text='Up Trend: --', font_size=dp(15),
                                 halign='left', color=GRAY, markup=True)
        self.trend_detail = Label(text='', font_size=dp(11), halign='left',
                                  color=GRAY, markup=True)
        self.trend_card.add_widget(self.trend_label)
        self.trend_card.add_widget(self.trend_detail)
        self.add_widget(self.trend_card)

        # ── 辅助信息卡片 ──
        self.info_card = Card(size_hint_y=None, height=dp(110))
        self.info_label = Label(text='Loading...', font_size=dp(12),
                                halign='left', color=GRAY, markup=True)
        self.info_card.add_widget(self.info_label)
        self.add_widget(self.info_card)

        # ── 最近段 ──
        self.seg_card = Card(size_hint_y=None, height=dp(90))
        self.seg_label = Label(text='Recent Segments', font_size=dp(12),
                               halign='left', color=GRAY, markup=True)
        self.seg_card.add_widget(self.seg_label)
        self.add_widget(self.seg_card)

        # ── 按钮 ──
        btn_layout = BoxLayout(orientation='horizontal', spacing=dp(8),
                               size_hint_y=None, height=dp(44))
        btn_refresh = Button(text='REFRESH', background_color=(0.14, 0.53, 0.21, 1),
                             color=WHITE, font_size=dp(14), bold=True)
        btn_refresh.bind(on_press=self.do_refresh)
        btn_layout.add_widget(btn_refresh)
        self.add_widget(btn_layout)

        # ── 底部状态 ──
        self.status = Label(text='', font_size=dp(10), halign='center',
                            color=get_color_from_hex('#484f58'),
                            size_hint_y=None, height=dp(20))
        self.add_widget(self.status)

        # 初始加载
        Clock.schedule_once(lambda dt: self.do_refresh(None), 0.5)

    def do_refresh(self, instance):
        self.status.text = 'Updating...'
        self.signal_bar.clear_widgets()
        self.signal_bar.add_widget(Label(text='Loading...', color=GRAY, font_size=dp(14)))
        threading.Thread(target=self._fetch_data, daemon=True).start()

    def _fetch_data(self):
        try:
            result = run_analysis()
            self.result = result
            Clock.schedule_once(lambda dt: self._update_ui(result), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self._show_error(str(e)), 0)

    def _show_error(self, msg):
        self.status.text = f'Error: {msg[:80]}'
        self.signal_bar.clear_widgets()
        self.signal_bar.add_widget(Label(text=f'Error: {msg[:60]}', color=RED, font_size=dp(12)))

    def _update_ui(self, r):
        trend = r['趋势']
        aux = r['辅助']
        sig = r['认购信号']

        # 信号条
        self.signal_bar.set_active(sig)

        # 趋势
        if trend['上涨趋势']:
            self.trend_label.text = '[b][color=#f85149]UP TREND = YES[/color][/b]'
            self.trend_detail.text = trend.get('上涨详情', '')
        else:
            self.trend_label.text = '[b]UP TREND = NO[/b]'
            self.trend_detail.text = ''

        # 辅助信息
        dc = aux['距上次认购']; dp_ = aux['距上次认沽']
        info_lines = [
            f'Data Date: {r["数据日期"].strftime("%Y-%m-%d")}',
            f'Update: {r["数据更新"]}',
            f'Total Days: {r["总交易日"]}',
            f'Up Segs: {r["涨势段数"]}',
            f'Last Signal: {dc}d ago' if dc is not None else 'Last Signal: --',
        ]
        cp = aux['上次认购盈亏']
        if cp:
            emoji = '+' if cp['收益率'] > 0 else ''
            info_lines.append(f'Last PnL: {emoji}{cp["收益率"]:.1f}% ({cp.get("退出","?")}, {cp["持仓天数"]}d)')
        self.info_label.text = '\n'.join(info_lines)

        # 最近段
        up_seg = r['_up_seg']
        seg_lines = []
        for s in up_seg[-3:]:
            seg_lines.append(f'{s["A日期"].strftime("%m/%d")} -> {s["B日期"].strftime("%m/%d")}  '
                            f'CloseHi={s["区间收盘最高"]:.0f}  Hi={s["区间最高"]:.0f}')
        self.seg_label.text = 'Recent:\n' + '\n'.join(seg_lines) if seg_lines else 'Recent: --'
        self.seg_card.height = dp(50 + max(20, len(seg_lines) * 18))

        self.status.text = f'Updated: {r["数据更新"]}'


# ── App ──
class SignalApp(App):
    def build(self):
        Window.clearcolor = BG
        self.title = 'Seg Signal'
        return MainScreen()


if __name__ == '__main__':
    SignalApp().run()
