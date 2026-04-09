# 빌드 가이드 (Framer/아임웹 30분 완성용)

대표님, 아래 가이드를 따라가시면 30분 안에 고퀄리티 랜딩페이지를 올리실 수 있습니다.

---

## 1. 디자인 컨셉 (Aesthetics)
- **Theme**: Dark Mode (배경: `#0A0A0A`)
- **Accent Color**: Electric Blue (`#007AFF`) 또는 Deep Purple (`#5856D6`)
- **Font**: Pretendard (추천) 또는 Noto Sans KR (Bold/ExtraBold)

## 2. 섹션별 배치 가이드

### **Section 1: Hero (배경 이미지 활용)**
- **배경**: 생성된 `landing_page_hero_mockup` 이미지를 사용하여 시각적 임팩트를 줍니다.
- **텍스트 배치**: 이미지가 좌측 정렬이므로 텍스트 블록은 정중앙 또는 좌측 하단에 배치하세요.
- **버튼**: '네온 효과'가 들어간 Primary CTA 버튼을 배치합니다.

### **Section 2: Problem (Comparison)**
- **Layout**: 2-Column 그리드
- **Left**: "기존 방식" (흑백 처리, 복잡한 HWP 화면 캡쳐, '15시간 소요' 텍스트)
- **Right**: "우리 방식" (컬러 강조, 깔끔한 AI UI, '1시간 소요' 텍스트)

### **Section 3: Feature Cards**
- **Layout**: 3-Column 카드 레이아웃
- **Effect**: Hover 시 카드가 살짝 위로 올라가는 마이크로 인터랙션 추가 (Framer에서 Hover State 사용)

### **Section 4: Pricing (Floating Card)**
- **Layout**: 화면 중앙에 떠 있는 듯한 Glassmorphism 카드
- **배경**: `rgba(255, 255, 255, 0.05)`와 `backdrop-filter: blur(20px)` 적용
- **Stripe 결제 링크**: CTA 버튼에 바로 연결 (Conversation 174d0728 참고)

---

## 3. 빠른 완성을 위한 팁
1. **Framer 사용자**: 'Framer Components'에서 'Hero Section' 템플릿을 끌어온 뒤 텍스트와 이미지만 교체하세요.
2. **아임웹 사용자**: '섹션 추가' -> '이미지-텍스트' 조합을 활용하고, 배경색을 검은색으로 고정한 뒤 버튼 디자인만 커스텀하세요.

---

## [참고] 생성된 히어로 이미지
![Landing Page Hero Mockup](file:///Users/kang-yeonjun/.gemini/antigravity/brain/1fa067a5-0657-4751-95eb-d2b82d6b4103/landing_page_hero_mockup_1775746519622.png)
