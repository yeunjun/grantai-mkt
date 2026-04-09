// Interactivity for Landing Page

document.addEventListener('DOMContentLoaded', () => {
    // Reveal animations on scroll
    const observerOptions = {
        threshold: 0.1
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('reveal');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    document.querySelectorAll('.feature-card, .comparison-card, .pricing-card').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'all 0.6s ease-out';
        observer.observe(el);
    });

    // Add reveal class style via JS for simplicity or use CSS
    const style = document.createElement('style');
    style.innerHTML = `
        .reveal {
            opacity: 1 !important;
            transform: translateY(0) !important;
        }
    `;
    document.head.appendChild(style);

    // Mock "Slot" counter update
    let slots = 3;
    const slotsFill = document.querySelector('.slots-fill');
    const slotsText = document.querySelector('.pricing-desc');

    // Simulate occasional updates
    setInterval(() => {
        if (slots === 1) return;
        if (Math.random() < 0.1) {
            slots--;
            slotsText.innerHTML = `현재 ${10 - slots}개 기업 신청 완료 (남은 자리: ${slots}개)`;
            slotsFill.style.width = `${(10 - slots) * 10}%`;
            
            // Highlight pulse on change
            slotsText.style.color = '#fff';
            setTimeout(() => slotsText.style.color = 'var(--neon-pink)', 1000);
        }
    }, 10000);
});
