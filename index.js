/* ==========================================
   GrantAI — Landing Page JavaScript
   ========================================== */

// ── 설정 ──
const CONFIG = {
  tossLink:   'https://pay.toss.im/PLACEHOLDER',
  kakaoLink:  'https://open.kakao.com/o/PLACEHOLDER',
  appLink:    'https://yeunjun.github.io/grantai-mkt/app/',
  totalFreeSlots: 100,
  usedFreeSlots:  14,
};

// ==========================================
// 0. 프리미엄 커스텀 커서
// ==========================================
function initCustomCursor() {
  const dot = document.createElement('div');
  const outline = document.createElement('div');
  dot.className = 'cursor-dot';
  outline.className = 'cursor-outline';
  document.body.appendChild(dot);
  document.body.appendChild(outline);

  window.addEventListener('mousemove', (e) => {
    const { clientX, clientY } = e;
    dot.style.transform = `translate(${clientX - 4}px, ${clientY - 4}px)`;
    // Slight delay for outline
    outline.style.transform = `translate(${clientX - 20}px, ${clientY - 20}px)`;
  });

  // Hover effect on links
  document.querySelectorAll('a, button, .sample-card').forEach(el => {
    el.addEventListener('mouseenter', () => outline.style.transform += ' scale(1.5)');
    el.addEventListener('mouseleave', () => outline.style.transform = outline.style.transform.replace(' scale(1.5)', ''));
  });
}

// ==========================================
// 1. 스카시티 카운터 (날짜 기반 동적 계산 → 신뢰도 ↑)
// ==========================================
function initScarcityCounter() {
  const remaining = CONFIG.totalFreeSlots - CONFIG.usedFreeSlots;
  const els = document.querySelectorAll('#slots-counter, #final-slots');
  els.forEach(el => {
    if (el) el.textContent = remaining;
  });

  // 남은 숫자가 20 이하면 경고 스타일
  if (remaining <= 20) {
    document.querySelectorAll('.scarcity-bar').forEach(el => {
      el.style.background = 'rgba(239,68,68,0.15)';
      el.style.borderColor = 'rgba(239,68,68,0.4)';
    });
  }
}

// ==========================================
// 2. Scroll Reveal 애니메이션
// ==========================================
function initScrollReveal() {
  const revealEls = document.querySelectorAll('.reveal');

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.12, rootMargin: '0px 0px -48px 0px' }
  );

  revealEls.forEach(el => observer.observe(el));
}

// ==========================================
// 3. 네비게이션 스크롤 효과
// ==========================================
function initNav() {
  const nav = document.getElementById('nav');
  let lastScroll = 0;

  window.addEventListener('scroll', () => {
    const scrollY = window.scrollY;

    if (scrollY > 80) {
      nav.style.background = 'rgba(8,8,16,0.92)';
    } else {
      nav.style.background = 'rgba(8,8,16,0.7)';
    }

    // Hide on scroll down, show on scroll up
    if (scrollY > lastScroll && scrollY > 200) {
      nav.style.transform = 'translateY(-100%)';
    } else {
      nav.style.transform = 'translateY(0)';
    }
    lastScroll = scrollY;
  }, { passive: true });
}

// ==========================================
// 4. FAQ 아코디언
// ==========================================
function toggleFAQ(id) {
  const item = document.getElementById(id);
  if (!item) return;

  const isOpen = item.classList.contains('open');

  // 모두 닫기
  document.querySelectorAll('.faq-item').forEach(el => {
    el.classList.remove('open');
    const btn = el.querySelector('.faq-question');
    if (btn) btn.setAttribute('aria-expanded', 'false');
  });

  // 클릭한 것 열기 (이미 열려있으면 닫음)
  if (!isOpen) {
    item.classList.add('open');
    const btn = item.querySelector('.faq-question');
    if (btn) btn.setAttribute('aria-expanded', 'true');
  }
}

// ==========================================
// 5. 이미지 모달
// ==========================================
function openModal(src) {
  const modal = document.getElementById('imgModal');
  const img = document.getElementById('modalImg');
  if (!modal || !img) return;

  img.src = src;
  modal.classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeModal(e) {
  // backdrop 클릭이거나 버튼 클릭 시 닫기
  if (e && e.target !== document.getElementById('imgModal') && !e.target.classList.contains('modal-close')) return;
  const modal = document.getElementById('imgModal');
  if (modal) modal.classList.remove('open');
  document.body.style.overflow = '';
}

// ESC 키로 모달 닫기
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    const modal = document.getElementById('imgModal');
    if (modal && modal.classList.contains('open')) {
      modal.classList.remove('open');
      document.body.style.overflow = '';
    }
  }
});

