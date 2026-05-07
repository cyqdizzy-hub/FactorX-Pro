import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import hashlib
import akshare as ak
from datetime import datetime
import os
import base64
from supabase import create_client, Client

# --- 页面设置 (极宽布局) ---
st.set_page_config(page_title="FactorX Pro (数据直连版)", page_icon="🛰️", layout="wide", initial_sidebar_state="expanded")

# ==========================================
#        🎨 深度 UI 美化与 Logo
# ==========================================
def inject_custom_css():
    st.markdown("""
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {background-color: transparent !important;}
        [data-testid="stAppDeployButton"] {display: none;}
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        div[data-testid="metric-container"] {
            background-color: rgba(130, 130, 130, 0.05); border: 1px solid rgba(130, 130, 130, 0.2);
            padding: 15px 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
        }
        div[data-testid="metric-container"]:hover { transform: translateY(-2px); box-shadow: 0 8px 15px rgba(0,0,0,0.1); }
        .stButton > button { border-radius: 8px; font-weight: 600; transition: all 0.3s ease; }
        .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 5px 10px rgba(0,0,0,0.15); }
        .news-link { text-decoration: none; color: #1E88E5; font-weight: 500; transition: color 0.2s; }
        .news-link:hover { text-decoration: underline; color: #0D47A1; }
        .report-btn { display: inline-block; padding: 10px 15px; margin-top: 10px; background-color: #f0f2f6; color: #31333F; border-radius: 8px; text-decoration: none; font-weight: 600; border: 1px solid #dcdcdc; transition: all 0.2s; }
        .report-btn:hover { background-color: #e0e2e6; color: #1E88E5; border-color: #1E88E5; }
        </style>
    """, unsafe_allow_html=True)

inject_custom_css()

