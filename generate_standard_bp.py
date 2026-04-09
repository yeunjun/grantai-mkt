import requests
import os

webhook_url = "https://discord.com/api/webhooks/1491822368681885837/sda4wQsNMOtLIqwS3QQcwQjXTjttm2slw-AHMFJ9LVjkcneQyYpyjoAuame_sCNG3xJR"

# 중기부 예비창업패키지 표준 양식 구조화
standard_content = """
【 2024년 예비창업패키지 사업계획서 】

□ 창업아이템명: 온디바이스 AI용 저전력 NPU 반도체 IP 설계 고도화

1. 문제인식 (Problem)
  1-1. 창업아이템의 배경 및 필요성
    ○ 현재 온디바이스 AI 시장은 기하급수적으로 성장 중이나, 기존 GPU의 전력 소모(TDP) 이슈로 하드웨어 제약 발생
    ○ 로봇 및 드론 등 배터리 기반 Edge 기기에서 실시간 추론을 위한 '초저전력 가속기' 부재
  1-2. 해결하고자 하는 현안 문제
    ○ 외산 IP(ARM 등)에 대한 높은 의존도 및 과도한 로열티 지출로 인한 수익성 악화

2. 해결방안 (Solution)
  2-1. 창업아이템의 사업화 전략
    ○ RISC-V 기반 고효율 아키텍처 설계를 통해 특정 벤더 종속성 완전 탈피 (비용 40% 절감)
    ○ Static/Dynamic 전력 제어 로직을 하드웨어 레벨에서 통합 구현
  2-2. 기술적 차별성 및 구현 방안
    ○ [차별화] 8-bit 정밀도 가변 연산을 통한 연산 속도 2배 향상 및 정확도 손실 0.5% 미만 유지

3. 성장전략 (Scale-up)
  3-1. 자금 조달 계획
    ○ 총 사업비 1억 5천만 원 (정부지원금 1억 원 + 자부담 5천만 원) 기반 MPW 공정 착수
  3-2. 로드맵 및 마케팅 전략
    ○ '26.Q4: TSMC 28nm 공정 Tape-out | '27.Q1: 시제품 실증 및 PoC 수행

4. 팀 구성 (Team)
  4-1. 대표자 및 핵심인력 보유역량
    ○ 대표자: OO대 반도체 설계 전공 및 해당 분야 5년 경력자
    ○ 핵심인력: RTL 설계 전문가 2명, 펌웨어 엔지니어 1명

본 문서는 GrantAI가 생성한 중기부 표준 양식 초안입니다.
"""

file_name = "2024_예비창업패키지_GrantAI_반도체설계_초안.pdf" # 확장자만 PDF로 (모바일 뷰어용)
with open(file_name, "w", encoding="utf-8") as f:
    f.write(standard_content)

# 파일 전송
with open(file_name, "rb") as f:
    files = {"file": (file_name, f)}
    data = {"content": "📢 **[중기부 표준 양식 맞춤]** 사업계획서 초안이 생성되었습니다.\n1.문제인식~4.팀구성까지 실제 양식 구조를 준수했습니다."}
    requests.post(webhook_url, data=data, files=files)

print("SUCCESS")
