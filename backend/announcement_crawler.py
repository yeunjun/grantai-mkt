"""
GrantAI — 정부지원사업 공고 자동 수집 & 매칭 엔진 (Phase 2A)

공고 소스:
  1. 기업마당 (bizinfo.go.kr) - SME 지원사업 전체
  2. 공공데이터포털 (data.go.kr) - 중소벤처기업부 지원사업 목록
  3. K-Startup (k-startup.go.kr) - 창업 특화

환경 변수 (필수):
  BIZINFO_API_KEY   — 기업마당 API 키
  DATA_GO_KR_KEY    — 공공데이터포털 서비스키
  ANTHROPIC_API_KEY — Claude API 키 (매칭 판단용)
  DISCORD_WEBHOOK   — 알림 웹훅 URL

API 발급 방법:
  - data.go.kr: 회원가입 → "중소벤처기업부_지원사업_공고" 검색 → 활용신청
  - bizinfo.go.kr: https://www.bizinfo.go.kr/apiList.do 접속 → API 신청
"""

import os
import json
import sqlite3
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

import httpx
from google import genai

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("grant_crawler")

DB_PATH = Path(__file__).parent / "grants.db"

BIZINFO_API_KEY = os.getenv("BIZINFO_API_KEY", "")
DATA_GO_KR_KEY  = os.getenv("DATA_GO_KR_KEY", "")
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY", "")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK", "")


# ─────────────────────────────────────────
# DB 초기화
# ─────────────────────────────────────────

