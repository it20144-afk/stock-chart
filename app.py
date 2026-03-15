import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import requests

# 페이지 설정
st.set_page_config(page_title="나의 4분할 주식 차트", layout="wide")

st.title("📊 Smart Multi-Asset Dashboard")
st.markdown("종목명(한글/영문) 또는 코드를 입력하면 4분할 차트를 생성합니다.")

# 사이드바 설정
st.sidebar.header("검색 및 설정")
search_input = st.sidebar.text_input("검색어 (4개, 쉼표 구분)", "AAPL, TSLA, NVDA, MSFT")
days_to_display = st.sidebar.slider("차트 표시 기간 (일)", 30, 365, 120)

# 종목명 -> 티커 변환 함수 (검색 실패 시를 위해 개선)
def get_ticker_from_name(query):
    query = query.strip()
    if query.isdigit() and len(query) == 6: return f"{query}.KS"
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&quotesCount=1"
        res = requests.get(url, headers={'User-agent': 'Mozilla/5.0'})
        data = res.json()
        if data['quotes']:
            return data['quotes'][0]['symbol']
    except:
        return query
    return query

# 기술적 지표 계산 함수
def get_indicators(df):
    df['MA10'] = df['Close'].rolling(window=10).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA50'] = df['Close'].rolling(window=50).mean()
    df['MA120'] = df['Close'].rolling(window=120).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['Hist'] = df['MACD'] - df['Signal']
    return df

# 차트 그리기 함수
def plot_full_chart(ticker_query):
    try:
        ticker = get_ticker_from_name(ticker_query)
        # 데이터 수집 방식 최적화 (auto_adjust 추가)
        df = yf.download(ticker, start=datetime.now() - timedelta(days=500), progress=False, auto_adjust=True)
        
        if df.empty and ('.KS' in ticker or ticker.isdigit()):
            alt_ticker = ticker.replace('.KS', '.KQ') if '.KS' in ticker else f"{ticker}.KQ"
            df = yf.download(alt_ticker, start=datetime.now() - timedelta(days=500), progress=False, auto_adjust=True)
            if not df.empty: ticker = alt_ticker

        if df.empty: return None, ticker
        
        df = get_indicators(df).iloc[-days_to_display:]
        last_price = df['Close'].iloc[-1]

        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                            vertical_spacing=0.03, 
                            row_heights=[0.6, 0.15, 0.15])

        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Price"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA10'], line=dict(color='green', width=1.2), name="10MA"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='red', width=1.2), name="20MA"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA50'], line=dict(color='blue', width=1.2), name="50MA"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA120'], line=dict(color='white', width=1.8), name="120MA"), row=1, col=1)

        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#FFA500', width=1.2)), row=2, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="green", row=2, col=1)

        colors = ['red' if val >= 0 else 'blue' for val in df['Hist']]
        fig.add_trace(go.Bar(x=df.index, y=df['Hist'], marker_color=colors), row=3, col=1)
        
        fig.update_layout(height=600, template="plotly_dark", showlegend=False, 
                          margin=dict(l=10, r=10, t=50, b=10), xaxis_rangeslider_visible=False)
        
        curr_info = f"[{ticker}] Price: {last_price:,.0f} | 10MA: {df['MA10'].iloc[-1]:,.2f}"
        fig.add_annotation(xref="paper", yref="paper", x=0, y=1.05, text=curr_info, showarrow=False, font=dict(size=12, color="yellow"))
        
        return fig, ticker
    except: return None, ticker_query

# 레이아웃 배치
queries = [q.strip() for q in search_input.split(',')][:4]
if queries:
    cols = st.columns(2)
    for i, q in enumerate(queries):
        with cols[i % 2]:
            fig, final_ticker = plot_full_chart(q)
            st.markdown(f"### 📍 {q}")
            if fig: st.plotly_chart(fig, use_container_width=True)
            else: st.error(f"'{q}' ({final_ticker}) 데이터 수집 실패")
            if fig: st.plotly_chart(fig, use_container_width=True)
            else: st.error(f"'{q}' 검색 실패")
