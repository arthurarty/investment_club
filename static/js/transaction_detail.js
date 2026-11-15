document.addEventListener('DOMContentLoaded', function() {
  // Switch the transaction page between its view card and its edit form.
  const view = document.getElementById('transactionViewCard');
  const form = document.getElementById('transactionEditCard');
  const actions = document.getElementById('transactionViewActions');
  if (!view || !form || !actions) return;
  const hint = document.getElementById('transactionDirtyHint');

  const open = function() {
    view.hidden = true;
    actions.hidden = true;
    form.hidden = false;
    form.querySelector('input:not([type="hidden"])').focus();
  };
  const close = function() {
    form.reset();
    // Re-apply the comma formatting to the restored amounts.
    form.querySelectorAll('[data-amount-input]').forEach(function(amount) {
      amount.dispatchEvent(new Event('input'));
    });
    hint.textContent = '';
    form.hidden = true;
    view.hidden = false;
    actions.hidden = false;
  };

  document.getElementById('transactionEditBtn').addEventListener('click', open);
  document.getElementById('transactionCancelBtn').addEventListener('click', close);
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && !form.hidden) close();
  });
  form.addEventListener('input', function(e) {
    if (e.isTrusted) hint.textContent = 'Unsaved changes';
  });
});