def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS announcements (
        id          TEXT PRIMARY KEY,
        source      TEXT,
        title       TEXT,
        org         TEXT,
        category    TEXT,
        start_date  TEXT,
        end_date    TEXT,
        amount      TEXT,
        url         TEXT,
        raw_json    TEXT,
        created_at  TEXT DEFAULT (datetime('now','localtime'))
    );

    CREATE TABLE IF NOT EXISTS customers (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT,
        industry    TEXT,
        keywords    TEXT,   -- JSON array
        email       TEXT,
        discord_id  TEXT,
        created_at  TEXT DEFAULT (datetime('now','localtime'))
    );

    CREATE TABLE IF NOT EXISTS matches (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id     INTEGER,
        announcement_id TEXT,
        score           REAL,
        reason          TEXT,
        notified        INTEGER DEFAULT 0,
        created_at      TEXT DEFAULT (datetime('now','localtime')),
        UNIQUE(customer_id, announcement_id)
    );
    """)
    con.commit()
    con.close()
    log.info("DB 초기화 완료: %s", DB_PATH)


# ─────────────────────────────────────────
# 1. 기업마당 API
# ─────────────────────────────────────────

async def fetch_bizinfo(client: httpx.AsyncClient, page: int = 1, per_page: int = 100) -> list[dict]:
    """기업마당 지원사업 공고 조회"""
    url = "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do"
    params = {
        "crtfcKey":  BIZINFO_API_KEY,
        "dataType":  "json",
        "pageUnit":  str(per_page),
        "pageIndex": str(page),
    }
    try:
        resp = await client.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("jsonArray", [])
        log.info("기업마당 공고 %d건 수집 (page %d)", len(items), page)
        return items
    except Exception as e:
        log.warning("기업마당 API 오류: %s", e)
        return []


def normalize_bizinfo(item: dict) -> dict:
    return {
        "id":         f"bizinfo_{item.get('pblancId', '')}",
        "source":     "기업마당",
        "title":      item.get("pblancNm", ""),
        "org":        item.get("excInsttNm", ""),
        "category":   item.get("bsnsSe", ""),
        "start_date": item.get("reqstBeginDe", ""),
        "end_date":   item.get("reqstEndDe", ""),
        "amount":     item.get("sprtLmttPd", ""),
        "url":        f"https://www.bizinfo.go.kr/web/biz/bizinfoView.do?pblancId={item.get('pblancId', '')}",
        "raw_json":   json.dumps(item, ensure_ascii=False),
    }


# ─────────────────────────────────────────
# 2. 공공데이터포털 — 중소벤처기업부 지원사업
# ─────────────────────────────────────────

async def fetch_data_go_kr(client: httpx.AsyncClient, page: int = 1, per_page: int = 100) -> list[dict]:
    """중소벤처기업부 지원사업 공고 목록 (data.go.kr)"""
    url = "https://apis.data.go.kr/1421000/bizinfo/getAnnouncementList"
    params = {
        "serviceKey":  DATA_GO_KR_KEY,
        "pageNo":      str(page),
        "numOfRows":   str(per_page),
        "type":        "json",
    }
    try:
        resp = await client.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("data", [])
        log.info("data.go.kr 공고 %d건 수집 (page %d)", len(items), page)
        return items
    except Exception as e:
        log.warning("data.go.kr API 오류: %s", e)
        return []


def normalize_data_go_kr(item: dict) -> dict:
    return {
        "id":         f"datagokr_{item.get('번호', '')}",
        "source":     "공공데이터포털",
        "title":      item.get("사업명", ""),
        "org":        item.get("담당기관", ""),
        "category":   item.get("지원분야", ""),
        "start_date": item.get("접수시작일", ""),
        "end_date":   item.get("접수마감일", ""),
        "amount":     item.get("지원금액", ""),
        "url":        item.get("상세URL", ""),
        "raw_json":   json.dumps(item, ensure_ascii=False),
    }


# ─────────────────────────────────────────
# 3. K-Startup — 창업진흥원
#    (공개 API 엔드포인트 / 무인증 조회 가능한 RSS 활용)
# ─────────────────────────────────────────

async def fetch_kstartup(client: httpx.AsyncClient) -> list[dict]:
    """K-Startup 공지사항 RSS 수집 (API Key 불필요)"""
    url = "https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do"
    # RSS/JSON 공개 엔드포인트 — 정식 API 키 발급 전 임시 사용
    try:
        resp = await client.get(url, timeout=10)
        # HTML 파싱 대신 API 공개 후 교체 예정
        # 현재는 빈 리스트 반환 (API Key 발급 후 활성화)
        log.info("K-Startup: API Key 발급 후 활성화 예정")
        return []
    except Exception as e:
        log.warning("K-Startup 수집 오류: %s", e)
        return []


# ─────────────────────────────────────────
# DB 저장
# ─────────────────────────────────────────

def upsert_announcements(items: list[dict]) -> int:
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    new_count = 0
    for item in items:
        try:
            cur.execute("""
                INSERT OR IGNORE INTO announcements
                    (id, source, title, org, category, start_date, end_date, amount, url, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item["id"], item["source"], item["title"], item["org"],
                item["category"], item["start_date"], item["end_date"],
                item["amount"], item["url"], item["raw_json"],
            ))
            if cur.rowcount > 0:
                new_count += 1
        except Exception as e:
            log.warning("DB 저장 오류 (id=%s): %s", item.get("id"), e)
    con.commit()
    con.close()
    return new_count


# ─────────────────────────────────────────
# Claude 기반 키워드 매칭
# ─────────────────────────────────────────

def match_announcements_for_customer(customer: dict) -> list[dict]:
    """
    고객 키워드 vs 공고 타이틀/카테고리 → Claude로 매칭 점수 산출
    Returns: List of {announcement_id, score, reason}
    """
    if not GEMINI_API_KEY:
        log.warning("GEMINI_API_KEY 미설정 — 단순 키워드 매칭으로 대체")
        return _simple_keyword_match(customer)

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    today = datetime.now().strftime("%Y%m%d")
    cur.execute("""
        SELECT id, title, org, category, end_date, amount, url
        FROM announcements
        WHERE end_date >= ? OR end_date = '' OR end_date IS NULL
        ORDER BY created_at DESC
        LIMIT 200
    """, (today,))
    rows = cur.fetchall()
    con.close()

    if not rows:
        return []

    ann_text = "\n".join(
        f"[{r[0]}] {r[1]} | {r[2]} | {r[3]} | 마감:{r[4]} | 지원금:{r[5]}"
        for r in rows
    )
    keywords = json.loads(customer.get("keywords", "[]"))
    industry = customer.get("industry", "")

    prompt = f"""다음은 정부지원사업 공고 목록입니다.

회사 정보:
- 업종: {industry}
- 사업 키워드: {', '.join(keywords)}

공고 목록 (형식: [공고ID] 제목 | 기관 | 분야 | 마감 | 지원금):
{ann_text}

위 공고 중 이 회사가 신청할 수 있는 TOP 5를 선정하고, 각 공고에 대해 JSON 배열로 반환하세요.
형식: [{{"id": "공고ID", "score": 0.0~1.0, "reason": "한 줄 이유"}}]
JSON만 반환, 다른 텍스트 없이."""

    try:
        client_ai = genai.Client(api_key=GEMINI_API_KEY)
        resp = client_ai.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        result_text = resp.text.strip()
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        matches = json.loads(result_text)
        log.info("Gemini 매칭 완료: 고객 %s → %d건", customer.get("name"), len(matches))
        return matches
    except Exception as e:
        log.warning("Gemini 매칭 오류: %s", e)
        return _simple_keyword_match(customer)


