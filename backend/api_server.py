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
import re
import io
import json
import base64
import asyncio
import tempfile
from pathlib import Path
from typing import Optional, AsyncGenerator

from google import genai
from google.genai import types as genai_types
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# reportlab PDF 생성
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# 한글 폰트 등록 (최초 1회)
_KO_FONT = "Helvetica"
for _fp in ["/System/Library/Fonts/Supplemental/AppleGothic.ttf",
            "/Library/Fonts/AppleGothic.ttf",
            "/System/Library/Fonts/AppleSDGothicNeo.ttc"]:
    if os.path.exists(_fp):
        try:
            pdfmetrics.registerFont(TTFont("KO", _fp))
            _KO_FONT = "KO"
            break
        except Exception:
            pass

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
# PDF 생성 유틸
# ─────────────────────────────────────────

def _pdf_style(name, **kw):
    defaults = dict(fontName=_KO_FONT, fontSize=10, leading=17, spaceAfter=4)
    defaults.update(kw)
    return ParagraphStyle(name, **defaults)

_PDF_STYLES = {
    "T":  _pdf_style("T",  fontSize=18, leading=26, spaceAfter=6, alignment=1,
                     textColor=colors.HexColor("#003366")),
    "H1": _pdf_style("H1", fontSize=13, leading=22, spaceAfter=6, spaceBefore=14,
                     textColor=colors.HexColor("#003366")),
    "H2": _pdf_style("H2", fontSize=11, leading=19, spaceAfter=5, spaceBefore=10,
                     textColor=colors.HexColor("#1a3a5c")),
    "BD": _pdf_style("BD", fontSize=9.5, leading=16, spaceAfter=3),
    "MT": _pdf_style("MT", fontSize=8.5, leading=14, textColor=colors.HexColor("#64748b")),
}

def _clean_pdf(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"\*+", "", s)
    s = re.sub(r"#{1,6}\s*", "", s)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").strip()

def generate_pdf_bytes(proposal_text: str, company_name: str = "사업계획서") -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=22*mm, rightMargin=22*mm,
                            topMargin=28*mm, bottomMargin=28*mm)
    S = _PDF_STYLES
    story = []

    # 표지
    story.append(Spacer(1, 10*mm))
    story.append(Paragraph("사  업  계  획  서", S["T"]))
    story.append(Spacer(1, 4*mm))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#003366")))
    story.append(Spacer(1, 6*mm))
    cover = [["기업명", company_name], ["작성일", "AI 자동 작성 (GrantAI)"]]
    ct = Table(cover, colWidths=[38*mm, 120*mm])
    ct.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), _KO_FONT), ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef2ff")),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#003366")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(ct)
    story.append(Spacer(1, 8*mm))

    # 본문 파싱
    for line in proposal_text.split("\n"):
        s = line.strip()
        if not s:
            story.append(Spacer(1, 2.5*mm))
            continue
        c = _clean_pdf(s)
        if not c:
            continue
        if s.startswith("---"):
            story.append(HRFlowable(width="100%", thickness=0.4,
                                    color=colors.HexColor("#e2e8f0")))
        elif s.startswith("|"):
            story.append(Paragraph(c, S["MT"]))
        elif re.match(r"^#{1,2}\s", s):
            story.append(Paragraph(c, S["H1"]))
        elif re.match(r"^#{3,}\s", s):
            story.append(Paragraph(c, S["H2"]))
        elif s.startswith(("□", "○")):
            story.append(Paragraph(c, S["H2"]))
        elif s.startswith(("- ", "* ", "▪", "◦")):
            story.append(Paragraph("\u00a0\u00a0\u00a0" + c, S["BD"]))
        else:
            story.append(Paragraph(c, S["BD"]))

    doc.build(story)
    return buf.getvalue()


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

class PTGenerationRequest(BaseModel):
    company_info: dict
    proposal_text: str


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
    # PDF 생성 후 base64 첨부
    try:
        pdf_bytes = generate_pdf_bytes(
            result["proposal_text"],
            req.company_info.get("company_name", "사업계획서"),
        )
        result["pdf_b64"] = base64.b64encode(pdf_bytes).decode()
    except Exception as e:
        result["pdf_b64"] = None
        result["pdf_error"] = str(e)
    return result


# ─────────────────────────────────────────
# SSE 스트리밍 계획서 생성 (실시간 진행률)
# ─────────────────────────────────────────

@app.post("/generate-stream")
async def generate_proposal_stream(req: GenerateRequest):
    """
    SSE 스트리밍: 생성 단계마다 progress 이벤트 → 완료 시 done 이벤트 (pdf_b64 포함)
    """
    if not GEMINI_API_KEY:
        raise HTTPException(503, "GEMINI_API_KEY 미설정")

    async def event_stream() -> AsyncGenerator[str, None]:
        queue: asyncio.Queue = asyncio.Queue()

        async def progress_cb(event: dict):
            await queue.put(event)

        async def run():
            try:
                result = await generate_proposal_with_refinement(
                    company_info=req.company_info,
                    announcement_id=req.announcement_id,
                    run_refinement=req.run_refinement,
                    progress_cb=progress_cb,
                )
                try:
                    pdf_bytes = generate_pdf_bytes(
                        result["proposal_text"],
                        req.company_info.get("company_name", "사업계획서"),
                    )
                    result["pdf_b64"] = base64.b64encode(pdf_bytes).decode()
                except Exception as pe:
                    result["pdf_b64"] = None
                    result["pdf_error"] = str(pe)
                await queue.put({"type": "done", **result})
            except Exception as e:
                await queue.put({"type": "error", "message": str(e)})

        task = asyncio.create_task(run())

        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=360)
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                    if event.get("type") in ("done", "error"):
                        break
                except asyncio.TimeoutError:
                    yield 'data: {"type":"error","message":"timeout"}\n\n'
                    break
        finally:
            task.cancel()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ─────────────────────────────────────────