def render_logo(width=80, center=False):
    if os.path.exists("icon.png"):
        if center:
            with open("icon.png", "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode()
            html_code = f"""<div style="display: flex; justify-content: center; margin-bottom: 15px;"><img src="data:image/png;base64,{encoded_string}" style="width: {width}px; height: {width}px; border-radius: 20px; box-shadow: 0 8px 16px rgba(0,0,0,0.3);"></div>"""
            st.markdown(html_code, unsafe_allow_html=True)
        else:
            st.image("icon.png", width=width)
    else:
        if center: st.markdown("<h1 style='text-align: center;'>🛰️ Pro</h1>", unsafe_allow_html=True)

# ==========================================
#        0. 云端数据库连接 (Supabase + JSONBIN)
# ==========================================
# 用户管理依然走 JSONBIN
API_KEY = st.secrets.get("JSONBIN_KEY", "")
BIN_ID = st.secrets.get("JSONBIN_ID", "")
URL = f"https://api.jsonbin.io/v3/b/{BIN_ID}"
HEADERS = {"X-Master-Key": API_KEY, "Content-Type": "application/json"}

# 核心行情数据走 Supabase
SUPA_URL = st.secrets.get("SUPABASE_URL", "")
SUPA_KEY = st.secrets.get("SUPABASE_KEY", "")
supabase: Client = None
if SUPA_URL and SUPA_KEY:
    try:
        supabase = create_client(SUPA_URL, SUPA_KEY)
    except Exception:
        pass

def hash_password(password): return hashlib.sha256(password.encode()).hexdigest()

def load_all_cloud_data():
    try:
        response = requests.get(URL, headers=HEADERS)
        data = response.json().get("record", {})
        if "users" not in data: data["users"] = {}
        if "watchlists" not in data: data["watchlists"] = {}
        return data
    except Exception: return {"users": {}, "watchlists": {}}

def save_to_cloud(all_data):
    try: requests.put(URL, json=all_data, headers=HEADERS)
    except Exception as e: st.error(f"⚠️ 同步失败: {e}")

def get_category(symbol):
    symbol = str(symbol).strip().upper()
    if symbol.endswith(".SZ") or symbol.endswith(".SS"): return "📊 国内 ETF" if symbol.startswith("15") or symbol.startswith("51") else "🇨🇳 A股个股"
    elif symbol.endswith(".HK"): return "🇭🇰 港股"
    elif symbol.isalpha(): return "🇺🇸 美股"
    else: return "🌍 其他标的"

# ==========================================
#        1. 登录与侧边栏
# ==========================================
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'current_user' not in st.session_state: st.session_state.current_user = ""

if not st.session_state.logged_in:
    spacer1, login_col, spacer3 = st.columns([1, 1.5, 1])
    with login_col:
        st.write("<br><br>", unsafe_allow_html=True)
        render_logo(width=100, center=True)
        st.markdown("<h2 style='text-align: center; margin-bottom: 20px;'>FactorX Pro 核心直连版</h2>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            login_user = st.text_input("终端标识 (用户名)")
            login_pwd = st.text_input("安全密钥 (密码)", type="password")
            if st.form_submit_button("机构通道接入", type="primary", use_container_width=True):
                db = load_all_cloud_data()
                if login_user in db["users"] and db["users"][login_user] == hash_password(login_pwd):
                    st.session_state.logged_in, st.session_state.current_user = True, login_user
                    st.rerun()
                else: st.error("❌ 密钥校验失败。")
    st.stop()

render_logo(width=60, center=False)
st.sidebar.title(f"👋 {st.session_state.current_user}")
st.sidebar.caption("FactorX Pro Data-Link Active 🟢")
if st.sidebar.button("🚪 断开连接", use_container_width=True):
    st.session_state.logged_in, st.session_state.current_user = False, ""
    st.rerun()
st.sidebar.divider()

if 'watchlist' not in st.session_state or st.session_state.get('last_user') != st.session_state.current_user:
    all_users_data = load_all_cloud_data()
    st.session_state.watchlist = all_users_data["watchlists"].get(st.session_state.current_user, {})
    st.session_state.last_user = st.session_state.current_user
    st.session_state.sidebar_select = ""

for key in ['current_price', 'df_history', 'fundamentals', 'data_source', 'news_data', 'macro_news', 'report_link']:
    if key not in st.session_state: st.session_state[key] = None if key != 'df_history' else pd.DataFrame()

if st.sidebar.button("➕ 载入新监测标的", type="primary" if st.session_state.sidebar_select == "" else "secondary", use_container_width=True):
    st.session_state.sidebar_select = ""
    st.rerun()
st.sidebar.divider()

categories_dict = {}
for sym, data in st.session_state.watchlist.items(): categories_dict.setdefault(data.get('category', '🌍 其他标的'), []).append((sym, data))
for cat, items in categories_dict.items():
    st.sidebar.caption(f"**{cat}**") 
    for sym, data in items:
        col1, col2 = st.sidebar.columns([4, 1])
        if col1.button(f"{data.get('name', '')} ({sym})" if data.get('name', '') else f"📊 {sym}", key=f"sel_{sym}", type="primary" if st.session_state.sidebar_select == sym else "secondary", use_container_width=True):
            st.session_state.sidebar_select = sym
            st.rerun()
        if col2.button("🗑️", key=f"del_{sym}"):
            del st.session_state.watchlist[sym]
            db = load_all_cloud_data()
            db["watchlists"][st.session_state.current_user] = st.session_state.watchlist
            save_to_cloud(db)
            st.rerun()

default_sym = st.session_state.sidebar_select if st.session_state.sidebar_select else "TSM"
default_data = st.session_state.watchlist.get(default_sym, {})
default_name, default_cost, default_qty = default_data.get('name', ''), float(default_data.get('cost', 0.0)), int(default_data.get('qty', 0))

# ==========================================
#        3. Pro 版数据中枢 (数据库直连优先)
# ==========================================
@st.cache_data(ttl=300, show_spinner=False)
def fetch_multi_factor_data(symbol):
    df = pd.DataFrame()
    fund_data = {"PE": None, "ROE": None, "52w_Change": None}
    source_name = "未获取"
    news_list, macro_list = [], []
    report_url = ""
    
    symbol = str(symbol).strip().upper()
    is_a_share = symbol.endswith(".SZ") or symbol.endswith(".SS")
    base_code = symbol.split('.')[0] 
    report_url = f"https://so.eastmoney.com/Yanbao/s?keyword={base_code}" if is_a_share else f"https://seekingalpha.com/symbol/{base_code}"

    # 1. 获取宏观快讯
    try:
        cls_df = ak.stock_zh_a_alerts_cls()
        if not cls_df.empty:
            for idx, row in cls_df.head(6).iterrows():
                if len(str(row.get('内容', ''))) > 15: macro_list.append({"time": str(row.get('时间', ''))[-8:], "content": str(row.get('内容', ''))[:80] + "..."})
    except Exception: pass

    # 💥 2. 【Pro 版核心】优先从 Supabase 数据库拉取 iFinD 数据
    if supabase is not None:
        try:
            res = supabase.table("factorx_data").select("*").eq("symbol", symbol).order("date", desc=True).limit(250).execute()
            if res.data and len(res.data) > 20:
                df = pd.DataFrame(res.data)
                df['Date'] = pd.to_datetime(df['date'])
                df.set_index('Date', inplace=True)
                df = df.sort_index() # 确保时间正序
                df.rename(columns={'open':'Open', 'high':'High', 'low':'Low', 'close':'Close', 'volume':'Volume'}, inplace=True)
                source_name = "FactorX 专有云库 (iFinD 机构直连 ⚡)"
        except Exception as e: print(f"Supabase读取失败: {e}")

    # 3. 如果数据库没有，降级使用爬虫引擎 (Yahoo / AKShare)兜底
    if df.empty:
        try:
            session = requests.Session()
            retry = Retry(connect=3, backoff_factor=0.5)
            adapter = HTTPAdapter(max_retries=retry)
            session.mount('http://', adapter)
            session.mount('https://', adapter)
            session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/115.0.0.0"})
            
            yf_df = yf.download(symbol, period="1y", session=session, timeout=4, progress=False) 
            if yf_df is not None and not yf_df.empty and len(yf_df) > 20:
                if isinstance(yf_df.columns, pd.MultiIndex): yf_df.columns = yf_df.columns.get_level_values(0)
                df, source_name = yf_df, "Yahoo Global API (降级爬取)"
                info = yf.Ticker(symbol, session=session).info
                fund_data = {"PE": info.get('trailingPE', info.get('forwardPE')), "ROE": info.get('returnOnEquity'), "52w_Change": info.get('52WeekChange')}
        except Exception: pass

        if df.empty:
            try:
                ak_df = ak.stock_zh_a_hist(symbol=base_code, period="daily", adjust="qfq") if is_a_share else ak.stock_us_hist(symbol=base_code, period="daily", adjust="qfq")
                if not ak_df.empty:
                    ak_df.rename(columns={'日期':'Date', '开盘':'Open', '收盘':'Close', '最高':'High', '最低':'Low', '成交量':'Volume'}, inplace=True)
                    ak_df.index = pd.to_datetime(ak_df['Date'])
                    df, source_name = ak_df.tail(250), "AKShare 镜像库 (降级爬取)"
            except Exception: pass

    # 新闻兜底
    if is_a_share:
        try:
            ak_news = ak.stock_news_em(symbol=base_code)
            if not ak_news.empty: news_list = [{"title": r.get('新闻标题'), "link": r.get('新闻链接', '#'), "publisher": r.get('文章来源'), "time": r.get('发布时间', '')[-14:-3]} for i, r in ak_news.head(6).iterrows()]
        except Exception: pass

    if df.empty: return None, {}, "查无数据！请确保本地打通了 iFinD 数据库同步，或标的代码正确。", "", [], [], ""

    # --- 💥 4. 高阶量化因子计算 (V2.0 增强) ---
    try:
        df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
        df['High'] = pd.to_numeric(df['High'], errors='coerce')
        df['Low'] = pd.to_numeric(df['Low'], errors='coerce')
        df['Volume'] = pd.to_numeric(df['Volume'], errors='coerce')

        df['MA20'], df['MA60'] = df['Close'].rolling(20).mean(), df['Close'].rolling(60).mean()
        df['MACD'] = df['Close'].ewm(span=12).mean() - df['Close'].ewm(span=26).mean()
        
        # RSI
        delta = df['Close'].diff()
        rs = (delta.where(delta > 0, 0)).rolling(14).mean() / (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + rs))

        # 布林带 (BBands)
        df['BB_Std'] = df['Close'].rolling(20).std()
        df['BB_Up'] = df['MA20'] + 2 * df['BB_Std']
        df['BB_Low'] = df['MA20'] - 2 * df['BB_Std']

        # ATR (真实波幅)
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        df['ATR'] = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1).rolling(14).mean()

        # OBV (能量潮)
        df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
        df['OBV_MA'] = df['OBV'].rolling(20).mean()

        return df.iloc[-126:], fund_data, "成功", source_name, news_list, macro_list, report_url
    except Exception as e: return None, {}, f"指标计算错误: {e}", "", [], [], ""

