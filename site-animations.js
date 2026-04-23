(() => {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  let ticking = false;
  let lottieLoading = false;
  let curtainAnim = null;
  let curtainInitialized = false;

  function onScrollRaf(callback) {
    window.addEventListener('scroll', () => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        callback();
        ticking = false;
      });
    }, { passive: true });
  }

  function injectCSS() {
    if (document.getElementById('gn-anim-css')) return;
    const style = document.createElement('style');
    style.id = 'gn-anim-css';
    style.textContent = `
      .gn-curtain {
        position: fixed;
        inset: 0;
        z-index: 999998;
        background: #070b14;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 14px;
        pointer-events: none;
      }
      #gn-curtain-lottie {
        position: absolute;
        inset: 0;
        width: 100vw;
        height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      #gn-curtain-lottie svg {
        width: 100% !important;
        height: 100% !important;
        object-fit: cover;
      }
      .gn-curtain-logo {
        font-family: 'Syne', sans-serif;
        font-size: 1.15rem;
        font-weight: 800;
        color: #f0f4ff;
        letter-spacing: -0.02em;
        opacity: 0;
        animation: gnFadeIn 0.7s ease 0.4s forwards;
      }
      .gn-curtain-logo span { color: #9DD9F8; }
      .gn-curtain.gn-leaving {
        animation: gnCurtainOut 0.75s cubic-bezier(.76,0,.24,1) forwards;
      }
      @keyframes gnCurtainOut {
        0%   { clip-path: inset(0 0 0 0); }
        100% { clip-path: inset(0 0 100% 0); }
      }
      @keyframes gnFadeIn {
        to { opacity: 1; }
      }
    `;
    document.head.appendChild(style);
  }

  function loadLottieScript() {
    if (window.lottie || lottieLoading) return Promise.resolve();
    lottieLoading = true;
    return new Promise((resolve) => {
      const s = document.createElement('script');
      s.src = 'https://cdnjs.cloudflare.com/ajax/libs/bodymovin/5.12.2/lottie.min.js';
      s.onload = () => resolve();
      s.onerror = () => resolve();
      document.head.appendChild(s);
    });
  }

  function initCurtain() {
    if (reduceMotion) return;
    if (curtainInitialized) return;
    if (document.getElementById('gn-curtain-main')) return;
    const path = window.location.pathname.toLowerCase();
    const isHome = path.endsWith('/') || path.endsWith('/index.html') || path.endsWith('index.html');
    if (!isHome) return;
    curtainInitialized = true;
    window.__gnCurtainActive = true;

    const curtain = document.createElement('div');
    curtain.className = 'gn-curtain';
    curtain.id = 'gn-curtain-main';

    const lottieContainer = document.createElement('div');
    lottieContainer.id = 'gn-curtain-lottie';
    lottieContainer.style.cssText = `
      width: 100vw;
      height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
    `;

    curtain.appendChild(lottieContainer);
    document.body.prepend(curtain);

    let leaving = false;
    let animStartedAt = 0;
    let hardTimeoutId = null;
    const MIN_VISIBLE_MS = 1400;

    const leaveCurtain = () => {
      if (leaving) return;
      leaving = true;
      if (hardTimeoutId) {
        clearTimeout(hardTimeoutId);
        hardTimeoutId = null;
      }

      curtain.classList.add('gn-leaving');
      curtain.addEventListener('animationend', () => {
        if (curtainAnim) {
          curtainAnim.destroy();
          curtainAnim = null;
        }
        curtain.remove();
      }, { once: true });
    };

    const play = () => {
      if (!window.lottie) return;
      const isLight = document.documentElement.classList.contains('light-mode');
      const jsonFile = isLight ? 'logoremixbranca.json' : 'Logo-3-remix.json';
      try {
        if (curtainAnim) {
          curtainAnim.destroy();
          curtainAnim = null;
        }
        curtainAnim = window.lottie.loadAnimation({
          container: lottieContainer,
          renderer: 'svg',
          loop: false,
          autoplay: true,
          path: jsonFile,
          rendererSettings: {
            preserveAspectRatio: 'xMidYMid slice',
            clearCanvas: true,
          },
        });
        animStartedAt = performance.now();
        curtainAnim.addEventListener('complete', () => {
          const elapsed = Math.max(0, performance.now() - animStartedAt);
          const wait = Math.max(0, MIN_VISIBLE_MS - elapsed);
          setTimeout(leaveCurtain, wait);
        });

        // Fallback para evitar travar overlay se o evento complete não vier.
        hardTimeoutId = setTimeout(leaveCurtain, 12000);
      } catch (e) {
        setTimeout(leaveCurtain, 300);
      }
    };

    if (window.lottie) {
      play();
    } else {
      loadLottieScript().then(play);
    }

    // Fallback extra: se Lottie não carregar, fecha em tempo razoável.
    setTimeout(() => {
      if (!leaving && !window.lottie) {
        leaveCurtain();
      }
    }, 2500);
  }

  function initScrollProgress() {
    if (reduceMotion) return;

    if (!document.querySelector('.scroll-progress')) {
      const bar = document.createElement('div');
      bar.className = 'scroll-progress';
      document.body.appendChild(bar);
    }

    const setProgress = () => {
      const doc = document.documentElement;
      const scrollTop = doc.scrollTop || document.body.scrollTop;
      const max = (doc.scrollHeight - doc.clientHeight) || 1;
      const progress = Math.min(1, Math.max(0, scrollTop / max));
      doc.style.setProperty('--scroll-progress', `${progress * 100}%`);
    };

    setProgress();
    onScrollRaf(setProgress);
  }

  function initSectionMaskReveal() {
    if (reduceMotion || !('IntersectionObserver' in window)) return;

    const blocks = document.querySelectorAll('.page-hero, .secao, .stats-bar, .cta-section, .pagamento-wrapper');
    blocks.forEach((el) => el.classList.add('section-mask-reveal'));

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add('in-view');
          observer.unobserve(entry.target);
        });
      },
      { threshold: 0.12, rootMargin: '0px 0px -6% 0px' }
    );

    blocks.forEach((el) => observer.observe(el));
  }

  function splitWords(el) {
    if (!el || el.dataset.splitReady === '1') return;

    const text = el.textContent;
    if (!text || !text.trim()) return;

    const words = text.trim().split(/\s+/g);
    el.textContent = '';

    words.forEach((word, i) => {
      const span = document.createElement('span');
      span.className = 'word-reveal';
      span.style.transitionDelay = `${Math.min(i * 0.035, 0.5)}s`;
      span.textContent = word;
      el.appendChild(span);
      el.appendChild(document.createTextNode(' '));
    });

    el.dataset.splitReady = '1';
  }

  function initHeadingStagger() {
    if (reduceMotion || !('IntersectionObserver' in window)) return;

    const heads = document.querySelectorAll('.hero-titulo, .titulo-secao, .cta-titulo');
    heads.forEach(splitWords);

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add('words-in-view');
          observer.unobserve(entry.target);
        });
      },
      { threshold: 0.2 }
    );

    heads.forEach((el) => observer.observe(el));
  }

  function initRevealAnimations() {
    if (reduceMotion || !('IntersectionObserver' in window)) return;

    const targets = document.querySelectorAll(
      '.secao .card-glow, .secao .plano-card, .secao .faq-item, .secao .passo, .secao .nivel-card, .secao .valor-item, .secao .membro-card, .secao .stack-item, .secao .fluxo-item, .secao .problema-item, .secao .resumo-card, .secao .form-card, .stats-grid > div'
    );

    targets.forEach((el, idx) => {
      if (el.classList.contains('animar') || el.classList.contains('animar-2') || el.classList.contains('animar-3') || el.classList.contains('animar-4')) {
        return;
      }
      el.classList.add('reveal-on-scroll');
      el.classList.add(`reveal-stagger-${(idx % 4) + 1}`);
    });

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add('in-view');
          observer.unobserve(entry.target);
        });
      },
      { threshold: 0.14, rootMargin: '0px 0px -8% 0px' }
    );

    document.querySelectorAll('.reveal-on-scroll').forEach((el) => observer.observe(el));
  }

  function initMagneticButtons() {
    if (reduceMotion || window.matchMedia('(max-width: 900px)').matches) return;

    const buttons = document.querySelectorAll('.btn-primario, .btn-secundario, .btn-plano, .nav-cta');

    buttons.forEach((btn) => {
      btn.addEventListener('mousemove', (e) => {
        const rect = btn.getBoundingClientRect();
        const x = e.clientX - rect.left - rect.width / 2;
        const y = e.clientY - rect.top - rect.height / 2;
        btn.style.transform = `translate(${x * 0.08}px, ${y * 0.08}px)`;
      });

      btn.addEventListener('mouseleave', () => {
        btn.style.transform = '';
      });
    });
  }

  function initParallax() {
    if (reduceMotion || window.matchMedia('(max-width: 900px)').matches) return;

    const targets = document.querySelectorAll('.hero-orbe, .mini-card, .escudo-container, .problema-visual, .missao-visual');
    if (!targets.length) return;

    const update = () => {
      const y = window.scrollY;
      targets.forEach((el, idx) => {
        const speed = 0.015 + (idx % 4) * 0.01;
        const offset = (y * speed).toFixed(2);
        el.style.transform = `translate3d(0, ${offset}px, 0)`;
      });
    };

    update();
    onScrollRaf(update);
  }

  function initCardTilt() {
    if (reduceMotion || window.matchMedia('(max-width: 900px)').matches) return;

    const cards = document.querySelectorAll('.card-glow, .plano-card, .membro-card, .fluxo-item, .faq-item');

    cards.forEach((card) => {
      card.classList.add('tilt-surface');

      card.addEventListener('mousemove', (e) => {
        const rect = card.getBoundingClientRect();
        const px = (e.clientX - rect.left) / rect.width;
        const py = (e.clientY - rect.top) / rect.height;

        const ry = (px - 0.5) * 6;
        const rx = (0.5 - py) * 6;

        card.style.transform = `perspective(900px) rotateX(${rx.toFixed(2)}deg) rotateY(${ry.toFixed(2)}deg) translateY(-2px)`;
      });

      card.addEventListener('mouseleave', () => {
        card.style.transform = '';
      });
    });
  }

  function initCounters() {
    if (reduceMotion || !('IntersectionObserver' in window)) return;

    const counters = Array.from(document.querySelectorAll('.stat-numero'))
      .filter((el) => /^\d+%$|^\d+$/.test(el.textContent.trim()));

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;

        const el = entry.target;
        const original = el.textContent.trim();
        const isPercent = original.endsWith('%');
        const target = parseInt(original.replace(/\D/g, ''), 10);
        if (Number.isNaN(target)) return;

        let start = 0;
        const dur = 900;
        const t0 = performance.now();

        const tick = (now) => {
          const p = Math.min(1, (now - t0) / dur);
          const eased = 1 - Math.pow(1 - p, 3);
          start = Math.round(target * eased);
          el.textContent = isPercent ? `${start}%` : `${start}`;
          if (p < 1) requestAnimationFrame(tick);
        };

        requestAnimationFrame(tick);
        observer.unobserve(el);
      });
    }, { threshold: 0.55 });

    counters.forEach((el) => observer.observe(el));
  }

  function initFloatingAccents() {
    if (reduceMotion) return;

    const accents = document.querySelectorAll('.hero-orbe, .missao-visual, .problema-visual');
    accents.forEach((el) => el.classList.add('motion-float-soft'));
  }

  document.addEventListener('DOMContentLoaded', () => {
    injectCSS();
    initCurtain();
    initScrollProgress();
    initSectionMaskReveal();
    initHeadingStagger();
    initRevealAnimations();
    initMagneticButtons();
    initParallax();
    initCardTilt();
    initCounters();
    initFloatingAccents();
  });
})();