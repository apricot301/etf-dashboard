import os
import requests
import urllib.parse
from supabase import create_client, Client
from datetime import datetime

# GitHub Secrets에서 가져온 키들
API_KEY = os.environ.get("DATA_GO_KR_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 수집 대상 종목 (테스트용으로 6개만 먼저 세팅. 나중에 추가 가능)
TARGET_ETFS = {
    "487530": "ACE 미국500데일리타겟커버드콜(합성)",
    "481060": "KODEX 미국AI테크TOP10타겟커버드콜",
    "486450": "PLUS 고배당주위클리커버드콜",
    "488420": "RISE 미국배당100데일리고정커버드콜",
    "482730": "SOL 미국500타겟데일리커버드콜액티브",
    "482740": "TIGER 미국30년국채커버드콜액티브(H)"
}

def fetch_and_upsert():
    decoded_key = urllib.parse.unquote(API_KEY)
    url = "https://apis.data.go.kr/1160100/service/GetSecuritiesProductInfoService/getETFDivdInfo"
    
    now = datetime.now()
    # 실행하는 달의 '전달' 배당을 조회 (예: 8월 실행 시 7월 배당)
    target_month = f"{now.year}{now.month - 1:02d}" if now.month > 1 else f"{now.year - 1}12"
    
    for code, name in TARGET_ETFS.items():
        params = {
            "serviceKey": decoded_key,
            "resultType": "json",
            "numOfRows": "30",
            "pageNo": "1",
            "likeSrtnCd": code
        }
        
        try:
            res = requests.get(url, params=params, timeout=10).json()
            items = res.get("response", {}).get("body", {}).get("items", {}).get("item", [])
            
            for item in items:
                bas_dt = str(item.get("dvdBasDt", ""))
                if bas_dt.startswith(target_month):
                    data = {
                        "symbol": code,
                        "name": name,
                        "dividend_base_date": bas_dt,
                        "payment_date": item.get("cashDvdPayDt", "미정"),
                        "dividend_amount": float(item.get("stkDivdCashPaymrtAmt", 0)),
                        "tax_standard_amount": float(item.get("taxStdAmt", 0))
                    }
                    supabase.table("etf_dividends").upsert(data, on_conflict="symbol,dividend_base_date").execute()
                    print(f"[{name}] {target_month} 데이터 수집 완료")
        except Exception as e:
            print(f"[{name}] 에러: {e}")

if __name__ == "__main__":
    fetch_and_upsert()
