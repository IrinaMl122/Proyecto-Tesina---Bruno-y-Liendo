document.addEventListener('DOMContentLoaded', () => {
  // Toggle mostrar/ocultar contraseña
  document.querySelectorAll('.password-toggle').forEach((btn) => {
    btn.addEventListener('click', () => {
      const targetSelector = btn.getAttribute('data-target');
      const input = document.querySelector(targetSelector);
      if (!input) return;
      
      const isPassword = input.getAttribute('type') === 'password';
      input.setAttribute('type', isPassword ? 'text' : 'password');
      
      // Cambiar la imagen del botón
      const img = btn.querySelector('img');
      if (img) {
        if (isPassword) {
          // Mostrar contraseña - cambiar a ojo cerrado
          img.src = img.src.replace('ojoabierto', 'ojocerrado');
          img.alt = 'Ocultar contraseña';
        } else {
          // Ocultar contraseña - cambiar a ojo abierto
          img.src = img.src.replace('ojocerrado', 'ojoabierto');
          img.alt = 'Mostrar contraseña';
        }
      }
      
      btn.setAttribute('aria-label', isPassword ? 'Ocultar contraseña' : 'Mostrar contraseña');
      btn.classList.toggle('is-revealed', isPassword);
    });
  });

  // Estado de "cargando" en botones de formularios al enviar
  document.querySelectorAll('form').forEach((form) => {
    form.addEventListener('submit', (e) => {
      const submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn) {
        submitBtn.classList.add('btn-loading');
        submitBtn.disabled = true;
      }
    });
  });

  // Efecto micro-animación al enfocar inputs
  document.querySelectorAll('.form input, .form textarea, .form select').forEach((el) => {
    el.addEventListener('focus', () => el.classList.add('is-focused'));
    el.addEventListener('blur', () => el.classList.remove('is-focused'));
  });

  // IntersectionObserver: revelar elementos al entrar en viewport
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1 });

  document.querySelectorAll('.reveal, .card, .project-card, .stat-item, .recent-project').forEach(el => {
    el.classList.add('reveal');
    observer.observe(el);
  });

  // Header sticky ligero al hacer scroll
  const root = document.documentElement;
  let lastY = 0;
  window.addEventListener('scroll', () => {
    const y = window.scrollY || document.documentElement.scrollTop;
    if (y > 8 && y >= lastY) {
      root.classList.add('is-stuck');
    } else if (y < 8) {
      root.classList.remove('is-stuck');
    }
    lastY = y;
  });
});


