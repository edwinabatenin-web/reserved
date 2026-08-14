document.addEventListener("DOMContentLoaded", () => {
    const root = document.documentElement;
    const menuButton = document.querySelector("[data-menu-button]");
    const menuBackdrop = document.querySelector("[data-menu-backdrop]");
    const sidebar = document.querySelector("#sidebar");
    const themeButton = document.querySelector("[data-theme-toggle]");
    const notificationButton = document.querySelector("[data-notification-toggle]");
    const notificationPanel = document.querySelector("[data-notification-panel]");

    if (menuButton && sidebar) {
        const openMenu = () => {
            sidebar.classList.add("open");
            menuButton.setAttribute("aria-expanded", "true");
            if (menuBackdrop) menuBackdrop.hidden = false;
        };
        const closeMenu = () => {
            sidebar.classList.remove("open");
            menuButton.setAttribute("aria-expanded", "false");
            if (menuBackdrop) menuBackdrop.hidden = true;
        };

        menuButton.addEventListener("click", () => {
            sidebar.classList.contains("open") ? closeMenu() : openMenu();
        });

        // Backdrop tap closes the menu.
        if (menuBackdrop) {
            menuBackdrop.addEventListener("click", closeMenu);
        }

        // Click outside the sidebar (and not on the button) closes it.
        document.addEventListener("click", (e) => {
            if (sidebar.classList.contains("open") &&
                !sidebar.contains(e.target) &&
                e.target !== menuButton) {
                closeMenu();
            }
        });

        // Escape key closes the menu.
        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape" && sidebar.classList.contains("open")) {
                closeMenu();
                menuButton.focus();
            }
        });

        // Clicking a nav link inside the sidebar closes it on narrow viewports.
        // On desktop the sidebar is always visible and .open is never set,
        // so this handler is harmless there.
        sidebar.querySelectorAll("a[href]").forEach((link) => {
            link.addEventListener("click", () => {
                if (sidebar.classList.contains("open")) closeMenu();
            });
        });
    }

    const savedTheme = localStorage.getItem("reserved-theme");
    if (savedTheme) root.dataset.theme = savedTheme;

    if (themeButton) {
        themeButton.addEventListener("click", () => {
            const nextTheme = root.dataset.theme === "dark" ? "light" : "dark";
            root.dataset.theme = nextTheme;
            localStorage.setItem("reserved-theme", nextTheme);
            window.dispatchEvent(new Event("reserved-theme-change"));
        });
    }

    // ── Notification system ───────────────────────────────────────────────
    // The estimate notification lives only in the notification popover.
    // The old floating toast has been removed; recalculation now sets a
    // localStorage flag that shows an unread badge on the bell icon.
    const NOTIF_EST_KEY    = "rsvd-notif-estimate";
    const notifCount       = document.getElementById("notif-count");
    const notifBadge       = document.getElementById("notif-badge");
    const notifEstimate    = document.getElementById("notif-estimate");
    const notifEstDismiss  = document.getElementById("notif-estimate-dismiss");

    function getEstimateNotif() {
        try { return JSON.parse(localStorage.getItem(NOTIF_EST_KEY)); } catch { return null; }
    }
    function saveEstimateNotif(data) { localStorage.setItem(NOTIF_EST_KEY, JSON.stringify(data)); }
    function clearEstimateNotif()    { localStorage.removeItem(NOTIF_EST_KEY); }

    function updateNotifUI() {
        const n      = getEstimateNotif();
        const unread = (n && n.unread) ? 1 : 0;
        if (notifCount) { notifCount.textContent = unread || ""; notifCount.hidden = !unread; }
        if (notifBadge) { notifBadge.textContent = unread ? "1 new" : ""; notifBadge.hidden = !unread; }
        if (notifEstimate) notifEstimate.hidden = !unread;
    }

    // Dismiss ✕ — clear the notification entirely
    if (notifEstDismiss) {
        notifEstDismiss.addEventListener("click", (e) => {
            e.stopPropagation();
            clearEstimateNotif();
            updateNotifUI();
        });
    }

    // Click the notification item → go to dashboard calculation area, clear notification
    if (notifEstimate) {
        const openEstimateNotification = (e) => {
            if (e.target.closest(".notif-dismiss")) return;
            clearEstimateNotif();
            updateNotifUI();
            window.location.href = notifEstimate.dataset.notificationLink;
        };
        notifEstimate.addEventListener("click", openEstimateNotification);
        notifEstimate.addEventListener("keydown", (e) => {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                openEstimateNotification(e);
            }
        });
    }

    // Seed badge on every page load
    updateNotifUI();

    // Notification popover open/close
    if (notificationButton && notificationPanel) {
        const setNotificationsOpen = (open) => {
            notificationPanel.hidden = !open;
            notificationButton.setAttribute("aria-expanded", open ? "true" : "false");
        };
        notificationButton.addEventListener("click", (event) => {
            event.stopPropagation();
            setNotificationsOpen(notificationPanel.hidden);
        });
        document.addEventListener("click", (event) => {
            if (!notificationPanel.contains(event.target) && event.target !== notificationButton) {
                setNotificationsOpen(false);
            }
        });
        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && !notificationPanel.hidden) {
                setNotificationsOpen(false);
                notificationButton.focus();
            }
        });
    }

    document.querySelectorAll("[data-count-up]").forEach((element) => {
        const target = Number(element.dataset.countUp || 0);
        const duration = 850;
        const start = performance.now();
        const step = (time) => {
            const progress = Math.min(1, (time - start) / duration);
            const eased = 1 - Math.pow(1 - progress, 3);
            element.textContent = new Intl.NumberFormat("en-GB", {
                style: "currency",
                currency: "GBP",
            }).format(target * eased);
            if (progress < 1) requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
    });

    document.querySelectorAll("[data-allocation-width]").forEach((element) => {
        requestAnimationFrame(() => {
            element.style.width = `${element.dataset.allocationWidth}%`;
        });
    });

    document.querySelectorAll("[data-deadline]").forEach((element) => {
        const target = new Date(`${element.dataset.deadline}T00:00:00`);
        const now = new Date();
        const days = Math.ceil((target - now) / 86400000);
        element.textContent = days > 0 ? `${days} days remaining` : days === 0 ? "Due today" : "Deadline passed";
    });

    const form = document.querySelector("[data-calculation-form]");
    if (form) {
        form.addEventListener("submit", () => {
            const label = form.querySelector(".button-label");
            const spinner = form.querySelector(".button-spinner");
            if (label) label.textContent = "Updating";
            if (spinner) spinner.hidden = false;
            // Store notification in localStorage so badge appears on any page/revisit.
            // The notification lives in the popover only — no floating toast.
            saveEstimateNotif({ unread: true, ts: new Date().toISOString() });
        });
    }

    // ── Settings tabs ─────────────────────────────────────────────────────
    const tabs = document.querySelectorAll("[data-settings-tab]");
    const sections = document.querySelectorAll("[data-settings-section]");
    function activateSettingsTab(tab, moveFocus = false) {
        const target = tab.dataset.settingsTab;
        tabs.forEach((item) => {
            const selected = item === tab;
            item.classList.toggle("active", selected);
            item.setAttribute("aria-selected", selected ? "true" : "false");
            item.tabIndex = selected ? 0 : -1;
        });
        sections.forEach((section) => {
            const selected = section.dataset.settingsSection === target;
            section.classList.toggle("active", selected);
            section.hidden = !selected;
        });
        if (moveFocus) tab.focus();
    }
    tabs.forEach((tab, index) => {
        const target = tab.dataset.settingsTab;
        const section = Array.from(sections).find(
            (item) => item.dataset.settingsSection === target
        );
        tab.id = `settings-tab-${target}`;
        tab.setAttribute("role", "tab");
        tab.setAttribute("aria-controls", `settings-panel-${target}`);
        if (section) {
            section.id = `settings-panel-${target}`;
            section.setAttribute("role", "tabpanel");
            section.setAttribute("aria-labelledby", tab.id);
        }
        tab.addEventListener("click", () => activateSettingsTab(tab));
        tab.addEventListener("keydown", (event) => {
            let nextIndex = null;
            if (event.key === "ArrowRight" || event.key === "ArrowDown") nextIndex = (index + 1) % tabs.length;
            if (event.key === "ArrowLeft" || event.key === "ArrowUp") nextIndex = (index - 1 + tabs.length) % tabs.length;
            if (event.key === "Home") nextIndex = 0;
            if (event.key === "End") nextIndex = tabs.length - 1;
            if (nextIndex === null) return;
            event.preventDefault();
            activateSettingsTab(tabs[nextIndex], true);
        });
    });
    if (tabs.length) {
        activateSettingsTab(Array.from(tabs).find((tab) => tab.classList.contains("active")) || tabs[0]);
    }

    const settingsForm = document.querySelector("[data-settings-form]");
    if (settingsForm) {
        const errorSummary = settingsForm.querySelector(".settings-error-summary");
        if (errorSummary && errorSummary.hasAttribute("data-server-errors")) {
            errorSummary.querySelectorAll("[data-error-field]").forEach((link) => {
                const field = settingsForm.elements.namedItem(link.dataset.errorField);
                if (!field) return;
                field.id = `settings-field-${link.dataset.errorField}`;
                field.setAttribute("aria-invalid", "true");
                field.setAttribute("aria-describedby", "settings-error-summary");
                link.addEventListener("click", () => {
                    const section = field.closest("[data-settings-section]");
                    const tab = section && Array.from(tabs).find(
                        (item) => item.dataset.settingsTab === section.dataset.settingsSection
                    );
                    if (tab) activateSettingsTab(tab);
                    field.focus();
                });
            });
            errorSummary.focus();
        }
        const clearFieldError = (field) => {
            field.removeAttribute("aria-invalid");
            if (field.getAttribute("aria-describedby") === "settings-error-summary") {
                field.removeAttribute("aria-describedby");
            }
        };
        settingsForm.querySelectorAll("input, select, textarea").forEach((field) => {
            field.addEventListener("input", () => {
                if (field.checkValidity()) clearFieldError(field);
            });
            field.addEventListener("change", () => {
                if (field.checkValidity()) clearFieldError(field);
            });
        });
        settingsForm.addEventListener("submit", (event) => {
            settingsForm.querySelectorAll("[aria-invalid='true']").forEach(clearFieldError);
            const invalidFields = Array.from(settingsForm.querySelectorAll("input, select, textarea"))
                .filter((field) => !field.checkValidity());
            if (!invalidFields.length) {
                if (errorSummary) errorSummary.hidden = true;
                return;
            }
            event.preventDefault();
            invalidFields.forEach((field) => {
                field.setAttribute("aria-invalid", "true");
                field.setAttribute("aria-describedby", "settings-error-summary");
            });
            if (errorSummary) {
                errorSummary.hidden = false;
                errorSummary.focus();
            }
            const invalidSection = invalidFields[0].closest("[data-settings-section]");
            if (invalidSection) {
                const owningTab = Array.from(tabs).find(
                    (tab) => tab.dataset.settingsTab === invalidSection.dataset.settingsSection
                );
                if (owningTab) activateSettingsTab(owningTab);
            }
            invalidFields[0].focus();
        });
    }

    // ── Demo intro dismiss ────────────────────────────────────────────────
    const demoIntro = document.getElementById("demo-intro");
    const demoIntroDismiss = document.getElementById("demo-intro-dismiss");
    const INTRO_KEY = "rsvd-intro-dismissed";

    if (demoIntro) {
        if (sessionStorage.getItem(INTRO_KEY)) {
            demoIntro.hidden = true;
        }
        if (demoIntroDismiss) {
            demoIntroDismiss.addEventListener("click", () => {
                demoIntro.style.transition = "opacity .2s ease, transform .2s ease";
                demoIntro.style.opacity = "0";
                demoIntro.style.transform = "translateY(-6px)";
                setTimeout(() => { demoIntro.hidden = true; }, 220);
                sessionStorage.setItem(INTRO_KEY, "1");
            });
        }
    }

    // ── Guided walkthrough tour ───────────────────────────────────────────
    const TOUR_KEY = "rsvd-tour-v1";
    const tourEl       = document.getElementById("rsvd-tour");
    const tourBackdrop = document.getElementById("rsvd-tour-backdrop");
    const tourTitle    = document.getElementById("rsvd-tour-title");
    const tourBody     = document.getElementById("rsvd-tour-body");
    const tourCounter  = document.getElementById("rsvd-tour-counter");
    const tourPrev     = document.getElementById("rsvd-tour-prev");
    const tourNext     = document.getElementById("rsvd-tour-next");
    const tourSkip     = document.getElementById("rsvd-tour-skip");
    const startTourBtn = document.getElementById("start-tour-btn");

    const TOUR_STEPS = [
        {
            target: "[data-tour='estimated-tax']",
            title:  "Limited incremental estimate",
            body:   "This headline uses entered employment and freelance income. It omits savings, dividends, property, HICBC, tax already paid and other reliefs, so it is not a complete bill or assured set-aside amount.",
        },
        {
            target: "[data-tour='calculation']",
            title:  "Tax reserve breakdown",
            body:   "Reserved estimates the incremental Income Tax, Class 4 National Insurance and supported student-loan amount for an entered invoice. The breakdown is limited to those modelled components.",
        },
        {
            target: "[data-tour='chart']",
            title:  "Income and reserves",
            body:   "This illustrative chart compares freelance income with the limited modelled amount month by month; it does not establish a complete tax reserve.",
        },
        {
            target: "[data-tour='connections']",
            title:  "Connected accounts",
            body:   "In a future release, Reserved will read your real account balances automatically via open banking. This area shows what that will look like once bank connections are live.",
        },
    ];

    let tourStep = 0;

    function clearTourHighlight() {
        document.querySelectorAll(".rsvd-tour-highlight").forEach((el) => {
            el.classList.remove("rsvd-tour-highlight");
        });
    }

    function showTourStep(n) {
        const step   = TOUR_STEPS[n];
        const target = document.querySelector(step.target);
        tourTitle.textContent   = step.title;
        tourBody.textContent    = step.body;
        tourCounter.textContent = `${n + 1} of ${TOUR_STEPS.length}`;
        tourPrev.hidden         = n === 0;
        tourNext.textContent    = n === TOUR_STEPS.length - 1 ? "Done ✓" : "Next →";
        clearTourHighlight();
        if (target) {
            target.classList.add("rsvd-tour-highlight");
            target.scrollIntoView({ behavior: "smooth", block: "center" });
        }
        tourStep = n;
    }

    function dismissTour() {
        if (tourEl) tourEl.hidden = true;
        clearTourHighlight();
        localStorage.setItem(TOUR_KEY, "1");
    }

    function startTour() {
        if (!tourEl) return;
        tourEl.hidden = false;
        showTourStep(0);
    }

    if (startTourBtn) {
        startTourBtn.addEventListener("click", (e) => { e.preventDefault(); startTour(); });
    }

    if (tourEl) {
        // Auto-start if ?tour=1 is in the URL (linked from Overview "Take a tour" CTA)
        const _tourParam = new URLSearchParams(window.location.search).get("tour");
        if (_tourParam === "1") {
            history.replaceState(null, "", window.location.pathname);
            setTimeout(startTour, 600);
        // Otherwise auto-show only on pages that have the tour trigger button
        } else if (!localStorage.getItem(TOUR_KEY) && startTourBtn) {
            setTimeout(startTour, 1100);
        }
        if (tourSkip)     tourSkip.addEventListener("click", dismissTour);
        if (tourBackdrop) tourBackdrop.addEventListener("click", dismissTour);
        if (tourPrev)     tourPrev.addEventListener("click", () => { if (tourStep > 0) showTourStep(tourStep - 1); });
        if (tourNext) {
            tourNext.addEventListener("click", () => {
                if (tourStep < TOUR_STEPS.length - 1) showTourStep(tourStep + 1);
                else dismissTour();
            });
        }
        document.addEventListener("keydown", (e) => {
            if (!tourEl || tourEl.hidden) return;
            if (e.key === "Escape")       dismissTour();
            if (e.key === "ArrowRight" && tourStep < TOUR_STEPS.length - 1) showTourStep(tourStep + 1);
            if (e.key === "ArrowLeft"  && tourStep > 0)                     showTourStep(tourStep - 1);
        });
    }

    // ── Join Early Access ─────────────────────────────────────────────────
    const earlyAccessBtn    = document.getElementById("early-access-btn");
    const earlyAccessModal  = document.getElementById("early-access-modal");
    const earlyAccessClose  = document.getElementById("early-access-close");
    const earlyAccessForm   = document.getElementById("early-access-form");
    const earlyAccessThanks = document.getElementById("early-access-thanks");
    const modalBackgroundRegions = document.querySelectorAll(
        ".app-shell, #rsvd-tour, .action-pill-group"
    );

    function syncModalBackground() {
        const modalOpen = (earlyAccessModal && !earlyAccessModal.hidden) ||
            (feedbackModal && !feedbackModal.hidden);
        modalBackgroundRegions.forEach((region) => {
            if (modalOpen) {
                region.setAttribute("inert", "");
                region.setAttribute("aria-hidden", "true");
            } else {
                region.removeAttribute("inert");
                region.removeAttribute("aria-hidden");
            }
        });
    }

    const MODAL_FOCUSABLE = [
        "a[href]", "button:not([disabled])", "input:not([disabled]):not([type='hidden'])",
        "select:not([disabled])", "textarea:not([disabled])", "[tabindex]:not([tabindex='-1'])"
    ].join(",");

    function trapModalFocus(modal, event) {
        if (!modal || modal.hidden || event.key !== "Tab") return;
        const controls = Array.from(modal.querySelectorAll(MODAL_FOCUSABLE))
            .filter((control) => !control.hidden && control.getClientRects().length > 0);
        if (!controls.length) {
            event.preventDefault();
            modal.focus();
            return;
        }
        const first = controls[0];
        const last = controls[controls.length - 1];
        if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first.focus();
        }
    }

    function openEarlyAccess() {
        if (!earlyAccessModal) return;
        earlyAccessModal.hidden = false;
        if (feedbackModal) feedbackModal.hidden = true;
        syncModalBackground();
        const firstField = earlyAccessModal.querySelector("input:not([type='hidden']), button");
        if (firstField) firstField.focus();
    }
    function closeEarlyAccess() {
        if (earlyAccessModal) earlyAccessModal.hidden = true;
        syncModalBackground();
        if (earlyAccessBtn) earlyAccessBtn.focus();
    }

    if (earlyAccessBtn)   earlyAccessBtn.addEventListener("click", openEarlyAccess);
    if (earlyAccessClose) earlyAccessClose.addEventListener("click", closeEarlyAccess);

    const earlyAccessDuplicate = document.getElementById("early-access-duplicate");
    const earlyAccessError     = document.getElementById("early-access-error");

    function _eaShowError(msg, field = null) {
        if (!earlyAccessError) return;
        earlyAccessError.textContent = msg;
        earlyAccessError.hidden = false;
        if (field) {
            field.setAttribute("aria-invalid", "true");
            field.setAttribute("aria-describedby", "early-access-error");
            field.focus();
        } else {
            earlyAccessError.tabIndex = -1;
            earlyAccessError.focus();
        }
    }
    function _eaReset() {
        if (earlyAccessError)     { earlyAccessError.hidden = true; earlyAccessError.textContent = ""; }
        if (earlyAccessForm) earlyAccessForm.querySelectorAll("[aria-invalid='true']").forEach((field) => {
            field.removeAttribute("aria-invalid");
            field.removeAttribute("aria-describedby");
        });
        if (earlyAccessDuplicate)   earlyAccessDuplicate.hidden = true;
        if (earlyAccessThanks)      earlyAccessThanks.hidden = true;
        if (earlyAccessForm)        earlyAccessForm.hidden = false;
    }

    if (earlyAccessForm) {
        earlyAccessForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            if (earlyAccessError) earlyAccessError.hidden = true;
            const nameField  = earlyAccessForm.querySelector("[name='name']");
            const emailField = earlyAccessForm.querySelector("[name='email']");
            [nameField, emailField].forEach((field) => {
                field.removeAttribute("aria-invalid");
                field.removeAttribute("aria-describedby");
            });
            if (!nameField.value.trim())  { _eaShowError("Please enter your name.", nameField); return; }
            if (!emailField.value.trim() || !emailField.checkValidity()) {
                _eaShowError("Please enter a valid email address.", emailField);
                return;
            }

            const submitBtn = earlyAccessForm.querySelector("[type='submit']");
            if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = "Sending…"; }

            const data = new FormData(earlyAccessForm);
            const csrfMeta = document.querySelector("meta[name='csrf-token']");
            if (csrfMeta) data.append("csrf_token", csrfMeta.content);

            let json = { ok: false };
            try {
                const resp = await fetch("/early-access", { method: "POST", body: data });
                json = await resp.json();
            } catch (_) {}

            if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = "Request access"; }

            if (json.ok && json.duplicate) {
                earlyAccessForm.hidden = true;
                if (earlyAccessDuplicate) earlyAccessDuplicate.hidden = false;
                setTimeout(() => { closeEarlyAccess(); setTimeout(_eaReset, 300); }, 3000);
            } else if (json.ok) {
                earlyAccessForm.hidden = true;
                if (earlyAccessThanks) earlyAccessThanks.hidden = false;
                setTimeout(() => { closeEarlyAccess(); setTimeout(_eaReset, 300); }, 3000);
            } else {
                _eaShowError(json.error || "Something went wrong — please try again.");
            }
        });
    }

    // ── Share Feedback ────────────────────────────────────────────────────
    const feedbackBtn    = document.getElementById("feedback-btn");
    const feedbackModal  = document.getElementById("feedback-modal");
    const feedbackClose  = document.getElementById("feedback-close");
    const feedbackForm   = document.getElementById("feedback-form");
    const feedbackThanks = document.getElementById("feedback-thanks");

    function openFeedback() {
        if (!feedbackModal) return;
        feedbackModal.hidden = false;
        if (earlyAccessModal) earlyAccessModal.hidden = true;
        syncModalBackground();
        const firstControl = feedbackModal.querySelector("button, input, textarea");
        if (firstControl) firstControl.focus();
    }
    function closeFeedback() {
        if (feedbackModal) feedbackModal.hidden = true;
        syncModalBackground();
        if (feedbackBtn) feedbackBtn.focus();
    }

    if (feedbackBtn)   feedbackBtn.addEventListener("click", openFeedback);
    if (feedbackClose) feedbackClose.addEventListener("click", closeFeedback);

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            if (earlyAccessModal && !earlyAccessModal.hidden) closeEarlyAccess();
            if (feedbackModal && !feedbackModal.hidden) closeFeedback();
            return;
        }
        trapModalFocus(earlyAccessModal, e);
        trapModalFocus(feedbackModal, e);
    });

    const feedbackError = document.getElementById("feedback-error");

    if (feedbackForm) {
        feedbackForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            if (feedbackError) feedbackError.hidden = true;

            const submitBtn = feedbackForm.querySelector("[type='submit']");
            if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = "Sending…"; }

            const data = new FormData(feedbackForm);
            const csrfMeta = document.querySelector("meta[name='csrf-token']");
            if (csrfMeta) data.append("csrf_token", csrfMeta.content);

            let json = { ok: false };
            try {
                const resp = await fetch("/feedback", { method: "POST", body: data });
                json = await resp.json();
            } catch (_) {}

            if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = "Send feedback"; }

            if (json.ok) {
                feedbackForm.hidden = true;
                if (feedbackThanks) feedbackThanks.hidden = false;
                setTimeout(() => {
                    closeFeedback();
                    setTimeout(() => {
                        feedbackForm.hidden = false;
                        if (feedbackThanks) feedbackThanks.hidden = true;
                        feedbackForm.reset();
                    }, 300);
                }, 2200);
            } else {
                if (feedbackError) {
                    feedbackError.textContent = json.error || "Something went wrong — please try again.";
                    feedbackError.hidden = false;
                    feedbackError.tabIndex = -1;
                    feedbackError.focus();
                }
            }
        });
    }

    // ── Shared Escape handler ─────────────────────────────────────────────
    document.addEventListener("keydown", (e) => {
        if (e.key !== "Escape") return;
        if (feedbackModal     && !feedbackModal.hidden)     closeFeedback();
        if (earlyAccessModal  && !earlyAccessModal.hidden)  closeEarlyAccess();
    });
});
