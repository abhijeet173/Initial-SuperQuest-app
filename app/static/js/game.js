document.addEventListener('DOMContentLoaded', () => {
  const menu = document.querySelector('.menu-toggle');
  const nav = document.querySelector('.nav-links');
  menu?.addEventListener('click', () => {
    const open = menu.getAttribute('aria-expanded') === 'true';
    menu.setAttribute('aria-expanded', String(!open));
    nav?.classList.toggle('nav-open', !open);
  });

  document.querySelectorAll('.flash button').forEach((button) => {
    button.addEventListener('click', () => button.closest('.flash')?.remove());
  });

  const timer = document.querySelector('[data-countdown]');
  if (timer) {
    let remaining = Number(timer.dataset.countdown);
    const display = document.querySelector('#timer-display');
    const interval = window.setInterval(() => {
      remaining -= 1;
      display.textContent = String(Math.max(remaining, 0));
      timer.classList.toggle('timer-urgent', remaining <= 20);
      if (remaining <= 0) {
        window.clearInterval(interval);
        document.querySelector('#mission-form')?.submit();
      }
    }, 1000);
  }

  document.querySelectorAll('.hint-button').forEach((button) => {
    button.addEventListener('click', async () => {
      button.disabled = true;
      try {
        const response = await fetch(button.dataset.hintUrl, {
          method: 'POST',
          headers: { 'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content }
        });
        if (!response.ok) throw new Error('Hint unavailable');
        const { remove } = await response.json();
        document.querySelectorAll('.question-block:first-of-type .answer-option')[remove]?.classList.add('answer-eliminated');
        button.textContent = 'Hint used';
      } catch {
        button.disabled = false;
        button.textContent = 'Hint unavailable';
      }
    });
  });

  document.querySelectorAll('form[data-confirm]').forEach((form) => {
    form.addEventListener('submit', (event) => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });
});