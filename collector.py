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

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 웹사이트 스크래핑 오류를 원천 차단하기 위해 주요 커버드콜/고배당 ETF 코드와 이름을 직접 매핑
TARGET_ETFS = {
    "0199C0": "ACE 고배당주Plus커버드콜액티브",
    "489440": "ACE 미국반도체데일리타겟커버드콜(합성)",
    "487310": "ACE 미국배당퀄리티+커버드콜액티브",
    "493260": "ACE 미국빅테크7+데일리타겟커버드콜(합성)",
    "487530": "ACE 미국500데일리타겟커버드콜(합성)",
    "498410": "KODEX 금융고배당TOP10타겟위클리커버드콜",
    "483280": "KODEX 미국AI테크TOP10타겟커버드콜",
    "481060": "KODEX 미국배당다우존스타겟커버드콜",
    "441640": "KODEX 미국배당커버드콜액티브",
    "498400": "KODEX 200타겟위클리커버드콜",
    "0219E0": "KODEX 200커버드콜액티브",
    "0190G0": "KODEX 반도체타겟위클리커버드콜",
    "486450": "PLUS 고배당주위클리커버드콜",
    "488420": "RISE 미국배당100데일리고정커버드콜",
    "482730": "SOL 미국500타겟데일리커버드콜액티브",
    "494210": "SOL 미국500타겟데일리커버드콜액티브",
    "482740": "TIGER 미국30년국채커버드콜액티브(H)",
    "472150": "TIGER 배당커버드콜액티브"
}

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

decoded_key = urllib.parse.unquote(API_KEY)
div_url = "https://apis.data.go.kr/1160100/service/GetSecuritiesProductInfoService/getETFDivdInfo"
one_year_ago = (datetime.now() - relativedelta(years=1, days=15)).strftime('%Y-%m-%d')

success_count = 0
print("=== [2] 개별 종목 데이터 수집 진입 ===")

for code, name in TARGET_ETFS.items():
    try:
        df_price = fdr.DataReader(code, one_year_ago)
        current_price, r1m, r3m, r6m, r1y = calculate_returns(df_price)
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
                print(f"[{name}] 수집 및 적재 성공")
    except Exception as e:
        print(f"[{name}] 에러 발생: {e}")
        
    time.sleep(0.5)

print(f"=== [3] 모든 작업 종료! 총 {success_count}개 종목 적재 완료 ===")
