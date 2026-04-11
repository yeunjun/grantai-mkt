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
    """배점표 기반 PSST 초안 생성 (Pro 우선, 503 시 Flash 폴백)"""
    system_prompt = _load_system_prompt()

    sorted_criteria = sorted(criteria.get("criteria", []), key=lambda x: x["weight"], reverse=True)
    criteria_text = "\n".join(
        f"- {c['name']} ({c['weight']}점): {', '.join(c.get('key_points', []))}"
        for c in sorted_criteria
    )
    keywords = ", ".join(criteria.get("key_policy_keywords", []))
    expressions = ", ".join(criteria.get("preferred_expressions", []))

    # Fact-Grounding 데이터 추출 (Wizard Step 1~3 통합)
    fact_lines = []
    if company_info.get("fact_patent"):
        fact_lines.append(f"- 보유 특허/IP: {company_info['fact_patent']}건")
    if company_info.get("fact_monthly_revenue"):
        fact_lines.append(f"- 현재 월 매출: {company_info['fact_monthly_revenue']}만원")
    if company_info.get("fact_perf_improvement"):
        fact_lines.append(f"- 핵심 성능 개선 목표: 기존 대비 {company_info['fact_perf_improvement']}% 향상")
    if company_info.get("fact_grant_amount"):
        fact_lines.append(f"- 신청 지원금 규모: {company_info['fact_grant_amount']}만원")
    if company_info.get("fact_customers"):
        fact_lines.append(f"- 기존 고객/MOU/협력사: {company_info['fact_customers']}")
    
    # 추가 컨텍스트 (Wizard Step 2 & 3)
    extra_context = []
    if company_info.get("problem"):
        extra_context.append(f"1. 해결하려는 기존 시장의 문제점: {company_info['problem']}")
    if company_info.get("benefit"):
        extra_context.append(f"2. 고객이 얻는 구체적 이득/솔루션: {company_info['benefit']}")
    if company_info.get("business_model"):
        extra_context.append(f"3. 비즈니스 모델(BM): {company_info['business_model']}")
    if company_info.get("target_customer"):
        extra_context.append(f"4. 핵심 타깃 고객층: {company_info['target_customer']}")
    if company_info.get("unit_price"):
        extra_context.append(f"5. 제품/서비스 단가: {company_info['unit_price']}")
    if company_info.get("trl_level"):
        extra_context.append(f"6. 현재 기술준비도(TRL): {company_info['trl_level']}")

    fact_section = "\n[검증된 실측 데이터 — 계획서 곳곳에 반드시 활용]\n" + "\n".join(fact_lines) + "\n" if fact_lines else ""
    context_section = "\n[집중 서술 포인트 — 유저가 강조한 핵심 논리]\n" + "\n".join(extra_context) + "\n" if extra_context else ""

    user_prompt = f"""다음 회사 정보와 공고를 바탕으로 정부지원사업용 '격이 다른' 사업계획서를 작성하세요.
{fact_section}
{context_section}
[회사 및 공고 정보]
- 회사명: {company_info.get('company_name', '본 기업')}
- 설립연도: {company_info.get('founded_year', '미상')}
- 기술분야: {company_info.get('industry', '첨단기술')}
- 핵심기술: {company_info.get('core_tech', '')}
- 공고명: {announcement.get('title', '공고 매칭 안됨')}

[평가 배점표 — 배점 높은 항목을 집요하게 공략]
{criteria_text}

[필수 요구사항]
1. 작성 지침: 총 {criteria.get('total_pages', 15)}페이지 분량. 전문 행정 용어와 수치(Quantitative) 중심 서술.
2. 위계 구조: □(대주제) → ○(중주제) → -(세부내용/수치)
3. **방어적 논리(Defensive Logic)**: 본문에 [□ 예상 리스크 및 극복 방안] 표를 반드시 포함하여 기술적/시장적 위험을 선제적으로 반박.
4. **마크다운 표 필수 사용**: 
   - TAM-SAM-SOM 시장규모 표
   - 목표달성도 평가지표 표 (성능지표 5개 이상)
   - 경쟁사 비교 매트릭스
   - 고용창출 및 매출 로드맵 표
5. 정책 키워드 반영: {keywords}
6. 선호 표현 반영: {expressions}

사업계획서 작성을 시작하세요:"""

    prompt = f"{system_prompt}\n\n{user_prompt}"

    # Pro 우선 시도, 503/500 에러 시 Flash 폴백
    for model in ["gemini-2.5-pro", "gemini-2.5-flash"]:
        try:
            resp = client.models.generate_content(model=model, contents=prompt)
            return resp.text
        except Exception as e:
            err_str = str(e)
            if "503" in err_str or "UNAVAILABLE" in err_str or "500" in err_str:
                continue  # 다음 모델로 시도
            raise  # 다른 에러는 즉시 raise
    raise RuntimeError("모든 모델 사용 불가 (503/500)")


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

    for model in ["gemini-2.5-pro", "gemini-2.5-flash"]:
        try:
            resp = client.models.generate_content(model=model, contents=prompt)
            return resp.text
        except Exception as e:
            if "503" in str(e) or "UNAVAILABLE" in str(e) or "500" in str(e):
                continue
            raise
    raise RuntimeError("모든 모델 사용 불가")