def _simple_keyword_match(customer: dict) -> list[dict]:
    """Claude 미사용 시 단순 키워드 포함 여부로 매칭"""
    keywords = json.loads(customer.get("keywords", "[]"))
    industry = customer.get("industry", "")
    search_terms = keywords + [industry]

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    today = datetime.now().strftime("%Y%m%d")
    cur.execute("""
        SELECT id, title, category FROM announcements
        WHERE end_date >= ? OR end_date = '' OR end_date IS NULL
    """, (today,))
    rows = cur.fetchall()
    con.close()

    matches = []
    for row in rows:
        ann_text = f"{row[1]} {row[2]}".lower()
        hits = sum(1 for kw in search_terms if kw.lower() in ann_text)
        if hits > 0:
            matches.append({"id": row[0], "score": min(hits / len(search_terms), 1.0), "reason": f"키워드 {hits}개 일치"})

    matches.sort(key=lambda x: x["score"], reverse=True)
    return matches[:5]


def save_matches(customer_id: int, matches: list[dict]) -> list[dict]:
    """매칭 결과 저장, 신규 매칭만 반환"""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    new_matches = []
    for m in matches:
        try:
            cur.execute("""
                INSERT OR IGNORE INTO matches (customer_id, announcement_id, score, reason)
                VALUES (?, ?, ?, ?)
            """, (customer_id, m["id"], m["score"], m.get("reason", "")))
            if cur.rowcount > 0:
                # 공고 상세 조회
                cur.execute("SELECT title, org, end_date, url FROM announcements WHERE id = ?", (m["id"],))
                row = cur.fetchone()
                if row:
                    new_matches.append({**m, "title": row[0], "org": row[1], "end_date": row[2], "url": row[3]})
        except Exception as e:
            log.warning("매칭 저장 오류: %s", e)
    con.commit()
    con.close()
    return new_matches


# ─────────────────────────────────────────
# Discord 알림
# ─────────────────────────────────────────

async def notify_discord(customer_name: str, new_matches: list[dict]):
    if not DISCORD_WEBHOOK or not new_matches:
        return

    lines = [f"**[GrantAI] {customer_name}님 신규 공고 매칭 {len(new_matches)}건**\n"]
    for i, m in enumerate(new_matches[:5], 1):
        lines.append(
            f"{i}. **{m.get('title', '')}** ({m.get('org', '')})\n"
            f"   마감: {m.get('end_date', '미정')} | 점수: {m.get('score', 0):.0%}\n"
            f"   → {m.get('url', '')}\n"
        )

    payload = {"content": "\n".join(lines)[:1900]}
    async with httpx.AsyncClient() as client:
        try:
            await client.post(DISCORD_WEBHOOK, json=payload, timeout=10)
            log.info("Discord 알림 발송 완료")
        except Exception as e:
            log.warning("Discord 알림 오류: %s", e)


# ─────────────────────────────────────────
# 마감 임박 리마인더 (D-7)
# ─────────────────────────────────────────

