import os
import time
import requests
import urllib.parse
import pandas as pd
import FinanceDataReader as fdr
from dateutil.relativedelta import relativedelta
from datetime import datetime
from supabase import create_client, Client

print("=== [1] 스크립트를 시작합니다 ===")

API_KEY = os.getenv("DATA_GO_KR_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

print(f"환경변수 체크 -> API_KEY: {bool(API_KEY)}, SUPABASE_URL: {bool(SUPABASE_URL)}, SUPABASE_KEY: {bool(SUPABASE_KEY)}")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("Supabase 클라이언트 연결 성공")
except Exception as e:
    print(f"*** Supabase 연결 에러: {e} ***")

try:
    print("=== [2] FinanceDataReader로 전체 ETF 리스트 로딩 시도 중... ===")
    df_master = fdr.StockListing('ETF')
    print(f"ETF 리스트 로드 성공! 총 개수: {len(df_master)}")
except Exception as e:
    print(f"*** [에러 발생] ETF 리스트를 불러오지 못했습니다: {e} ***")
    exit()

# 필터링 조건
filtered_etfs = df_master[
    df_master['Name'].str.contains('커버드콜|배당|고배당|타겟', na=False)
]
print(f"=== [3] 필터링된 대상 ETF 개수: {len(filtered_etfs)}개 ===")

if len(filtered_etfs) == 0:
    print("*** [경고] 검색 조건에 맞는 ETF가 0개입니다! ***")
    exit()

one_year_ago = (datetime.now() - relativedelta(years=1, days=15)).strftime('%Y-%m-%d')
decoded_key = urllib.parse.unquote(API_KEY)
div_url = "https://apis.data.go.kr/1160100/service/GetSecuritiesProductInfoService/getETFDivdInfo"

success_count = 0
print("=== [4] 개별 종목 데이터 수집 루프 진입 ===")

for idx, row in filtered_etfs.iterrows():
    code = str(row['Symbol'])
    name = row['Name']
    
    try:
        df_price = fdr.DataReader(code, one_year_ago)
        if df_price is not None and not df_price.empty:
            current_price = df_price['Close'].iloc[-1]
            last_date = df_price.index[-1]
            
            def get_past_return(months_ago):
                target_date = last_date - relativedelta(months=months_ago)
                past_df = df_price[df_price.index <= target_date]
                if past_df.empty: return 0.0
                return round(((current_price / past_df['Close'].iloc[-1]) - 1) * 100, 2)
            
            r1m = get_past_return(1)
            r3m = get_past_return(3)
            r6m = get_past_return(6)
            r1y = get_past_return(12)
        else:
            current_price, r1m, r3m, r6m, r1y = 0, 0, 0, 0, 0
    except Exception as e:
        current_price, r1m, r3m, r6m, r1y = 0, 0, 0, 0, 0
        
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
                success_count += 1
    except Exception as e:
        pass
        
    time.sleep(0.3)

print(f"=== [5] 모든 작업 종료! 총 {success_count}개 종목 적재 완료 ===")
