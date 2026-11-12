document.addEventListener('DOMContentLoaded', function() {
  const rows = document.querySelectorAll('#expenseTable tbody tr');
  const search = document.getElementById('expenseSearch');
  const month = document.getElementById('expenseMonth');
  function apply() {
    const q = search.value.trim().toLowerCase();
    const m = month.value;
    let total = 0;
    let n = 0;
    rows.forEach(function(r) {
      const ok = (!m || r.dataset.month === m) && (!q || r.textContent.toLowerCase().indexOf(q) > -1);
      r.hidden = !ok;
      if (ok) { total += Number(r.dataset.amount); n++; }
    });
    document.getElementById('expenseFootTotal').textContent = 'Ugx ' + total.toLocaleString('en-US');
    document.getElementById('expenseFootCount').textContent = n + (n === 1 ? ' expense' : ' expenses');
    document.getElementById('expenseFoot').hidden = n === 0;
    document.getElementById('expenseEmpty').hidden = n > 0 || rows.length === 0;
  }
  // Record expense: show the amount comma separated as it is typed.
  const amount = document.querySelector('#recordExpenseModal [data-amount-input]');
  if (amount) {
    const wrap = document.createElement('div');
    wrap.className = 'si-amount-wrap';
    const prefix = document.createElement('span');
    prefix.textContent = 'UGX';
    prefix.setAttribute('aria-hidden', 'true');
    amount.parentNode.insertBefore(wrap, amount);
    wrap.append(prefix, amount);

    const format = function() {
      const caret = amount.selectionStart || 0;
      const digitsBefore = amount.value.slice(0, caret).replace(/\D/g, '').length;
      const digits = amount.value.replace(/\D/g, '').replace(/^0+(?=\d)/, '').slice(0, 13);
      const out = digits ? Number(digits).toLocaleString('en-US') : '';
      amount.value = out;
      let i = 0;
      let seen = 0;
      while (i < out.length && seen < digitsBefore) {
        if (/\d/.test(out[i])) seen++;
        i++;
      }
      amount.setSelectionRange(i, i);
    };
    amount.addEventListener('input', format);
    if (amount.value) format();
  }
  search.addEventListener('input', apply);
  month.addEventListener('change', apply);
  if (rows.length) apply();
  const modal = document.getElementById('recordExpenseModal');
  if (modal && modal.dataset.showOnLoad === 'true') {
    new bootstrap.Modal(modal).show();
  }
});
