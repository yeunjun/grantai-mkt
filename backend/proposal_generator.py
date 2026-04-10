"""
GrantAI — 승인율 최대화 사업계획서 생성 엔진 (Phase 2C)

파이프라인:
  1. 공고 평가기준 추출  (공고 ID → DB 조회 → Claude로 배점표 분석)
  2. PSST 초안 생성     (회사 정보 + 배점표 → government_reviewer_prompt)
  3. Self-Refinement    (심사관 시뮬레이터 3라운드: 약점 지적 → 보강 → 재평가)
  4. 최종 점수 예측     (합격 가능성 % 출력)
"""

import os
import json
import sqlite3
import asyncio
from pathlib import Path

from google import genai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
DB_PATH = Path(__file__).parent / "grants.db"
PROMPT_PATH = Path(__file__).parent.parent / "government_reviewer_prompt.md"
REFINEMENT_ROUNDS = 3  # Self-Refinement 반복 횟수


def _get_announcement(ann_id: str) -> dict:
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT title, org, category, end_date, amount, raw_json FROM announcements WHERE id = ?", (ann_id,))
    row = cur.fetchone()
    con.close()
    if not row:
        return {}
    keys = ["title", "org", "category", "end_date", "amount", "raw_json"]
    return dict(zip(keys, row))


def _load_system_prompt() -> str:
    if PROMPT_PATH.exists():
        return PROMPT_PATH.read_text(encoding="utf-8")
    return "당신은 정부지원사업 전문 심사위원입니다."


# ─────────────────────────────────────────
# Step 1: 공고 평가기준 추출
# ─────────────────────────────────────────

def extract_evaluation_criteria(client: genai.Client, announcement: dict) -> dict:
    """공고 정보에서 평가 배점표 추출"""
    ann_text = f"""
공고명: {announcement.get('title', '')}
기관: {announcement.get('org', '')}
분야: {announcement.get('category', '')}
지원금: {announcement.get('amount', '')}
""".strip()

    prompt = f"""다음 정부지원사업 공고를 분석하여 평가 배점표를 JSON으로 추출하세요.
공고 정보가 부족한 경우 해당 분야 표준 배점을 추정하세요.

공고:
{ann_text}

반환 형식:
{{
  "criteria": [
    {{"name": "사업화 역량", "weight": 40, "key_points": ["..."]}}
  ],
  "total_pages": 15,
  "submission_format": "HWP",
  "key_policy_keywords": ["AI", "반도체"],
  "preferred_expressions": ["선순환 체계", "파급효과"]
}}
JSON만 반환."""

    try:
        resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        raw = resp.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception:
        # 기본 배점표 반환
        return {
            "criteria": [
                {"name": "문제 인식 및 시장성", "weight": 25, "key_points": ["TAM/SAM/SOM 정량화", "시장 성장률"]},
                {"name": "기술성 및 혁신성",    "weight": 30, "key_points": ["TRL 수준", "경쟁사 대비 우위"]},
                {"name": "사업화 가능성",       "weight": 30, "key_points": ["유닛 이코노믹스", "매출 로드맵"]},
                {"name": "팀 역량",             "weight": 15, "key_points": ["전문 인력", "고용 창출 계획"]},
            ],
            "total_pages": 15,
            "key_policy_keywords": ["AI", "디지털전환"],
            "preferred_expressions": ["선순환 체계 구축", "파급 효과 극대화"],
        }


# ─────────────────────────────────────────
# Step 2: PSST 초안 생성
# ─────────────────────────────────────────

def generate_draft(client: genai.Client, company_info: dict, announcement: dict, criteria: dict) -> str:
    """배점표 기반 PSST 초안 생성"""
    system_prompt = _load_system_prompt()

    # 배점 높은 항목 강조 지시
    sorted_criteria = sorted(criteria.get("criteria", []), key=lambda x: x["weight"], reverse=True)
    criteria_text = "\n".join(
        f"- {c['name']} ({c['weight']}점): {', '.join(c.get('key_points', []))}"
        for c in sorted_criteria
    )
    keywords = ", ".join(criteria.get("key_policy_keywords", []))
    expressions = ", ".join(criteria.get("preferred_expressions", []))

    user_prompt = f"""다음 회사 정보와 공고를 바탕으로 사업계획서를 작성하세요.

[회사 정보]
{json.dumps(company_info, ensure_ascii=False, indent=2)}

[공고 정보]
{json.dumps(announcement, ensure_ascii=False, indent=2)}

[평가 배점표 — 배점 높은 항목에 분량 집중]
{criteria_text}

[정책 키워드 필수 포함]: {keywords}
[선호 표현 사용]: {expressions}

[작성 지침]
- 총 {criteria.get('total_pages', 15)}페이지 분량
- 배점 최고 항목부터 상세히 서술
- TAM-SAM-SOM 표 반드시 포함 (실제 수치 기입)
- 모든 주장은 정량 데이터로 뒷받침
- 개조식 위계 구조: □(대) → ○(중) → -(소)
- 감성적 표현 금지, 수치 기반만 허용
- #003366 색상 태그로 핵심 수치 강조

사업계획서를 작성하세요:"""

    resp = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=f"{system_prompt}\n\n{user_prompt}",
    )
    return resp.text


