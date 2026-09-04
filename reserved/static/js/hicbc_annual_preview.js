/* Ephemeral manual HICBC preview only; no storage, calculation or linked fallback. */
(() => {
    'use strict';
    const form = document.getElementById('hicbc-annual-form');
    if (!form) return;
    const result = document.getElementById('annual-result');
    const error = document.getElementById('annual-error');
    const submit = document.getElementById('annual-submit');
    const money = ['employment_income', 'sole_trade_profit', 'savings_interest', 'dividends',
        'uk_property_receipts', 'uk_property_allowable_expenses', 'brought_forward_uk_property_loss',
        'foreign_property_gross_receipts', 'foreign_property_allowable_expenses', 'gross_ras_pension',
        'residential_finance_costs', 'foreign_tax_paid'];
    const confirmations = ['full_tax_year_including_known_future', 'uk_resident',
        'employment_basis', 'other_ani_adjustments'];
    const fields = ['tax_year', 'responsibility_status', 'calculation_status', 'headline',
        'projected_user_hicbc', 'possible_charge_low', 'possible_charge_high',
        'household_change_status', 'based_on_partner_estimate', 'messages'];
    const amounts = ['projected_user_hicbc', 'possible_charge_low', 'possible_charge_high'];
    // Existing customer_view headlines, not independently authored tax/customer policy.
    // Source-derived executable fixtures bind these to the current producer.
    const headlines = {
        no_charge: 'Reserved does not estimate a High Income Child Benefit Charge for you based on the information currently available.',
        person_liable: 'Based on the information currently available, Reserved estimates that the High Income Child Benefit Charge may apply to you.',
        partner_liable: 'Based on the information currently available, Reserved has not included a High Income Child Benefit Charge in your estimate.',
        ambiguous: 'Responsibility for the High Income Child Benefit Charge cannot currently be determined because the available income information is overlapping.',
        insufficient_facts: 'Reserved needs more information to estimate whether the High Income Child Benefit Charge applies to you.',
    };
    const closedMessage = 'Confirm your income details for this tax year to estimate this charge.';
    const unavailable = 'This preview is not available. Check your information or sign in again and retry.';
    let generation = 0;
    let pending;
    const clear = () => {
        generation += 1;
        if (pending) pending.abort();
        result.replaceChildren();
        result.removeAttribute('aria-busy');
        error.textContent = '';
        error.hidden = true;
        for (const control of form.elements) control.removeAttribute('aria-invalid');
    };
    const fail = (message) => {
        result.replaceChildren();
        error.textContent = message;
        error.hidden = false;
        error.focus();
    };
    const paragraph = (text) => {
        const node = document.createElement('p');
        node.textContent = text;
        result.appendChild(node);
    };
    const validView = (view, status) => {
        if (!view || typeof view !== 'object' || Array.isArray(view)
            || Object.keys(view).sort().join('|') !== fields.slice().sort().join('|')
            || view.tax_year !== form.dataset.taxYear
            || typeof view.based_on_partner_estimate !== 'boolean'
            || !Array.isArray(view.messages) || view.messages.length > 32) return false;
        for (const key of ['tax_year', 'responsibility_status', 'calculation_status', 'headline', 'household_change_status']) {
            if (typeof view[key] !== 'string' || view[key].length > 1000) return false;
        }
        if (!view.messages.every(value => typeof value === 'string' && value.length <= 1000)) return false;
        if (!amounts.every(key => view[key] === null || (typeof view[key] === 'string'
            && /^(?:0|[1-9][0-9]{0,2}(?:,[0-9]{3})*)\.[0-9]{2}$/.test(view[key])
            && view[key].length <= 20))) return false;
        const responsibility = view.responsibility_status;
        const calculation = view.calculation_status;
        if (!Object.prototype.hasOwnProperty.call(headlines, responsibility)
            || view.headline !== headlines[responsibility]
            // This fresh annual-preview producer has no previous-result transition.
            || view.household_change_status !== 'not_applicable') return false;
        const point = view.projected_user_hicbc;
        const low = view.possible_charge_low;
        const high = view.possible_charge_high;
        if ((low === null) !== (high === null)) return false;
        // Exact comparison of already-formatted amounts, not a tax calculation.
        if (low !== null && BigInt(low.replace(/[,.]/g, '')) > BigInt(high.replace(/[,.]/g, ''))) return false;
        if (status === 409) return responsibility === 'insufficient_facts'
            && calculation === 'insufficient_facts' && amounts.every(key => view[key] === null)
            && view.based_on_partner_estimate === false
            && view.messages.length === 1 && view.messages[0] === closedMessage;
        if (responsibility === 'no_charge') return calculation === 'not_applicable'
            && point === '0.00' && low === point && high === point;
        if (responsibility === 'insufficient_facts') return calculation === 'insufficient_facts'
            && point === null && (low === null || low === '0.00');
        if (responsibility === 'ambiguous') return calculation === 'bounded_range'
            && point === null && low === '0.00';
        if (calculation === 'calculated_with_material_uncertainty') return point === null && low === '0.00';
        return calculation === 'calculated' && point !== null && low === point && high === point
            && (responsibility !== 'partner_liable' || point === '0.00');
    };
    form.addEventListener('input', clear);
    form.addEventListener('change', clear);
    form.addEventListener('reset', clear);
    window.addEventListener('pagehide', clear);
    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        clear();
        const current = generation;
        const payload = {schema_version: 'hicbc-manual-annual/1', tax_year: form.dataset.taxYear};
        let invalid = false;
        for (const name of money) {
            const control = form.elements.namedItem(name);
            payload[name] = control.value;
            if (!/^(?:0|[1-9][0-9]{0,7})(?:\.[0-9]{1,2})?$/.test(control.value)) {
                control.setAttribute('aria-invalid', 'true'); invalid = true;
            }
        }
        payload.country = form.elements.namedItem('country').value;
        if (!['England', 'Wales', 'Northern Ireland'].includes(payload.country)) {
            form.elements.namedItem('country').setAttribute('aria-invalid', 'true'); invalid = true;
        }
        for (const name of confirmations) {
            if (!form.elements.namedItem(name).checked) {
                form.elements.namedItem(name).setAttribute('aria-invalid', 'true'); invalid = true;
            }
        }
        if (invalid) { fail('We cannot calculate this preview yet. Enter every annual amount (0 if it does not apply), choose a supported country and confirm each statement only if true.'); return; }
        payload.full_tax_year_including_known_future = true;
        payload.uk_resident = true;
        payload.employment_basis = 'all_jobs_taxable_after_salary_sacrifice_and_net_pay';
        payload.other_ani_adjustments = 'none';
        const token = document.querySelector('meta[name="csrf-token"]');
        if (!token || !token.content) { fail(unavailable); return; }
        pending = new AbortController();
        result.setAttribute('aria-busy', 'true');
        paragraph('Checking your separate annual preview…');
        try {
            const response = await fetch('/v2/hicbc/annual-preview', {
                method: 'POST', credentials: 'same-origin', redirect: 'error', cache: 'no-store',
                headers: {'Content-Type': 'application/json', 'X-CSRFToken': token.content},
                body: JSON.stringify(payload), signal: pending.signal,
            });
            if (current !== generation) return;
            if (response.redirected || ![200, 409].includes(response.status)
                || (response.headers.get('Content-Type') || '').split(';')[0].trim() !== 'application/json') throw new Error();
            const view = await response.json();
            if (current !== generation) return;
            if (!validView(view, response.status)) throw new Error();
            result.replaceChildren();
            paragraph('Separate annual-information preview for tax year ' + view.tax_year);
            paragraph(view.headline);
            if (view.projected_user_hicbc !== null) paragraph('Estimated charge that may apply to you: £' + view.projected_user_hicbc);
            else if (view.possible_charge_low !== null) paragraph('Possible charge that may apply to you: between £' + view.possible_charge_low + ' and £' + view.possible_charge_high + '.');
            for (const message of view.messages) paragraph(message);
        } catch (_) {
            if (current === generation) fail(unavailable);
        } finally {
            if (current === generation) result.removeAttribute('aria-busy');
        }
    });
    submit.disabled = false;
})();
