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

# 59개 전 종목 고유 코드(Symbol) 리스트
TARGET_CODES = [
    "487530", "481060", "486450", "488420", "482730", "482740",
    "489440", "487310", "493260", "496610", "491760", "493250",
    "488770", "489450", "491750", "493240", "492390", "480410",
    "480420", "487290", "486440", "489370", "484550", "486460",
    "480290", "480300", "490190", "490200", "490210", "490220",
    "491410", "492580", "495170", "496150", "496160", "497330",
    "497340", "498010", "498020", "498030", "499110", "499120",
    "500110", "500120", "501230", "501240", "502340", "502350",
    "503410", "503420", "504510", "504520", "505110", "505120",
    "506110", "506120", "507110", "507120", "508110"
]

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
    
    print("주식 마스터 데이터 로딩 중...")
    try:
        df_master = fdr.StockListing('ETF')
    except Exception as e:
        print(f"ETF 리스트 로드 실패: {e}")
        return

    one_year_ago = (datetime.now() - relativedelta(years=1, days=15)).strftime('%Y-%m-%d')
    
    for code in TARGET_CODES:
        matched = df_master[df_master['Symbol'] == code]
        if matched.empty:
            print(f"[{code}] 마스터에서 코드를 찾을 수 없습니다.")
            continue
        name = matched.iloc[0]['Name']
        
        # 1. 주가 및 수익률 계산
        try:
            df_price = fdr.DataReader(code, one_year_ago)
            current_price, r1m, r3m, r6m, r1y = calculate_returns(df_price)
        except Exception as e:
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
                    print(f"[{name}({code})] 적재 성공")
                else:
                    print(f"[{name}({code})] 공시된 배당 데이터 없음")
        except Exception as e:
            print(f"[{name}({code})] 에러: {e}")
            
        time.sleep(0.5)

if __name__ == "__main__":
    fetch_and_process()