def plot_candlestick(df, symbol, name):
    title = f"{name} ({symbol}) - Pro 级多维量化图表" if name else f"{symbol} - Pro 级多维量化图表"
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_width=[0.2, 0.8])
    
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K线'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='MA20', line=dict(color='#ffca28', width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], name='MA60', line=dict(color='#2196f3', width=1.5)), row=1, col=1)
    
    # 画布林带轨道
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_Up'], name='布林上轨', line=dict(color='rgba(200, 200, 200, 0.5)', width=1, dash='dot')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_Low'], name='布林下轨', line=dict(color='rgba(200, 200, 200, 0.5)', width=1, dash='dot'), fill='tonexty', fillcolor='rgba(200, 200, 200, 0.05)'), row=1, col=1)
    
    colors = ['#ef5350' if row['Open'] > row['Close'] else '#26a69a' for index, row in df.iterrows()]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='成交量', marker_color=colors), row=2, col=1)
    
    fig.update_layout(title=title, xaxis_rangeslider_visible=False, height=550, margin=dict(l=10, r=10, t=40, b=10), showlegend=False, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    return fig

# ==========================================
#        4. UI 展示与高阶诊断
# ==========================================
st.title("🛰️ FactorX Pro 机构指挥舱")
ui_key = default_sym if default_sym else "new_entry"

with st.container():
    c1, c2, c3, c4, c5 = st.columns([1.2, 1.2, 1, 1, 1.2])
    with c1: input_symbol = st.text_input("代码", value=default_sym, key=f"sym_{ui_key}", help="深市:.SZ, 沪市:.SS, 美股直接输")
    with c2: input_name = st.text_input("名称", value=default_name, key=f"name_{ui_key}")
    with c3: input_cost = st.number_input("底仓成本", value=default_cost, step=0.01, key=f"cost_{ui_key}")
    with c4: input_qty = st.number_input("持仓数量", value=default_qty, step=100, key=f"qty_{ui_key}")
    with c5:
        st.write("") 
        if st.button("🔄 启动 Pro 多维扫描", type="primary", use_container_width=True):
            if input_symbol:
                with st.spinner(f'FactorX 引擎正在接入机构底层库...'):
                    df_h, funds, msg, source, news, macro, report = fetch_multi_factor_data(input_symbol)
                    if df_h is not None:
                        st.session_state.df_history = df_h
                        st.session_state.current_price = float(df_h.iloc[-1]['Close'])
                        st.session_state.fundamentals = funds
                        st.session_state.data_source = source
                        st.session_state.news_data = news 
                        st.session_state.macro_news = macro
                        st.session_state.report_link = report
                    else: st.error(f"❌ {msg}")

if st.button("💾 将标的写入 FactorX 云端矩阵"):
    if input_symbol:
        st.session_state.watchlist[input_symbol] = {"name": input_name, "cost": input_cost, "qty": input_qty, "category": get_category(input_symbol)}
        db = load_all_cloud_data()
        db["watchlists"][st.session_state.current_user] = st.session_state.watchlist
        save_to_cloud(db)
        st.session_state.sidebar_select = input_symbol 
        st.rerun() 

st.divider()

if not st.session_state.df_history.empty and st.session_state.current_price > 0:
    st.caption(f"**📡 FactorX Data-Link：** 已接驳 `{st.session_state.data_source}`")
    
    col_chart, col_risk = st.columns([2.2, 1], gap="large")
    with col_chart: st.plotly_chart(plot_candlestick(st.session_state.df_history, input_symbol, input_name), use_container_width=True)
    with col_risk:
        st.subheader("🛡️ 极限风控推演")
        current_p = st.session_state.current_price
        atr = st.session_state.df_history.iloc[-1]['ATR']
        st.metric("最新现价", f"¥ {current_p:.3f}")
        
        # 结合 ATR 的智能止损提示
        st.info(f"**📉 机器建议防守线：** \n基于近14日真实波幅(ATR={atr:.2f})计算，科学止损位应设在 **{current_p - atr*1.5:.2f}** 之下，以过滤庄家日常洗盘震荡。")
        
        qty_add = st.slider("计划加仓推演", min_value=0, max_value=int(max(input_qty * 2, 1000)), value=0, step=100, key=f"slider_{ui_key}")
        total_qty = input_qty + qty_add
        new_cost = ((input_cost * input_qty) + (current_p * qty_add)) / total_qty if total_qty > 0 else input_cost
        safe_cushion = ((current_p - new_cost) / current_p) * 100 if current_p > 0 and total_qty > 0 else 0
        
        st.metric("新保本点", f"{new_cost:.3f}", f"成本变化 {new_cost-input_cost:.3f}" if qty_add>0 else None, delta_color="inverse")
        st.metric("安全垫", f"{safe_cushion:.2f}%")

    st.markdown("<br>### 📊 深度量化体检报告 (V2.0增强版)", unsafe_allow_html=True)
    f1, f2, f3, f4 = st.columns(4)
    df = st.session_state.df_history
    fund = st.session_state.fundamentals
    
    ma20, ma60 = df.iloc[-1]['MA20'], df.iloc[-1]['MA60']
    rsi, atr = df.iloc[-1]['RSI'], df.iloc[-1]['ATR']
    obv, obv_ma = df.iloc[-1]['OBV'], df.iloc[-1]['OBV_MA']
    pe, roe = fund.get('PE'), fund.get('ROE')
    
    with f1:
        st.info("🧠 **量价与资金**")
        if obv > obv_ma: st.write("🟢 **OBV能量潮:** 主力吸筹")
        else: st.write("🔴 **OBV能量潮:** 资金派发")
        st.write(f"**RSI (14日):** {rsi:.1f}")

    with f2:
        st.warning("🛡️ **波动与风控**")
        st.write(f"**日均波幅 (ATR):** {atr:.2f}")
        if rsi > 70: st.error("🔥 极度超买，警惕回调")
        elif rsi < 30: st.success("🧊 极度超卖，酝酿反弹")

    with f3:
        st.success("💼 **深度基本面**")
        st.write(f"**ROE:** {f'{roe*100:.1f}%' if roe else '未知'}")
        st.write(f"**市盈率 (PE):** {f'{pe:.1f}' if pe else '未知'}")

    with f4:
        st.error("🏛️ **趋势轨道**")
        if current_p > df.iloc[-1]['BB_Up']: st.write("⚠️ **突破上轨:** 乖离过大")
        elif current_p < df.iloc[-1]['BB_Low']: st.write("✅ **触底下轨:** 支撑显现")
        else: st.write("⚖️ **布林轨道:** 震荡通道内")
        w52 = fund.get('52w_Change')
        st.write(f"**近一年:** {f'{w52*100:.1f}%' if w52 else '未知'}")

    st.markdown("---")
    
    col_diag, col_news = st.columns([1.5, 1.2], gap="large")
    with col_diag:
        st.markdown("### 📝 FactorX Pro 综合诊断")
        score = 0
        reasons = []

        if current_p > ma60 and ma20 > ma60:
            score += 1
            reasons.append("✔ **趋势因子：** 稳居生命线，多头通道。")
        elif current_p < ma60:
            score -= 1
            reasons.append("❌ **趋势因子：** 跌破生命线，中线走弱。")
            
        if obv > obv_ma:
            score += 1
            reasons.append("✔ **资金因子(OBV)：** 能量潮指标向上突破，主力资金呈现净流入（吸筹）态势。")
        else:
            score -= 1
            reasons.append("❌ **资金因子(OBV)：** 能量潮指标疲软，场内资金呈现派发出逃态势。")

        if rsi > 70:
            score -= 1
            reasons.append("❌ **情绪因子：** RSI超买，散户FOMO严重。")
        elif rsi < 30:
            score += 1
            reasons.append("✔ **情绪因子：** RSI极度冰点，做空动能衰竭。")
        
        if score >= 2: st.success("🟢 **核心指令：强烈看多 (Strong Buy)**")
        elif score == 1: st.info("🟡 **核心指令：谨慎乐观 (Cautious Optimism)**")
        elif score <= -1: st.error("🔴 **核心指令：防范风险 (Risk Warning / Sell)**")
        else: st.warning("⚪ **核心指令：中性观望 (Neutral)**")

        with st.expander("🔍 展开量化评分逻辑", expanded=False):
            for reason in reasons: st.markdown(reason)

    with col_news:
        st.markdown("### 📰 灵犀情报局")
        tab_stock, tab_macro, tab_report = st.tabs(["🎯 个股异动", "🌍 宏观电报", "📑 深度研报"])
        with tab_stock:
            if st.session_state.news_data:
                for item in st.session_state.news_data: st.markdown(f"""<div style="margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px dashed rgba(130,130,130,0.3);"><a href="{item['link']}" target="_blank" class="news-link" style="font-size: 13px;">{item['title']}</a><div style="font-size: 11px; color: gray; margin-top: 2px;">⏱️ {item['time']} | 🗞️ {item['publisher']}</div></div>""", unsafe_allow_html=True)
            else: st.caption("暂未嗅探到关联资讯。")
        with tab_macro:
            if st.session_state.macro_news:
                for item in st.session_state.macro_news: st.markdown(f"""<div style="margin-bottom: 8px; font-size: 13px;"><span style="color: #E53935; font-weight: bold;">{item['time']}</span> - {item['content']}</div>""", unsafe_allow_html=True)
            else: st.caption("宏观接口暂未响应。")
        with tab_report:
            if st.session_state.report_link: st.markdown(f"""<a href="{st.session_state.report_link}" target="_blank" class="report-btn">🔗 前往查阅 [{input_symbol}] 深度研报库</a>""", unsafe_allow_html=True)
else:
    st.info("💡 请在上方确认代码后，点击“启动 Pro 多维扫描”。")