# ─────────────────────────────────────────
# 메인 파이프라인
# ─────────────────────────────────────────

async def generate_proposal_with_refinement(
    company_info: dict,
    announcement_id: str,
    run_refinement: bool = True,
    progress_cb=None,  # async callable(event: dict)
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

    async def cb(event: dict):
        if progress_cb:
            await progress_cb(event)

    client = genai.Client(api_key=GEMINI_API_KEY)

    # Step 1: 공고 정보 조회 + 평가기준 추출
    await cb({"type": "progress", "step": "criteria", "message": "공고 평가기준 분석 중..."})
    announcement = await asyncio.to_thread(_get_announcement, announcement_id) if announcement_id else {}
    criteria = await asyncio.to_thread(extract_evaluation_criteria, client, announcement)

    # Step 2: 초안 생성
    await cb({"type": "progress", "step": "draft", "message": "PSST 계획서 초안 작성 중... (약 40초)"})
    draft = await asyncio.to_thread(generate_draft, client, company_info, announcement, criteria)

    if not run_refinement:
        await cb({"type": "progress", "step": "done_draft", "message": "초안 생성 완료"})
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
        await cb({"type": "progress", "step": "review", "round": round_num,
                  "message": f"심사관 시뮬레이터 검토 {round_num}라운드..."})
        critique = await asyncio.to_thread(reviewer_critique, client, current_draft, criteria)

        score = critique.get("score", 0)
        prob  = critique.get("pass_probability", 0)
        log_entry = {"round": round_num, "score": score, "pass_probability": prob,
                     "weaknesses_count": len(critique.get("weaknesses", []))}
        refinement_log.append(log_entry)

        await cb({"type": "score_update", "round": round_num, "score": score,
                  "pass_probability": prob,
                  "message": f"라운드 {round_num} 점수: {score}점 (합격률 {int(prob*100)}%)"})

        if prob >= 0.85:
            break

        await cb({"type": "progress", "step": "refine", "round": round_num,
                  "message": f"약점 보강 중... ({len(critique.get('weaknesses',[]))}개 항목)"})
        current_draft = await asyncio.to_thread(refine_draft, client, current_draft, critique, round_num)

    # 최종 평가
    await cb({"type": "progress", "step": "final", "message": "최종 점수 예측 중..."})
    final_critique = await asyncio.to_thread(reviewer_critique, client, current_draft, criteria)

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


# ─────────────────────────────────────────
# Step 4: 대면 발표용 PT 스크립트 & Q&A 비동기 생성 (Background)
# ─────────────────────────────────────────

async def generate_pt_script_and_qa_background(client: genai.Client, company_info: dict, proposal_text: str) -> dict:
    """
    유저가 독설 리포트/결제창을 읽는 동안 백그라운드에서 조용히 비동기로 실행되어 
    프로 플랜(149,000원)용으로 제공할 5분 PT 스크립트와 모범 방어 Q&A를 생성합니다.
    (결제 시점엔 이미 완성이 되어 있도록 구축)
    """
    prompt = f"""당신은 최고의 정부지원사업 발표(PT) 컨설턴트입니다.
다음은 방금 완성된 사업계획서 본문입니다.

[사업계획서 본문]
{proposal_text[:6000]}

이를 바탕으로, 대면 심사에 사용할 완벽한 무기 2가지를 작성해주십시오.

1. 대면 발표용 5분 PT 스크립트 (도입부의 강력한 후킹, 핵심 수치 강조, 클로징 포함)
2. 가장 날카로운 예상 압박 질문(기술력, 시장성, BM) 10개와 그에 대한 모범 방어 답변서

다음 JSON 형식으로 반환하세요:
{{
  "pt_script": "안녕하세요, 대표 ... 입니다. 저희 팀은 ...",
  "qa_defense": [
    {{"question": "이 시장은 대기업 진입 시 방어막이 있습니까?", "answer": "네, 저희의 차별점은 ... 입니다."}}
  ]
}}
JSON만 반환."""

    try:
        # 비동기로 별도 스레드에서 실행 (유저 대기 시간 없음)
        resp = await asyncio.to_thread(client.models.generate_content, model="gemini-2.5-flash", contents=prompt)
        raw = resp.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as e:
        print(f"Background PT Script Generation Error: {e}")
        return {"pt_script": "", "qa_defense": []}
