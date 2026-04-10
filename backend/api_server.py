"""
GrantAI — FastAPI 백엔드 서버 (Phase 2B)

엔드포인트:
  POST /upload      — 파일 업로드 + Claude Vision 분석
  POST /match       — 고객 등록 + 공고 즉시 매칭
  GET  /matches     — 고객 매칭 공고 조회
  POST /generate    — 사업계획서 생성 (Self-Refinement 포함)
  GET  /health      — 헬스체크

실행:
  pip install fastapi uvicorn python-multipart httpx anthropic
  uvicorn backend.api_server:app --reload --port 8000
"""

import os
import json
import base64
import asyncio
import tempfile
from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types as genai_types
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .announcement_crawler import (
    init_db, register_customer, get_customer_matches,
    match_announcements_for_customer, save_matches, notify_discord, run_crawler
)
from .processor import BureaucraticBrain
from .proposal_generator import generate_proposal_with_refinement

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

app = FastAPI(title="GrantAI API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()
brain = BureaucraticBrain()


# ─────────────────────────────────────────
# Pydantic 모델
# ─────────────────────────────────────────

class MatchRequest(BaseModel):
    name: str
    industry: str
    keywords: list[str]
    description: str = ""
    email: str = ""
    discord_id: str = ""

class GenerateRequest(BaseModel):
    customer_id: int
    announcement_id: str
    company_info: dict          # name, industry, core_tech, team, revenue 등
    run_refinement: bool = True # Self-Refinement 3라운드 실행 여부


# ─────────────────────────────────────────
# 파일 업로드 + Claude Vision 분석
# ─────────────────────────────────────────

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    PDF / HWP / DOCX 업로드 → Claude Vision으로 회사 정보 추출
    Returns: {name, industry, core_tech, market, team, keywords}
    """
    if not GEMINI_API_KEY:
        raise HTTPException(503, "GEMINI_API_KEY 미설정")

    content = await file.read()
    ext = Path(file.filename or "").suffix.lower()
    client = genai.Client(api_key=GEMINI_API_KEY)
    extract_prompt = (
        "이 문서에서 회사/사업 정보를 추출해 JSON으로 반환하세요.\n"
        "형식: {\"company_name\": \"\", \"industry\": \"\", \"core_tech\": \"\", "
        "\"market_description\": \"\", \"team_size\": \"\", \"revenue\": \"\", "
        "\"keywords\": [], \"strengths\": []}\n"
        "JSON만 반환, 추가 텍스트 없이."
    )

    # PDF — Gemini File API로 업로드 후 분석
    if ext == ".pdf":
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        uploaded = client.files.upload(file=tmp_path)
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[uploaded, extract_prompt],
        )
        os.unlink(tmp_path)
    else:
        # HWP/DOCX — 텍스트 추출 후 분석
        text = content.decode("utf-8", errors="ignore")[:8000]
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"{extract_prompt}\n\n텍스트:\n{text}",
        )

    raw = resp.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)


# ─────────────────────────────────────────
# 고객 등록 + 공고 즉시 매칭
# ─────────────────────────────────────────

@app.post("/match")
async def match_grants(req: MatchRequest):
    """
    고객 정보 등록 → 즉시 공고 매칭 → 상위 5건 반환
    """
    cust_id = register_customer(
        name=req.name,
        industry=req.industry,
        keywords=req.keywords,
        email=req.email,
        discord_id=req.discord_id,
    )

    customer = {
        "id": cust_id,
        "name": req.name,
        "industry": req.industry,
        "keywords": json.dumps(req.keywords, ensure_ascii=False),
    }
    matches = match_announcements_for_customer(customer)
    new_matches = save_matches(cust_id, matches)

    # 신규 매칭이면 Discord 알림
    if new_matches:
        asyncio.create_task(notify_discord(req.name, new_matches))

    # 전체 매칭 공고 반환
    all_matches = get_customer_matches(cust_id, limit=10)
    return {
        "customer_id": cust_id,
        "total_matches": len(all_matches),
        "matches": all_matches,
    }


# ─────────────────────────────────────────
# 고객 매칭 공고 조회
# ─────────────────────────────────────────

@app.get("/matches/{customer_id}")
def get_matches(customer_id: int, limit: int = 10):
    matches = get_customer_matches(customer_id, limit=limit)
    return {"customer_id": customer_id, "matches": matches}


# ─────────────────────────────────────────
# 사업계획서 생성 (Self-Refinement)
# ─────────────────────────────────────────

@app.post("/generate")
async def generate_proposal(req: GenerateRequest):
    """
    공고 + 회사 정보 → PSST 계획서 초안 → Self-Refinement 3라운드
    Returns: {proposal_text, score_prediction, weaknesses, pdf_b64}
    """
    if not GEMINI_API_KEY:
        raise HTTPException(503, "GEMINI_API_KEY 미설정")

    result = await generate_proposal_with_refinement(
        company_info=req.company_info,
        announcement_id=req.announcement_id,
        run_refinement=req.run_refinement,
    )
    return result


# ─────────────────────────────────────────
# 헬스체크
# ─────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0"}


# ─────────────────────────────────────────
# 크롤러 수동 트리거 (관리자용)
# ─────────────────────────────────────────

@app.post("/admin/crawl")
async def trigger_crawl():
    asyncio.create_task(run_crawler())
    return {"status": "크롤러 시작됨 (백그라운드)"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api_server:app", host="0.0.0.0", port=8000, reload=True)
