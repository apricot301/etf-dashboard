import os
from supabase import create_client, Client

# 환경변수 로드
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Supabase 연결
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 가상의 테스트 데이터 생성
test_data_list = [
    {"symbol": "487530", "name": "ACE 미국500데일리타겟커버드콜(합성)", "dividend_base_date": "20260731", "payment_date": "20260804", "dividend_amount": 125, "tax_standard_amount": 125},
    {"symbol": "481060", "name": "KODEX 미국AI테크TOP10타겟커버드콜", "dividend_base_date": "20260731", "payment_date": "20260804", "dividend_amount": 127, "tax_standard_amount": 127},
    {"symbol": "486450", "name": "PLUS 고배당주위클리커버드콜", "dividend_base_date": "20260731", "payment_date": "20260804", "dividend_amount": 90, "tax_standard_amount": 0},
    {"symbol": "488420", "name": "RISE 미국배당100데일리고정커버드콜", "dividend_base_date": "20260731", "payment_date": "20260804", "dividend_amount": 98, "tax_standard_amount": 98},
    {"symbol": "482730", "name": "SOL 미국500타겟데일리커버드콜액티브", "dividend_base_date": "20260731", "payment_date": "20260804", "dividend_amount": 105, "tax_standard_amount": 105},
    {"symbol": "482740", "name": "TIGER 미국30년국채커버드콜액티브(H)", "dividend_base_date": "20260731", "payment_date": "20260804", "dividend_amount": 102, "tax_standard_amount": 102}
]

def insert_test_data():
    print("테스트 데이터 주입을 시작합니다...")
    
    for data in test_data_list:
        try:
            # upsert 명령: 중복된 날짜가 있으면 덮어쓰고, 없으면 새로 추가
            supabase.table("etf_dividends").upsert(
                data, on_conflict="symbol,dividend_base_date"
            ).execute()
            print(f"[{data['name']}] 데이터 저장 완료!")
        except Exception as e:
            print(f"[{data['name']}] 에러: {e}")

if __name__ == "__main__":
    insert_test_data()