async def send_deadline_reminders():
    """마감 7일 이내 공고 알림"""
    deadline = (datetime.now() + timedelta(days=7)).strftime("%Y%m%d")
    today = datetime.now().strftime("%Y%m%d")

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        SELECT m.customer_id, c.name, a.title, a.org, a.end_date, a.url
        FROM matches m
        JOIN customers c ON c.id = m.customer_id
        JOIN announcements a ON a.id = m.announcement_id
        WHERE a.end_date BETWEEN ? AND ?
          AND m.notified = 0
    """, (today, deadline))
    rows = cur.fetchall()

    for row in rows:
        customer_name = row[1]
        msg = (
            f"⏰ **[GrantAI 마감 임박]** {customer_name}님\n"
            f"**{row[2]}** ({row[3]}) 마감 D-7 이내!\n"
            f"마감일: {row[4]} → {row[5]}"
        )
        payload = {"content": msg}
        async with httpx.AsyncClient() as client:
            try:
                await client.post(DISCORD_WEBHOOK, json=payload, timeout=10)
            except Exception:
                pass
        # 알림 완료 표시
        cur.execute("UPDATE matches SET notified = 1 WHERE customer_id = ? AND announcement_id = ?", (row[0], row[2]))

    con.commit()
    con.close()
    log.info("마감 임박 리마인더 %d건 발송", len(rows))


# ─────────────────────────────────────────
# 전체 크롤링 실행
# ─────────────────────────────────────────

async def run_crawler():
    """전체 공고 수집 → 고객 매칭 → 알림"""
    init_db()
    log.info("=== GrantAI 공고 크롤러 시작 ===")

    async with httpx.AsyncClient(headers={"User-Agent": "GrantAI/2.0"}) as client:
        # 1. 공고 수집
        tasks = [
            fetch_bizinfo(client, page=1),
            fetch_bizinfo(client, page=2),
            fetch_data_go_kr(client, page=1),
            fetch_kstartup(client),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_items = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                log.warning("수집 오류 (task %d): %s", i, result)
                continue
            if i < 2:  # bizinfo
                all_items.extend([normalize_bizinfo(r) for r in result])
            elif i == 2:  # data.go.kr
                all_items.extend([normalize_data_go_kr(r) for r in result])
            # k-startup은 현재 빈 리스트

        new_count = upsert_announcements(all_items)
        log.info("신규 공고 %d건 저장 (전체 수집: %d건)", new_count, len(all_items))

    # 2. 고객별 매칭 & 알림
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT id, name, industry, keywords FROM customers")
    customers = cur.fetchall()
    con.close()

    for (cust_id, name, industry, keywords) in customers:
        customer = {"id": cust_id, "name": name, "industry": industry, "keywords": keywords}
        matches = match_announcements_for_customer(customer)
        if matches:
            new_matches = save_matches(cust_id, matches)
            if new_matches:
                await notify_discord(name, new_matches)
                log.info("고객 [%s] 신규 매칭 %d건 알림", name, len(new_matches))

    # 3. 마감 임박 리마인더
    await send_deadline_reminders()
    log.info("=== 크롤러 완료 ===")


# ─────────────────────────────────────────
# 고객 등록 헬퍼 (API 서버에서 호출)
# ─────────────────────────────────────────

def register_customer(name: str, industry: str, keywords: list[str], email: str = "", discord_id: str = "") -> int:
    init_db()
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        INSERT INTO customers (name, industry, keywords, email, discord_id)
        VALUES (?, ?, ?, ?, ?)
    """, (name, industry, json.dumps(keywords, ensure_ascii=False), email, discord_id))
    cust_id = cur.lastrowid
    con.commit()
    con.close()
    log.info("고객 등록: %s (id=%d)", name, cust_id)
    return cust_id


def get_customer_matches(customer_id: int, limit: int = 10) -> list[dict]:
    """고객의 최근 매칭 공고 조회"""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        SELECT a.id, a.title, a.org, a.category, a.end_date, a.amount, a.url, m.score, m.reason
        FROM matches m
        JOIN announcements a ON a.id = m.announcement_id
        WHERE m.customer_id = ?
        ORDER BY m.score DESC, m.created_at DESC
        LIMIT ?
    """, (customer_id, limit))
    rows = cur.fetchall()
    con.close()
    keys = ["id", "title", "org", "category", "end_date", "amount", "url", "score", "reason"]
    return [dict(zip(keys, row)) for row in rows]


if __name__ == "__main__":
    asyncio.run(run_crawler())
