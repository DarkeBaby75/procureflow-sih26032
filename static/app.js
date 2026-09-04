document.querySelectorAll('[data-fill-email]').forEach((button) => {
  button.addEventListener('click', () => {
    document.querySelector('input[name="email"]').value = button.dataset.fillEmail;
    document.querySelector('input[name="password"]').value = button.dataset.fillPassword;
  });
});
document.querySelectorAll('[data-confirm]').forEach((form) => {
  form.addEventListener('submit', (event) => {
    if (!window.confirm(form.dataset.confirm)) event.preventDefault();
  });
});
document.querySelectorAll('[data-refresh]').forEach((button) => button.addEventListener('click', () => window.location.reload()));
document.querySelectorAll('[data-language-select]').forEach((select) => {
  select.addEventListener('change', () => {
    const form = select.closest('form');
    form.action = `/language/${select.value}`;
    form.submit();
  });
});
