// Shared components — Toast notifications + utility helpers
(function () {
  'use strict';

  // ── TOAST SYSTEM ──────────────────────────────────────────
  var Toast = {
    container: null,
    defaults: { duration: 3000, position: 'bottom-right' },

    _getContainer: function () {
      if (this.container && document.body.contains(this.container)) return this.container;

      var el = document.createElement('div');
      el.id = 'gn-toast-container';
      el.setAttribute('aria-live', 'polite');
      el.setAttribute('aria-atomic', 'true');
      document.body.appendChild(el);
      this.container = el;
      return el;
    },

    show: function (message, options) {
      options = options || {};
      var type = options.type || 'info'; // info, success, warning, error
      var duration = options.duration || this.defaults.duration;

      var container = this._getContainer();
      var toast = document.createElement('div');
      toast.className = 'gn-toast gn-toast-' + type;
      toast.setAttribute('role', 'alert');

      var icons = { info: '\u2139\uFE0F', success: '\u2705', warning: '\u26A0\uFE0F', error: '\u274C' };
      toast.innerHTML = '<span class="gn-toast-icon">' + (icons[type] || icons.info) + '</span>' +
                        '<span class="gn-toast-text">' + message + '</span>' +
                        '<button class="gn-toast-close" aria-label="Fechar notifica\u00E7\u00E3o">&times;</button>';

      container.appendChild(toast);

      // Trigger animation
      requestAnimationFrame(function () {
        toast.classList.add('gn-toast-show');
      });

      // Close button
      toast.querySelector('.gn-toast-close').addEventListener('click', function () {
        Toast._dismiss(toast);
      });

      // Auto-dismiss
      if (duration > 0) {
        setTimeout(function () { Toast._dismiss(toast); }, duration);
      }

      return toast;
    },

    _dismiss: function (toast) {
      toast.classList.remove('gn-toast-show');
      toast.classList.add('gn-toast-hide');
      setTimeout(function () { toast.remove(); }, 300);
    },

    success: function (msg, opts) { return this.show(msg, Object.assign({ type: 'success' }, opts || {})); },
    error: function (msg, opts) { return this.show(msg, Object.assign({ type: 'error' }, opts || {})); },
    warning: function (msg, opts) { return this.show(msg, Object.assign({ type: 'warning' }, opts || {})); },
    info: function (msg, opts) { return this.show(msg, Object.assign({ type: 'info' }, opts || {})); }
  };

  window.GnToast = Toast;

  // ── INJECT TOAST CSS ──────────────────────────────────────
  function injectToastCSS() {
    if (document.getElementById('gn-toast-css')) return;
    var style = document.createElement('style');
    style.id = 'gn-toast-css';
    style.textContent = `
      #gn-toast-container {
        position: fixed;
        bottom: 24px;
        right: 24px;
        z-index: 100000;
        display: flex;
        flex-direction: column;
        gap: 10px;
        pointer-events: none;
        max-width: 400px;
      }

      .gn-toast {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 14px 18px;
        background: var(--navy-2, #0d1526);
        border: 1px solid var(--border, rgba(157,217,248,0.2));
        border-radius: 14px;
        box-shadow: 0 12px 40px rgba(0,0,0,0.35);
        opacity: 0;
        transform: translateX(100%) scale(0.95);
        transition: all 0.3s cubic-bezier(0.2, 0.8, 0.2, 1);
        pointer-events: auto;
        font-size: 0.88rem;
        line-height: 1.4;
        color: var(--white, #f0f4ff);
      }

      .gn-toast-show {
        opacity: 1;
        transform: translateX(0) scale(1);
      }

      .gn-toast-hide {
        opacity: 0;
        transform: translateX(100%) scale(0.95);
      }

      .gn-toast-icon {
        font-size: 1.2rem;
        flex-shrink: 0;
      }

      .gn-toast-text {
        flex: 1;
      }

      .gn-toast-close {
        background: none;
        border: none;
        color: var(--white-dim, rgba(240,244,255,0.5));
        font-size: 1.1rem;
        cursor: pointer;
        padding: 2px 6px;
        border-radius: 6px;
        flex-shrink: 0;
        transition: background 0.15s;
      }

      .gn-toast-close:hover {
        background: var(--white-faint, rgba(240,244,255,0.08));
      }

      .gn-toast-success {
        border-left: 3px solid #2ecc71;
      }

      .gn-toast-warning {
        border-left: 3px solid #f39c12;
      }

      .gn-toast-error {
        border-left: 3px solid #ff3b5c;
      }

      .gn-toast-info {
        border-left: 3px solid #9DD9F8;
      }

      @media (max-width: 720px) {
        #gn-toast-container {
          left: 14px;
          right: 14px;
          bottom: 14px;
          max-width: none;
        }
        .gn-toast {
          transform: translateY(100%) scale(0.95);
        }
        .gn-toast-show {
          transform: translateY(0) scale(1);
        }
        .gn-toast-hide {
          transform: translateY(100%) scale(0.95);
        }
      }
    `;
    document.head.appendChild(style);
  }

  injectToastCSS();

  // ── RIPPLE EFFECT ON BUTTONS ──────────────────────────────
  function initRipple() {
    var buttons = document.querySelectorAll(
      '.btn-primario, .btn-secundario, .btn-plano, .btn-plano-primario, .btn-plano-secundario, .nav-cta, .btn-pagar'
    );

    buttons.forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        var rect = btn.getBoundingClientRect();
        var ripple = document.createElement('span');
        var size = Math.max(rect.width, rect.height);
        ripple.style.cssText = 'position:absolute;border-radius:50%;background:rgba(255,255,255,0.3);' +
          'width:' + size + 'px;height:' + size + 'px;' +
          'left:' + (e.clientX - rect.left - size / 2) + 'px;' +
          'top:' + (e.clientY - rect.top - size / 2) + 'px;' +
          'transform:scale(0);opacity:1;pointer-events:none;animation:gn-ripple 0.6s ease-out;';
        btn.style.position = btn.style.position || 'relative';
        btn.style.overflow = 'hidden';
        btn.appendChild(ripple);
        setTimeout(function () { ripple.remove(); }, 600);
      });
    });
  }

  // Inject ripple keyframes
  function injectRippleCSS() {
    if (document.getElementById('gn-ripple-css')) return;
    var style = document.createElement('style');
    style.id = 'gn-ripple-css';
    style.textContent = `
      @keyframes gn-ripple {
        to { transform: scale(4); opacity: 0; }
      }
    `;
    document.head.appendChild(style);
  }

  injectRippleCSS();

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initRipple);
  } else {
    initRipple();
  }
})();
