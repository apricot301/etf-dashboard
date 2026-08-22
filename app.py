import streamlit as st
from supabase import create_client, Client
import pandas as pd

st.set_page_config(page_title="나의 59개 커버드콜 대시보드", layout="wide")
st.title("📊 월간 커버드콜 ETF 통합 리포트")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

@st.cache_data(ttl=600)
def load_data():
    res = supabase.table("etf_dividends").select("*").order("dividend_base_date", desc=True).execute()
    return pd.DataFrame(res.data)

df = load_data()

if not df.empty:
    # 화면용 열 정리
    df = df[['name', 'dividend_base_date', 'payment_date', 'dividend_amount', 'tax_standard_amount', 'annual_yield', 'return_1m', 'return_3m', 'return_6m', 'return_1y']]
    df.columns = ['종목명', '배당기준일', '지급일자', '분배금(원)', '과표액(원)', '연환산분배율(%)', '1M(%)', '3M(%)', '6M(%)', '1Y(%)']
    
    # 숫자 포맷 지정 (소수점 정리 및 수익률 색상 입히기)
    styled_df = df.style.format({
        '분배금(원)': '{:,.0f}',
        '과표액(원)': '{:,.0f}',
        '연환산분배율(%)': '{:.2f}',
        '1M(%)': '{:+.2f}', '3M(%)': '{:+.2f}', '6M(%)': '{:+.2f}', '1Y(%)': '{:+.2f}'
    }).background_gradient(cmap='RdYlBu_r', subset=['1M(%)', '3M(%)', '6M(%)', '1Y(%)']) 
    
    st.dataframe(styled_df, use_container_width=True, hide_index=True, height=800)
else:
    st.info("데이터를 불러오고 있습니다. GitHub Actions 실행 결과를 확인해 주세요.")
