import os
import requests
import urllib.parse
from supabase import create_client, Client

# 환경변수 로드
API_KEY = os.getenv("DATA_GO_KR_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Supabase 연결
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 대상 종목 리스트 (테스트용 6개)
TARGET_ETFS = {
    "487530": "ACE 미국500데일리타겟커버드콜(합성)",
    "481060": "KODEX 미국AI테크TOP10타겟커버드콜",
    "486450": "PLUS 고배당주위클리커버드콜",
    "488420": "RISE 미국배당100데일리고정커버드콜",
    "482730": "SOL 미국500타겟데일리커버드콜액티브",
    "482740": "TIGER 미국30년국채커버드콜액티브(H)"
}

def fetch_and_upsert():
    # URL 인코딩 중복 방지
    decoded_key = urllib.parse.unquote(API_KEY)
    url = "https://apis.data.go.kr/1160100/service/GetSecuritiesProductInfoService/getETFDivdInfo"
    
    # 💡핵심 수정: 단일 월이 아닌 최근 2개월(26년 7월, 6월) 데이터를 모두 수집하도록 변경
    target_months = ["202607", "202606"] 
    
    print(f"데이터 수집을 시작합니다. 대상 월: {target_months}")
    
    for code, name in TARGET_ETFS.items():
        params = {
            "serviceKey": decoded_key,
            "resultType": "json",
            "numOfRows": "50", # 한번에 가져올 데이터 수를 넉넉히 잡음
            "pageNo": "1",
            "likeSrtnCd": code
        }
        
        try:
            # API 호출
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            # API 응답 구조에서 아이템 리스트 추출
            items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
            
            if not items:
                print(f"[{name}] API 응답에 데이터가 없습니다.")
                continue
                
            count = 0
            for item in items:
                bas_dt = str(item.get("dvdBasDt", ""))
                
                # 배당기준일(bas_dt)이 우리가 찾는 달(target_months)로 시작하는지 확인
                if any(bas_dt.startswith(month) for month in target_months):
                    db_data = {
                        "symbol": code,
                        "name": name,
                        "dividend_base_date": bas_dt,
                        "payment_date": item.get("cashDvdPayDt", "미정"),
                        "dividend_amount": float(item.get("stkDivdCashPaymrtAmt", 0)),
                        "tax_standard_amount": float(item.get("taxStdAmt", 0))
                    }
                    
                    # Supabase에 데이터 저장 (중복 시 업데이트)
                    supabase.table("etf_dividends").upsert(
                        db_data, on_conflict="symbol,dividend_base_date"
                    ).execute()
                    
                    count += 1
                    
            print(f"[{name}] {count}건의 배당 데이터 수집 완료")
            
        except Exception as e:
            print(f"[{name}] 실행 중 에러 발생: {e}")

if __name__ == "__main__":
    fetch_and_upsert()