// ==========================================
// 6. CTA 핸들러
// ==========================================
function handlePaidCTA(e) {
  // 인라인 스크립트의 openApplyModal()이 window에 있으면 그것을 사용
  if (e) e.preventDefault();
  if (typeof window.openApplyModal === 'function') {
    window.openApplyModal();
  }
}

// 카카오 링크 적용
function initKakaoLinks() {
  const kakaoLinks = document.querySelectorAll('#kakao-link');
  kakaoLinks.forEach(link => {
    link.href = CONFIG.kakaoLink.includes('PLACEHOLDER')
      ? '#'
      : CONFIG.kakaoLink;
  });
}

// ==========================================
// 7. 무료 리드 폼 제출
// ==========================================
function handleLeadSubmit(e) {
  e.preventDefault();
  const email = document.getElementById('lead-email').value;

  // TODO: 실제 배포 시 Airtable / Google Sheets webhook으로 교체
  console.log('Lead captured:', email);

  // 폼 성공 UI
  const form = document.getElementById('lead-form');
  form.innerHTML = `
    <div style="text-align:center; padding:16px; color:#22c55e; font-weight:700; font-size:1rem;">
      ✅ 이메일 접수 완료! 매칭 결과를 곧 보내드립니다.
    </div>
  `;

  showToast('✅ 접수되었습니다! 곧 연락드리겠습니다.', 'success');
}

// ==========================================
// 8. 토스트 알림
// ==========================================
function showToast(message, type = 'info') {
  // 기존 토스트 제거
  const existing = document.querySelector('.toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.style.cssText = `
    position: fixed;
    bottom: 32px;
    left: 50%;
    transform: translateX(-50%) translateY(20px);
    background: ${type === 'success' ? '#166534' : '#1e1b4b'};
    border: 1px solid ${type === 'success' ? 'rgba(34,197,94,0.3)' : 'rgba(99,102,241,0.3)'};
    color: ${type === 'success' ? '#86efac' : '#c7d2fe'};
    padding: 14px 28px;
    border-radius: 50px;
    font-size: 0.875rem;
    font-weight: 600;
    font-family: inherit;
    z-index: 9999;
    opacity: 0;
    transition: opacity 0.3s ease, transform 0.3s ease;
    white-space: nowrap;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
  `;
  toast.textContent = message;
  document.body.appendChild(toast);

  // 애니메이션
  requestAnimationFrame(() => {
    toast.style.opacity = '1';
    toast.style.transform = 'translateX(-50%) translateY(0)';
  });

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(-50%) translateY(20px)';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// ==========================================
// 9. 숫자 카운트업 애니메이션 (히어로 stats)
// ==========================================
function animateCountUp(el, target, suffix = '') {
  const duration = 1200;
  const start = 0;
  const step = (timestamp) => {
    if (!el._startTime) el._startTime = timestamp;
    const progress = Math.min((timestamp - el._startTime) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3); // ease out cubic
    el.textContent = Math.floor(start + (target - start) * eased) + suffix;
    if (progress < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

function initStatCounters() {
  const statObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting && !entry.target._counted) {
        entry.target._counted = true;
        const el = entry.target;
        const raw = el.dataset.value;
        const suffix = el.dataset.suffix || '';
        if (raw) animateCountUp(el, parseInt(raw), suffix);
      }
    });
  }, { threshold: 0.5 });

  document.querySelectorAll('.stat-value[data-value]').forEach(el => {
    statObserver.observe(el);
  });
}

// ==========================================
// 10. 부드러운 앵커 스크롤
// ==========================================
function initSmoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      const href = this.getAttribute('href');
      if (href === '#') return;
      const target = document.querySelector(href);
      if (target) {
        e.preventDefault();
        const offset = 80; // nav height
        const top = target.getBoundingClientRect().top + window.scrollY - offset;
        window.scrollTo({ top, behavior: 'smooth' });
      }
    });
  });
}

// ==========================================
// 전역 노출 — onclick 속성에서 호출 가능하도록
// ==========================================
window.toggleFAQ = toggleFAQ;
window.handlePaidCTA = handlePaidCTA;
window.openModal = openModal;
window.closeModal = closeModal;
window.handleLeadSubmit = handleLeadSubmit;

// ==========================================
// INIT — DOM 준비 후 모든 모듈 실행
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
  initCustomCursor();
  initScarcityCounter();
  initScrollReveal();
  initNav();
  initKakaoLinks();
  initStatCounters();
  initSmoothScroll();

  // 페이지 로드 직후 hero 요소들 즉시 표시
  setTimeout(() => {
    document.querySelectorAll('.hero .reveal').forEach(el => {
      el.classList.add('visible');
    });
  }, 100);
});