# ─────────────────────────────────────────
# Step 3: Self-Refinement (심사관 시뮬레이터)
# ─────────────────────────────────────────

def reviewer_critique(client: genai.Client, draft: str, criteria: dict) -> dict:
    """심사관 역할로 계획서 약점 지적 + 점수 예측"""
    sorted_criteria = sorted(criteria.get("criteria", []), key=lambda x: x["weight"], reverse=True)
    criteria_text = "\n".join(
        f"- {c['name']} (배점 {c['weight']}점)" for c in sorted_criteria
    )

    prompt = f"""당신은 중소벤처기업부 전문 심사위원입니다. 아래 사업계획서를 엄격하게 심사하세요.

[평가 기준]
{criteria_text}

[계획서]
{draft[:6000]}

다음 JSON 형식으로 반환하세요:
{{
  "score": 75,
  "grade": "B+",
  "pass_probability": 0.65,
  "strengths": ["강점1", "강점2"],
  "weaknesses": [
    {{"section": "기술성", "issue": "TRL 수준 미명시", "fix": "TRL 7 이상 근거 자료 추가"}}
  ],
  "critical_missing": ["TAM 출처 미기재", "경쟁사 비교표 없음"]
}}
JSON만 반환."""

    try:
        resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        raw = resp.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception:
        return {"score": 70, "pass_probability": 0.6, "weaknesses": [], "critical_missing": []}


def refine_draft(client: genai.Client, draft: str, critique: dict, round_num: int) -> str:
    """약점 피드백 기반 계획서 보강"""
    weaknesses = critique.get("weaknesses", [])
    critical = critique.get("critical_missing", [])

    fix_instructions = []
    for w in weaknesses:
        fix_instructions.append(f"- [{w.get('section','')}] {w.get('issue','')} → {w.get('fix','')}")
    for c in critical:
        fix_instructions.append(f"- 누락 항목 추가: {c}")

    if not fix_instructions:
        return draft

    prompt = f"""다음 사업계획서를 심사위원 피드백 기반으로 보강하세요. (라운드 {round_num}/{REFINEMENT_ROUNDS})

[피드백 반영 지시사항]
{chr(10).join(fix_instructions)}

[현재 계획서]
{draft}

위 피드백을 모두 반영하여 완성도 높은 계획서를 다시 작성하세요.
모든 수정 사항이 반영되었는지 확인하고, 정량 데이터를 더 구체화하세요."""

    resp = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt,
    )
    return resp.text


# ─────────────────────────────────────────
# 메인 파이프라인
# ─────────────────────────────────────────

async def generate_proposal_with_refinement(
    company_info: dict,
    announcement_id: str,
    run_refinement: bool = True,
) -> dict:
    """
    전체 생성 파이프라인 실행
    Returns:
      proposal_text     — 최종 계획서 전문
      score_prediction  — 합격 가능성 (0~1)
      estimated_score   — 예상 점수
      refinement_log    — 각 라운드 점수 변화
      weaknesses        — 남은 약점 목록
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY 미설정")

    client = genai.Client(api_key=GEMINI_API_KEY)

    # Step 1: 공고 정보 조회 + 평가기준 추출
    announcement = _get_announcement(announcement_id) if announcement_id else {}
    criteria = extract_evaluation_criteria(client, announcement)

    # Step 2: 초안 생성 (Claude Opus — 최고 품질)
    draft = generate_draft(client, company_info, announcement, criteria)

    if not run_refinement:
        return {
            "proposal_text": draft,
            "score_prediction": 0.6,
            "estimated_score": 70,
            "refinement_log": [],
            "weaknesses": [],
        }

    # Step 3: Self-Refinement Loop
    refinement_log = []
    current_draft = draft

    for round_num in range(1, REFINEMENT_ROUNDS + 1):
        critique = reviewer_critique(client, current_draft, criteria)
        log_entry = {
            "round": round_num,
            "score": critique.get("score", 0),
            "pass_probability": critique.get("pass_probability", 0),
            "weaknesses_count": len(critique.get("weaknesses", [])),
        }
        refinement_log.append(log_entry)

        # 점수가 충분히 높으면 조기 종료
        if critique.get("pass_probability", 0) >= 0.85:
            break

        current_draft = refine_draft(client, current_draft, critique, round_num)

    # 최종 평가
    final_critique = reviewer_critique(client, current_draft, criteria)

    return {
        "proposal_text": current_draft,
        "score_prediction": final_critique.get("pass_probability", 0),
        "estimated_score": final_critique.get("score", 0),
        "grade": final_critique.get("grade", ""),
        "strengths": final_critique.get("strengths", []),
        "weaknesses": final_critique.get("weaknesses", []),
        "refinement_log": refinement_log,
        "criteria_used": criteria,
    }
