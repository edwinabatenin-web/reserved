/**
 * optimise.js — Tax Opportunities page interactions.
 *
 * Responsibilities:
 *  1. "Explore scenario" toggle — show/hide the inline scenario explorer.
 *  2. Slider ↔ number-input synchronisation.
 *  3. Calculate button — POST JSON to /v2/optimise/calculate → update before/after table.
 *  4. Save button — POST JSON to /v2/optimise/save-scenario → show confirmation.
 *  5. Delete saved scenario — DELETE /v2/optimise/saved/:id → remove from DOM.
 */
(function () {
  'use strict';

  // ── Helpers ───────────────────────────────────────────────────────────────

  function fmtGBP(raw) {
    const n = parseFloat(String(raw).replace(/,/g, ''));
    if (isNaN(n)) return '—';
    return '£' + n.toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function diffClass(before, after) {
    const b = parseFloat(String(before).replace(/,/g, ''));
    const a = parseFloat(String(after).replace(/,/g, ''));
    if (isNaN(b) || isNaN(a)) return 'neutral';
    if (a < b) return 'positive';   // lower tax/HICBC is good
    if (a > b) return 'negative';
    return 'neutral';
  }

  function diffLabel(before, after) {
    const b = parseFloat(String(before).replace(/,/g, ''));
    const a = parseFloat(String(after).replace(/,/g, ''));
    if (isNaN(b) || isNaN(a)) return '—';
    const delta = a - b;
    if (delta === 0) return 'No change';
    const sign = delta > 0 ? '+' : '−';
    return sign + '£' + Math.abs(delta).toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function diffClassPA(before, after) {
    // For PA and ANI, direction is reversed (higher PA or lower ANI = good)
    const b = parseFloat(String(before).replace(/,/g, ''));
    const a = parseFloat(String(after).replace(/,/g, ''));
    if (isNaN(b) || isNaN(a)) return 'neutral';
    if (a > b) return 'positive';   // more PA is good
    if (a < b) return 'negative';
    return 'neutral';
  }

  function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  function setClass(id, cls) {
    const el = document.getElementById(id);
    if (el) { el.className = 'diff ' + cls; }
  }

  function show(id) {
    const el = document.getElementById(id);
    if (el) el.hidden = false;
  }

  function hide(id) {
    const el = document.getElementById(id);
    if (el) el.hidden = true;
  }

  // ── "Explore scenario" toggle ──────────────────────────────────────────────

  document.querySelectorAll('.opt-explore-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      const oppId    = btn.dataset.opp;
      const explorer = document.getElementById('explorer-' + oppId);
      if (!explorer) return;

      const isHidden = explorer.hidden;
      explorer.hidden = !isHidden;
      btn.textContent = isHidden ? 'Hide scenario' : 'Explore scenario';

      if (isHidden) {
        // Pre-fill slider with suggested amount
        const suggest = parseInt(btn.dataset.suggest || '0', 10);
        if (suggest > 0) {
          const slider = document.getElementById('slider-' + oppId);
          const input  = document.getElementById('amount-' + oppId);
          if (slider) slider.value = suggest;
          if (input)  input.value  = suggest;
        }
        explorer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    });
  });

  // ── Slider ↔ number-input sync ────────────────────────────────────────────

  document.querySelectorAll('[data-opp-id]').forEach(function (card) {
    const oppId = card.dataset.oppId;
    const slider = document.getElementById('slider-' + oppId);
    const input  = document.getElementById('amount-' + oppId);
    if (!slider || !input) return;

    slider.addEventListener('input', function () {
      input.value = slider.value;
    });

    input.addEventListener('input', function () {
      const v = parseInt(input.value, 10);
      if (!isNaN(v)) {
        slider.value = Math.max(0, Math.min(60000, v));
      }
    });
  });

  // ── Calculate ─────────────────────────────────────────────────────────────

  document.querySelectorAll('.opt-calculate-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      const oppId = btn.dataset.opp;
      const card  = document.querySelector('[data-opp-id="' + oppId + '"]');
      if (!card) return;

      const projectedIncome  = parseFloat(card.dataset.projected)   || 0;
      const currentPension   = parseFloat(card.dataset.currentPension) || 0;
      const annualCb         = parseFloat(card.dataset.annualCb)    || 0;
      const inputEl          = document.getElementById('amount-' + oppId);
      const additionalPension= parseFloat(inputEl ? inputEl.value : 0) || 0;

      btn.disabled = true;
      show('calc-spin-' + oppId);
      hide('results-' + oppId);

      fetch('/v2/optimise/calculate', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          opportunity_id:     oppId,
          projected_income:   projectedIncome,
          current_pension:    currentPension,
          additional_pension: additionalPension,
          annual_cb:          annualCb,
        }),
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (!data.ok) {
            alert('Calculation error: ' + (data.error || 'unknown'));
            return;
          }
          _applyResults(oppId, data, additionalPension);
          show('results-' + oppId);
        })
        .catch(function (err) {
          alert('Network error — please try again.');
          console.error(err);
        })
        .finally(function () {
          btn.disabled = false;
          hide('calc-spin-' + oppId);
        });
    });
  });

  function _applyResults(oppId, data, additionalPension) {
    const b = data.before;
    const a = data.after;

    // ANI (lower is not necessarily good — for PA taper, lower ANI restores PA)
    setText('r-before-ani-' + oppId, fmtGBP(b.ani));
    setText('r-after-ani-'  + oppId, fmtGBP(a.ani));
    setText('r-diff-ani-'   + oppId, diffLabel(b.ani, a.ani));
    setClass('r-diff-ani-'  + oppId, 'neutral');  // ANI direction is context-dependent

    // PA (higher is better)
    setText('r-before-pa-' + oppId, fmtGBP(b.pa));
    setText('r-after-pa-'  + oppId, fmtGBP(a.pa));
    setText('r-diff-pa-'   + oppId, diffLabel(b.pa, a.pa));
    setClass('r-diff-pa-'  + oppId, diffClassPA(b.pa, a.pa));

    // Income tax (lower is better)
    setText('r-before-it-' + oppId, fmtGBP(b.it));
    setText('r-after-it-'  + oppId, fmtGBP(a.it));
    setText('r-diff-it-'   + oppId, diffLabel(b.it, a.it));
    setClass('r-diff-it-'  + oppId, diffClass(b.it, a.it));

    // HICBC (lower is better)
    setText('r-before-hicbc-' + oppId, fmtGBP(b.hicbc));
    setText('r-after-hicbc-'  + oppId, fmtGBP(a.hicbc));
    setText('r-diff-hicbc-'   + oppId, diffLabel(b.hicbc, a.hicbc));
    setClass('r-diff-hicbc-'  + oppId, diffClass(b.hicbc, a.hicbc));

    // Summary figures
    setText('r-total-benefit-' + oppId, '£' + data.total_benefit);
    setText('r-brl-'           + oppId, '£' + data.basic_rate_relief);

    // Caveats
    const caveatList = document.getElementById('r-caveats-' + oppId);
    if (caveatList && data.caveats && data.caveats.length) {
      caveatList.innerHTML = data.caveats.map(function (c) {
        return '<li>' + _escapeHtml(c) + '</li>';
      }).join('');
    }

    // Store current result on the card for saving
    const card = document.querySelector('[data-opp-id="' + oppId + '"]');
    if (card) {
      card.dataset.lastResult = JSON.stringify({
        inputs: {
          projected_income:   parseFloat(card.dataset.projected)     || 0,
          current_pension:    parseFloat(card.dataset.currentPension) || 0,
          additional_pension: additionalPension,
          annual_cb:          parseFloat(card.dataset.annualCb)       || 0,
        },
        outputs: {
          it_reduction:    data.it_reduction,
          hicbc_reduction: data.hicbc_reduction,
          total_benefit:   data.total_benefit,
          basic_rate_relief: data.basic_rate_relief,
          total_pension:   data.total_pension,
        },
      });
    }

    // Reset save feedback
    hide('save-feedback-' + oppId);
  }

  // ── Save ──────────────────────────────────────────────────────────────────

  document.querySelectorAll('.opt-save-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      const oppId = btn.dataset.opp;
      const card  = document.querySelector('[data-opp-id="' + oppId + '"]');
      if (!card || !card.dataset.lastResult) return;

      let parsed;
      try {
        parsed = JSON.parse(card.dataset.lastResult);
      } catch (e) {
        return;
      }

      const label = prompt(
        'Give this comparison a name (optional — press OK to save without a name):',
        oppId + ' — £' + (parsed.inputs.additional_pension || 0) + ' extra pension'
      );
      if (label === null) return;  // user cancelled

      btn.disabled = true;
      fetch('/v2/optimise/save-scenario', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          opportunity_id: oppId,
          label:          label.trim(),
          inputs:         parsed.inputs,
          outputs:        parsed.outputs,
        }),
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.ok) {
            show('save-feedback-' + oppId);
          }
        })
        .catch(function (err) {
          alert('Failed to save — please try again.');
          console.error(err);
        })
        .finally(function () {
          btn.disabled = false;
        });
    });
  });

  // ── Delete saved scenario ─────────────────────────────────────────────────

  document.querySelectorAll('.opt-saved-delete').forEach(function (btn) {
    btn.addEventListener('click', function () {
      const id = btn.dataset.id;
      if (!id || !confirm('Remove this saved comparison?')) return;
      btn.disabled = true;
      fetch('/v2/optimise/saved/' + id, { method: 'DELETE' })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.ok) {
            const row = document.getElementById('saved-' + id);
            if (row) row.remove();
          }
        })
        .catch(function (err) {
          btn.disabled = false;
          console.error(err);
        });
    });
  });

  // ── XSS helper ────────────────────────────────────────────────────────────

  function _escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

})();
