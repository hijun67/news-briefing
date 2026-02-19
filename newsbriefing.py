import feedparser
import google.generativeai as genai
from supabase import create_client, Client
import json
import os

# 1. 환경 설정 (실제 서비스 시 환경변수 os.environ.get 사용 추천)
GEMINI_API_KEY = "AIzaSyBY4CwIUsaSBnlrUnx-9o5abtxWnjHGdRs"
SUPABASE_URL = "https://wnblylvgbprfbyvbjkbo.supabase.co"
SUPABASE_KEY = "sb_publishable_9ymOoqQ5TZIbj47zUW1lCQ_CtfyxfbT"

# API 연결 초기화
genai.configure(api_key=GEMINI_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. 크롤링 대상 RSS 리스트 (샘플 80개 중 일부 예시)
RSS_FEEDS = [
    {"country": "한국", "category": "국내정치", "url": "https://www.chosun.com/arc/outboundfeeds/rss/category/politics/"},
    {"country": "한국", "category": "국내경제", "url": "https://www.mk.co.kr/rss/30100041/"},
    {"country": "미국", "category": "해외경제", "url": "https://www.reutersagency.com/feed/?best-topics=business"},
    # ... 여기에 80개 언론사 RSS 주소 추가
]

def generate_ai_briefing(title, original_url):
    """Gemini API를 사용하여 뉴스를 재구성 및 요약"""
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    당신은 상업용 뉴스 브리핑 AI 에디터입니다.
    기사 제목: {title}
    
    위 내용을 바탕으로 다음 규칙을 지켜 요약하세요:
    1. 원문 문장을 절대 그대로 사용하지 말고 100% 새롭게 집필할 것.
    2. 핵심 사실 3개를 각각 25자 이내의 문장으로 작성할 것.
    3. 20자 내외의 새로운 헤드라인을 작성할 것.
    4. 출력은 반드시 아래 JSON 형식으로만 할 것. 
    
    {{
      "ai_headline": "새로운 제목",
      "summary": ["요약1", "요약2", "요약3"]
    }}
    """
    
    response = model.generate_content(prompt)
    try:
        # JSON 텍스트만 추출하여 파싱
        result = json.loads(response.text.replace('```json', '').replace('```', ''))
        return result
    except:
        return None

def main():
    print("🚀 뉴스 브리핑 수집 및 가공 시작...")
    
    for feed in RSS_FEEDS:
        parsed_feed = feedparser.parse(feed['url'])
        
        # 최신 기사 1~2개만 샘플링 (일일 할당량 조절)
        for entry in parsed_feed.entries[:1]:
            print(f"Processing: {entry.title}")
            
            # AI 요약 실행
            briefing = generate_ai_briefing(entry.title, entry.link)
            
            if briefing:
                # Supabase DB 규격에 맞게 데이터 가공
                summaries_jsonb = [
                    {"text": briefing['summary'][0], "url": entry.link},
                    {"text": briefing['summary'][1], "url": entry.link},
                    {"text": briefing['summary'][2], "url": entry.link}
                ]
                
                # 데이터 저장
                data = {
                    "country": feed['country'],
                    "category": feed['category'],
                    "ai_headline": briefing['ai_headline'],
                    "original_url": entry.link,
                    "summaries": summaries_jsonb,
                    "provider_name": parsed_feed.feed.get('title', 'Unknown')
                }
                
                response = supabase.table("news_briefings").insert(data).execute()
                print(f"✅ 저장 완료: {briefing['ai_headline']}")

if __name__ == "__main__":
    main()