# 점수 미리보기 (무료 — 점수/등급만 반환, 상세는 유료)
# ─────────────────────────────────────────

class ScorePreviewRequest(BaseModel):
    company_info: dict
    announcement_id: str = ""

@app.post("/score-preview")
async def score_preview(req: ScorePreviewRequest):
    """
    무료 점수 미리보기: 예상 점수 + 등급만 반환
    상세 강점/약점/보완방법은 프로 구독자 전용 (/generate 사용)
    """
    if not GEMINI_API_KEY:
        raise HTTPException(503, "GEMINI_API_KEY 미설정")

    client = genai.Client(api_key=GEMINI_API_KEY)

    # 회사 정보 기반 간단한 점수 예측 (Flash 모델로 빠르게)
    company_text = json.dumps(req.company_info, ensure_ascii=False)
    prompt = f"""다음 회사 정보를 바탕으로 정부지원사업 합격 가능성을 평가하세요.

회사 정보:
{company_text}

다음 JSON만 반환:
{{
  "score": 72,
  "grade": "B+",
  "pass_probability": 0.68,
  "one_line_feedback": "기술성 강점이나 시장성 데이터 보강 필요"
}}"""

    try:
        resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        raw = resp.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        return {
            "score": data.get("score", 70),
            "grade": data.get("grade", "B"),
            "pass_probability": data.get("pass_probability", 0.6),
            "one_line_feedback": data.get("one_line_feedback", ""),
            "upgrade_hint": f"점수를 {data.get('score', 70) + 8}점으로 높이는 3가지 방법 → 프로에서 확인",
        }
    except Exception:
        return {"score": 70, "grade": "B", "pass_probability": 0.60,
                "one_line_feedback": "기본 평가 완료", "upgrade_hint": "상세 보완 방법 → 프로에서 확인"}


# ─────────────────────────────────────────
# PT 스크립트 및 Q&A 비동기 생성 엔드포인트
# ─────────────────────────────────────────

from .proposal_generator import generate_pt_script_and_qa_background

@app.post("/generate-pt-script")
async def generate_pt_script(req: PTGenerationRequest):
    """
    비동기 PT 스크립트 생성: 유저가 화면을 보는 동안 백그라운드에서 실행
    """
    if not GEMINI_API_KEY:
        raise HTTPException(503, "GEMINI_API_KEY 미설정")
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    result = await generate_pt_script_and_qa_background(
        client=client,
        company_info=req.company_info,
        proposal_text=req.proposal_text
    )
    return result


# ─────────────────────────────────────────
# 인증 (로그인 / 회원가입)
# ─────────────────────────────────────────

import hmac, hashlib, time

_SECRET = "grantai-secret-2026"
_USERS = {
    "dev@grantai.io": {"password": "Grant2026!", "role": "dev",   "name": "개발자"},
}

def _make_token(email: str, role: str) -> str:
    payload = f"{email}:{role}:{int(time.time())}"
    sig = hmac.new(_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{payload}:{sig}"

def _verify_token(token: str) -> Optional[dict]:
    try:
        parts = token.rsplit(":", 1)
        if len(parts) != 2:
            return None
        payload, sig = parts
        expected = hmac.new(_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()[:16]
        if not hmac.compare_digest(sig, expected):
            return None
        email, role, ts = payload.split(":")
        return {"email": email, "role": role}
    except Exception:
        return None

class LoginRequest(BaseModel):
    email: str
    password: str

class SignupRequest(BaseModel):
    name: str
    email: str
    password: str

@app.post("/auth/login")
def auth_login(req: LoginRequest):
    user = _USERS.get(req.email)
    if not user or user["password"] != req.password:
        raise HTTPException(401, "이메일 또는 비밀번호가 틀렸습니다")
    token = _make_token(req.email, user["role"])
    return {"token": token, "role": user["role"], "name": user["name"], "email": req.email}

@app.post("/auth/signup")
def auth_signup(req: SignupRequest):
    if req.email in _USERS:
        raise HTTPException(409, "이미 가입된 이메일입니다")
    if len(req.password) < 6:
        raise HTTPException(400, "비밀번호는 6자 이상이어야 합니다")
    _USERS[req.email] = {"password": req.password, "role": "user", "name": req.name}
    token = _make_token(req.email, "user")
    return {"token": token, "role": "user", "name": req.name, "email": req.email}

@app.get("/auth/me")
def auth_me(token: str = ""):
    user = _verify_token(token)
    if not user:
        raise HTTPException(401, "Invalid token")
    return user


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
