import os
import time
import requests
import urllib.parse
import pandas as pd
import FinanceDataReader as fdr
from dateutil.relativedelta import relativedelta
from datetime import datetime
from supabase import create_client, Client

# 환경변수 설정
API_KEY = os.getenv("DATA_GO_KR_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def calculate_returns(df_price):
    if df_price is None or df_price.empty:
        return 0, 0, 0, 0, 0
    current_price = df_price['Close'].iloc[-1]
    last_date = df_price.index[-1]
    
    def get_past_return(months_ago):
        target_date = last_date - relativedelta(months=months_ago)
        past_df = df_price[df_price.index <= target_date]
        if past_df.empty: return 0.0
        return round(((current_price / past_df['Close'].iloc[-1]) - 1) * 100, 2)
    return current_price, get_past_return(1), get_past_return(3), get_past_return(6), get_past_return(12)

def fetch_and_process():
    decoded_key = urllib.parse.unquote(API_KEY)
    div_url = "https://apis.data.go.kr/1160100/service/GetSecuritiesProductInfoService/getETFDivdInfo"
    
    print("전체 국내 ETF 리스트 불러오는 중...")
    try:
        df_master = fdr.StockListing('ETF')
    except Exception as e:
        print(f"ETF 리스트 로드 실패: {e}")
        return

    # '커버드콜' 또는 '배당' 또는 '고배당'이 포함된 ETF 종목들을 자동으로 전부 필터링
    filtered_etfs = df_master[
        df_master['Name'].str.contains('커버드콜|배당|고배당|타겟', na=False)
    ]
    
    print(f"총 {len(filtered_etfs)}개의 대상 ETF를 자동으로 발굴했습니다. 수집을 시작합니다.")
    one_year_ago = (datetime.now() - relativedelta(years=1, days=15)).strftime('%Y-%m-%d')
    
    success_count = 0
    for idx, row in filtered_etfs.iterrows():
        code = str(row['Symbol'])
        name = row['Name']
        
        # 1. 주가 및 수익률 계산
        try:
            df_price = fdr.DataReader(code, one_year_ago)
            current_price, r1m, r3m, r6m, r1y = calculate_returns(df_price)
        except:
            current_price, r1m, r3m, r6m, r1y = 0, 0, 0, 0, 0
            
        # 2. 분배금 데이터 수집
        params = {"serviceKey": decoded_key, "resultType": "json", "numOfRows": "5", "pageNo": "1", "likeSrtnCd": code}
        
        try:
            res = requests.get(div_url, params=params, timeout=15)
            if res.status_code == 200:
                items = res.json().get("response", {}).get("body", {}).get("items", {}).get("item", [])
                
                if len(items) > 0:
                    item = items[0] 
                    div_amount = float(item.get("stkDivdCashPaymrtAmt", 0))
                    annual_yield = round((div_amount * 12) / current_price * 100, 2) if current_price > 0 else 0
                    
                    db_data = {
                        "symbol": code, 
                        "name": name,
                        "dividend_base_date": str(item.get("dvdBasDt", "")),
                        "payment_date": item.get("cashDvdPayDt", "미정"),
                        "dividend_amount": div_amount,
                        "tax_standard_amount": float(item.get("taxStdAmt", 0)),
                        "annual_yield": annual_yield,
                        "return_1m": r1m, "return_3m": r3m, "return_6m": r6m, "return_1y": r1y
                    }
                    supabase.table("etf_dividends").upsert(db_data, on_conflict="symbol,dividend_base_date").execute()
                    print(f"[{name}({code})] 수집 성공")
                    success_count += 1
        except Exception as e:
            pass
            
        time.sleep(0.3) # 서버 부하 방지 딜레이

    print(f"총 {success_count}개 종목의 데이터 수집 및 적재가 완료되었습니다.")

if __name__ == "__main__":
    fetch_and_process()
