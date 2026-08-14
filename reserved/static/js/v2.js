/* ============================================================
   Reserved™ — V2 Preview JavaScript
   Internal only · Not published
   ============================================================ */

(function () {
    'use strict';

    // ── State switcher ────────────────────────────────────────────────────────

    const STATES = ['empty', 'connecting', 'returning', 'connected', 'multi', 'expiring', 'reconnect', 'wrong-account', 'error', 'unavailable', 'disconnected'];

    function getActiveState() {
        const params = new URLSearchParams(location.search);
        return params.get('state') || 'empty';
    }

    function showState(key) {
        // Hide all state panels
        STATES.forEach(s => {
            const el = document.getElementById('v2-state-' + s);
            if (el) el.hidden = true;
        });

        // Show requested panel
        const target = document.getElementById('v2-state-' + key);
        if (target) {
            target.hidden = false;
            target.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }

        // Update URL (no reload)
        const url = new URL(location.href);
        url.searchParams.set('state', key);
        history.replaceState(null, '', url.toString());

        // Update active button
        document.querySelectorAll('.v2-state-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.state === key);
        });
    }

    // Attach state button listeners
    document.querySelectorAll('.v2-state-btn').forEach(btn => {
        btn.addEventListener('click', () => showState(btn.dataset.state));
    });

    // ── Action button wiring ──────────────────────────────────────────────────

    function handleAction(action) {
        switch (action) {
            case 'start-connect':
                showState('connecting');
                // Sandbox: simulate redirect delay then show error or success
                setTimeout(() => showState('connected'), 2800);
                break;

            case 'cancel-connect':
                showState('empty');
                break;

            case 'add-account':
                // Simulate connecting a second account
                showState('connecting');
                setTimeout(() => showState('multi'), 2600);
                break;

            case 'retry':
                showState('connecting');
                setTimeout(() => showState('connected'), 2600);
                break;

            case 'choose-bank':
                showState('empty');
                break;

            case 'renew':
                showState('connecting');
                setTimeout(() => showState('connected'), 2400);
                break;

            case 'disconnect':
                closeAllMenus();
                showState('disconnected');
                break;

            case 'refresh-sync':
                closeAllMenus();
                // Visual feedback only
                const activeCard = document.querySelector('.v2-account-card');
                if (activeCard) {
                    const syncEl = activeCard.querySelector('.v2-account-sync strong');
                    if (syncEl) {
                        const prev = syncEl.textContent;
                        syncEl.textContent = 'Syncing…';
                        setTimeout(() => { syncEl.textContent = 'Synced just now'; }, 1200);
                    }
                }
                break;

            case 'view-transactions':
                closeAllMenus();
                // Placeholder — would navigate to a transaction list in production
                alert('[V2 Preview] Transaction view not yet implemented in this preview.');
                break;

            case 'notify-me':
                // Placeholder
                alert('[V2 Preview] Notification preference saved (sandbox only).');
                break;

            case 'view-all-banks':
                openAllBanksModal();
                break;

            case 'go-home':
                location.href = '/';
                break;
        }
    }

    // Delegate all data-v2-action clicks
    document.addEventListener('click', e => {
        const btn = e.target.closest('[data-v2-action]');
        if (btn) {
            e.stopPropagation();
            handleAction(btn.dataset.v2Action);
        }
    });

    // ── Account option menus ──────────────────────────────────────────────────

    function closeAllMenus() {
        document.querySelectorAll('.v2-account-menu').forEach(m => m.hidden = true);
    }

    document.addEventListener('click', e => {
        const trigger = e.target.closest('[data-v2-menu]');
        if (trigger) {
            e.stopPropagation();
            const menuId = 'v2-menu-' + trigger.dataset.v2Menu;
            const menu = document.getElementById(menuId);
            if (!menu) return;
            // Close all others first
            document.querySelectorAll('.v2-account-menu').forEach(m => {
                if (m !== menu) m.hidden = true;
            });
            menu.hidden = !menu.hidden;
            return;
        }
        // Click outside → close all menus
        closeAllMenus();
    });

    // ── All banks modal ───────────────────────────────────────────────────────

    function openAllBanksModal() {
        const modal = document.getElementById('v2-all-banks-modal');
        if (modal) modal.hidden = false;
    }

    function closeAllBanksModal() {
        const modal = document.getElementById('v2-all-banks-modal');
        if (modal) modal.hidden = true;
    }

    const closeBtn = document.getElementById('v2-all-banks-close');
    if (closeBtn) closeBtn.addEventListener('click', closeAllBanksModal);

    // Close on backdrop click
    const modal = document.getElementById('v2-all-banks-modal');
    if (modal) {
        modal.addEventListener('click', e => {
            if (e.target === modal) closeAllBanksModal();
        });
    }

    // Close on Escape
    document.addEventListener('keydown', e => {
        if (e.key === 'Escape') {
            closeAllBanksModal();
            closeAllMenus();
        }
    });

    // ── Initial state ─────────────────────────────────────────────────────────
    // The server already rendered the correct state via hidden attributes.
    // Re-apply via JS to ensure the active button matches on first load.
    const initialState = getActiveState();
    document.querySelectorAll('.v2-state-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.state === initialState);
    });

})();
