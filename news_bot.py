import os
import html
import feedparser
import requests

from urllib.parse import quote
from datetime import datetime, timedelta, timezone

KEYWORD_GROUPS = {
    "엔터": [
        "하이브", "HYBE", "JYP", "SM", "YG",
        "BTS", "방탄소년단", "세븐틴", "SEVENTEEN",
        "TXT", "투모로우바이투게더",
        "엔하이픈", "ENHYPEN", "르세라핌", "뉴진스",
        "민희진", "방시혁",
        "BLACKPINK", "블랙핑크", "트레저", "TREASURE",
        "베이비몬스터", "양현석",
        "TWICE", "트와이스", "스트레이키즈", "STRAYKIDS",
        "ITZY", "엔믹스", "NMIXX", "NEXZ", "니쥬", "NIZIU",
        "NCT", "NCT 127", "NCT DREAM", "NCT WISH",
        "에스파", "aespa", "레드벨벳", "샤이니", "EXO",
        "소녀시대", "슈퍼주니어", "동방신기", "TVXQ",
        "보이넥스트도어", "TWS", "투어스",
        "캣츠아이", "KATSEYE", "&TEAM", "아일릿"
    ],
    "유통": [
        "이마트", "홈플러스",
        "롯데백화점", "현대백화점",
        "신세계", "올리브영", "무신사",
        "BGF리테일", "GS리테일",
        "면세점", "대형마트", "백화점 매출", "소비자심리",
        "방일 관광객", "방한 관광객",
        "외국인 관광객", "중일 관계"
    ]
}

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def clean_title(title):
    if " - " in title:
        title = title.rsplit(" - ", 1)[0]
    return title.strip()


def normalize_title(title):
    return (
        title.replace(" ", "")
        .replace("-", "")
        .replace("[", "")
        .replace("]", "")
        .lower()
    )


def get_original_url(url):
    try:
        response = requests.get(
            url,
            allow_redirects=True,
            timeout=10,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )
        return response.url
    except Exception:
        return url


def fetch_news(keyword, limit=3):
    encoded_keyword = quote(keyword)

    url = (
        f"https://news.google.com/rss/search?"
        f"q={encoded_keyword}&hl=ko&gl=KR&ceid=KR:ko"
    )

    feed = feedparser.parse(url)

    news = []
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=48)

    for entry in feed.entries:
        if not hasattr(entry, "published_parsed"):
            continue

        published_time = datetime(
            *entry.published_parsed[:6],
            tzinfo=timezone.utc
        )

        if published_time < cutoff:
            continue

        title = clean_title(entry.title)
        original_url = get_original_url(entry.link)

        news.append({
            "title": title,
            "link": original_url,
            "published_time": published_time
        })

        if len(news) >= limit:
            break

    return news


def build_message():
    today = datetime.now().strftime("%Y-%m-%d")

    message = (
        f"<b>[{today} 유통/엔터 뉴스]</b>\n"
        f"최근 48시간 기준\n\n"
    )

    seen_titles = set()
    total_count = 0

    for group_name, keywords in KEYWORD_GROUPS.items():
        group_articles = []

        for keyword in keywords:
            articles = fetch_news(keyword)

            for article in articles:
                title_key = normalize_title(article["title"])

                if title_key in seen_titles:
                    continue

                seen_titles.add(title_key)
                group_articles.append(article)

        if not group_articles:
            continue

        group_articles.sort(
            key=lambda x: x["published_time"],
            reverse=True
        )

        message += f"<b>■ {html.escape(group_name)}</b>\n"

        for article in group_articles[:15]:
            title = html.escape(article["title"])
            link = html.escape(article["link"], quote=True)

            message += f'• <a href="{link}">{title}</a>\n'

        message += "\n"
        total_count += len(group_articles[:15])

    if total_count == 0:
        message += "최근 48시간 내 유통/엔터 관련 뉴스가 없습니다."

    return message


def split_message(text, max_length=3500):
    chunks = []
    current = ""

    for line in text.splitlines(keepends=True):
        if len(current) + len(line) > max_length:
            chunks.append(current)
            current = line
        else:
            current += line

    if current:
        chunks.append(current)

    return chunks


def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    chunks = split_message(text)

    for chunk in chunks:
        response = requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": chunk,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }
        )

        print(response.status_code)
        print(response.text)

        response.raise_for_status()


if __name__ == "__main__":
    message = build_message()
    send_telegram(message)
