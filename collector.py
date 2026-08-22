import os
import time
import requests
import urllib.parse
import pandas as pd
import FinanceDataReader as fdr
from dateutil.relativedelta import relativedelta
from datetime import datetime
from supabase import create_client, Client

# 1. 환경변수 및 Supabase 세팅
API_KEY = os.getenv("DATA_GO_KR_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. 59개 전 종목 리스트
TARGET_NAMES = [
    "ACE 고배당주Plus커버드콜액티브", "ACE 미국반도체데일리타겟커버드콜(합성)", "ACE 미국배당퀄리티+커버드콜액티브", "ACE 미국빅테크7+데일리타겟커버드콜(합성)", "ACE 미국500데일리타겟커버드콜(합성)",
    "KODEX 금융고배당TOP10타겟위클리커버드콜", "KODEX 미국AI테크TOP10타겟커버드콜", "KODEX 미국S&P500데일리커버드콜OTM", "KODEX 미국S&P500배당귀족커버드콜(합성 H)", "KODEX 미국S&P500변동성확대시커버드콜", "KODEX 미국나스닥100데일리커버드콜OTM", "KODEX 미국배당다우존스타겟커버드콜", "KODEX 미국배당커버드콜액티브", "KODEX 미국성장커버드콜액티브", "KODEX 미국30년국채타겟커버드콜(합성 H)", "KODEX 반도체타겟위클리커버드콜", "KODEX 테슬라커버드콜채권혼합액티브", "KODEX 200커버드콜액티브", "KODEX 200타겟위클리커버드콜",
    "PLUS 고배당주위클리고정커버드콜", "PLUS 고배당주위클리커버드콜", "PLUS 미국배당증가성장주데일리커버드콜", "PLUS 차이나항셍테크위클리타겟커버드콜", "PLUS 테슬라위클리커버드콜채권혼합", "PLUS 200위클리커버드콜채권혼합", "PLUS 200커버드콜액티브",
    "RISE 미국AI밸류체인데일리고정커버드콜", "RISE 미국S&P500데일리고정커버드콜", "RISE 미국배당100데일리고정커버드콜", "RISE 미국테크100데일리고정커버드콜", "RISE 미국30년국채커버드콜(합성)", "RISE 차이나테크TOP10위클리타겟커버드콜", "RISE 코리아밸류업위클리고정커버드콜", "RISE 코스닥커버드콜액티브", "RISE 테슬라미국채타겟커버드콜혼합(합성)", "RISE 200고배당커버드콜ATM", "RISE 200위클리커버드콜",
    "SOL 국제금커버드콜액티브", "SOL 미국30년국채커버드콜(합성)", "SOL 미국500타겟데일리커버드콜액티브", "SOL 팔란티어미국채커버드콜혼합", "SOL 팔란티어커버드콜OTM채권혼합", "SOL 200타겟위클리커버드콜",
    "TIGER 미국AI빅테크10타겟데일리커버드콜", "TIGER 미국S&P500타겟데일리커버드콜", "TIGER 미국나스닥100커버드콜(합성)", "TIGER 미국나스닥100타겟데일리커버드콜", "TIGER 미국배당다우존스타겟데일리커버드콜", "TIGER 미국배당다우존스타겟커버드콜1호", "TIGER 미국배당다우존스타겟커버드콜2호", "TIGER 미국테크TOP10타겟커버드콜", "TIGER 미국30년국채커버드콜액티브(H)", "TIGER 반도체TOP10커버드콜액티브", "TIGER 배당커버드콜액티브", "TIGER 엔비디아미국채커버드콜밸런스(합성)", "TIGER 코리아배당다우존스위클리커버드콜", "TIGER 200커버드콜", "TIGER 200커버드콜OTM", "TIGER 200타겟위클리커버드콜"
]

def calculate_returns(df_price):
    """현재가 및 1,3,6,12개월 전 대비 수익률 계산"""
    if df_price is None or df_price.empty:
        return 0, 0, 0, 0, 0
    
    current_price = df_price['Close'].iloc[-1]
    last_date = df_price.index[-1]
    
    def get_past_return(months_ago):
        target_date = last_date - relativedelta(months=months_ago)
        past_df = df_price[df_price.index <= target_date]
        if past_df.empty:
            return 0.0
        past_price = past_df['Close'].iloc[-1]
        return round(((current_price / past_price) - 1) * 100, 2)
        
    return current_price, get_past_return(1), get_past_return(3), get_past_return(6), get_past_return(12)

def fetch_and_process():
    decoded_key = urllib.parse.unquote(API_KEY)
    div_url = "https://apis.data.go.kr/1160100/service/GetSecuritiesProductInfoService/getETFDivdInfo"
    
    # 3. ETF 목록 매핑
    print("국내 ETF 마스터 데이터 불러오는 중...")
    df_master = fdr.StockListing('ETF')
    
    now = datetime.now()
    target_months = [f"{now.year}{now.month:02d}", f"{now.year}{now.month-1:02d}"]
    one_year_ago = (now - relativedelta(years=1, days=15)).strftime('%Y-%m-%d')
    
    for name in TARGET_NAMES:
        matched = df_master[df_master['Name'] == name]
        if matched.empty:
            continue
        code = matched.iloc[0]['Symbol']
        
        # 주가 데이터 및 수익률 계산
        try:
            df_price = fdr.DataReader(code, one_year_ago)
            current_price, r1m, r3m, r6m, r1y = calculate_returns(df_price)
        except:
            current_price, r1m, r3m, r6m, r1y = 0, 0, 0, 0, 0
            
        # 분배금 데이터 조회 (공공데이터포털)
        params = {"serviceKey": decoded_key, "resultType": "json", "numOfRows": "20", "pageNo": "1", "likeSrtnCd": code}
        
        try:
            res = requests.get(div_url, params=params, timeout=5).json()
            items = res.get("response", {}).get("body", {}).get("items", {}).get("item", [])
            
            for item in items:
                bas_dt = str(item.get("dvdBasDt", ""))
                if any(bas_dt.startswith(m) for m in target_months):
                    div_amount = float(item.get("stkDivdCashPaymrtAmt", 0))
                    
                    # 연환산 분배율 계산 (최근 배당금 기준 12개월 단순 환산)
                    annual_yield = round((div_amount * 12) / current_price * 100, 2) if current_price > 0 else 0
                    
                    db_data = {
                        "symbol": code, "name": name,
                        "dividend_base_date": bas_dt,
                        "payment_date": item.get("cashDvdPayDt", "미정"),
                        "dividend_amount": div_amount,
                        "tax_standard_amount": float(item.get("taxStdAmt", 0)),
                        "annual_yield": annual_yield,
                        "return_1m": r1m, "return_3m": r3m, "return_6m": r6m, "return_1y": r1y
                    }
                    supabase.table("etf_dividends").upsert(db_data, on_conflict="symbol,dividend_base_date").execute()
                    break # 가장 최근 해당 월 데이터 하나만 넣고 다음 종목으로 패스
            print(f"[{name}] 데이터 적재 완료")
        except Exception as e:
            print(f"[{name}] 수집 에러 발생")
            
        time.sleep(0.5) # 공공데이터포털 서버 과부하 방지용 딜레이

if __name__ == "__main__":
    fetch_and_process()
