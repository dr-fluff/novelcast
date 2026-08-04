// novelcast/static/js/password_strength.js
//
// Data-attribute driven password UX, shared across every password form:
//   data-password-strength="<meterId>"       live strength bar + checklist
//   data-password-match="<otherInputId>"     live "passwords match" check
//   data-verify-password-url="<url>"         live server-side current-password check
//   form[data-password-guard]                 blocks submit until the above pass
//
// Mirrors novelcast.utils.password_validation.validate_password_strength —
// keep the two in sync if the rules ever change server-side.

(function () {
    'use strict';

    const RULES = [
        { key: 'length', label: 'At least 8 characters', test: (pw) => pw.length >= 8 },
        { key: 'lower', label: 'A lowercase letter', test: (pw) => /[a-z]/.test(pw) },
        { key: 'upper', label: 'An uppercase letter', test: (pw) => /[A-Z]/.test(pw) },
        { key: 'digit', label: 'A number', test: (pw) => /\d/.test(pw) },
        { key: 'special', label: 'A special character', test: (pw) => /[^\w\s]/.test(pw) },
    ];

    function evaluate(password) {
        const results = RULES.map((r) => ({ key: r.key, label: r.label, met: r.test(password) }));
        const score = results.filter((r) => r.met).length;
        return { results, score, valid: score === RULES.length };
    }

    function strengthMeta(score) {
        if (score <= 1) return { label: 'Weak', className: 'weak' };
        if (score <= 3) return { label: 'Okay', className: 'okay' };
        if (score === 4) return { label: 'Good', className: 'good' };
        return { label: 'Strong', className: 'strong' };
    }

    function buildMeter(container) {
        container.innerHTML =
            '<div class="password-meter__bar"><div class="password-meter__fill"></div></div>' +
            '<div class="password-meter__label"></div>' +
            '<ul class="password-meter__checklist"></ul>';

        const list = container.querySelector('.password-meter__checklist');
        RULES.forEach((rule) => {
            const item = document.createElement('li');
            item.dataset.check = rule.key;
            item.textContent = rule.label;
            list.appendChild(item);
        });
    }

    function updateMeter(container, password) {
        const { results, score, valid } = evaluate(password);
        const fill = container.querySelector('.password-meter__fill');
        const label = container.querySelector('.password-meter__label');
        const meta = strengthMeta(score);

        fill.className = 'password-meter__fill password-meter__fill--' + meta.className;
        fill.style.width = password.length === 0 ? '0%' : (score / RULES.length) * 100 + '%';

        label.textContent = password.length === 0 ? '' : meta.label;
        label.className = 'password-meter__label password-meter__label--' + meta.className;

        results.forEach((rule) => {
            const item = container.querySelector('[data-check="' + rule.key + '"]');
            if (item) item.classList.toggle('met', rule.met);
        });

        return valid;
    }

    function attachStrengthMeter(input) {
        const container = document.getElementById(input.dataset.passwordStrength);
        if (!container) return;
        buildMeter(container);
        updateMeter(container, input.value);
        input.addEventListener('input', () => updateMeter(container, input.value));
    }

    function attachMatchCheck(input) {
        const other = document.getElementById(input.dataset.passwordMatch);
        const message = input.dataset.passwordMatchMessage
            ? document.getElementById(input.dataset.passwordMatchMessage)
            : null;
        if (!other) return;

        function check() {
            if (!input.value && !other.value) {
                input.classList.remove('input--valid', 'input--invalid');
                if (message) message.textContent = '';
                return;
            }
            const matches = input.value === other.value;
            input.classList.toggle('input--invalid', !matches);
            input.classList.toggle('input--valid', matches && input.value.length > 0);
            if (message) message.textContent = matches ? '' : "Passwords don't match.";
        }

        input.addEventListener('input', check);
        other.addEventListener('input', check);
    }

    function attachCurrentPasswordCheck(input) {
        const endpoint = input.dataset.verifyPasswordUrl;
        const message = input.dataset.verifyPasswordMessage
            ? document.getElementById(input.dataset.verifyPasswordMessage)
            : null;
        if (!endpoint) return;

        let debounceTimer = null;
        let lastChecked = null;
        input.dataset.verified = 'unknown';

        function setState(state, text) {
            input.dataset.verified = state;
            input.classList.remove('input--valid', 'input--invalid', 'input--checking');
            if (state === 'valid') input.classList.add('input--valid');
            if (state === 'invalid') input.classList.add('input--invalid');
            if (state === 'checking') input.classList.add('input--checking');
            if (message) message.textContent = text || '';
        }

        function verify() {
            const value = input.value;
            if (!value) {
                setState('unknown', '');
                return;
            }
            if (value === lastChecked) return;

            setState('checking', 'Checking...');

            fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ current_password: value }),
            })
                .then((res) => res.json())
                .then((data) => {
                    lastChecked = value;
                    setState(
                        data.valid ? 'valid' : 'invalid',
                        data.valid ? 'Current password confirmed.' : "That's not your current password."
                    );
                })
                .catch(() => setState('unknown', ''));
        }

        input.addEventListener('blur', verify);
        input.addEventListener('input', () => {
            setState('unknown', '');
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(verify, 600);
        });
    }

    function attachFormGuard(form) {
        form.addEventListener('submit', (event) => {
            const strengthInputs = form.querySelectorAll('[data-password-strength]');
            for (const input of strengthInputs) {
                const container = document.getElementById(input.dataset.passwordStrength);
                if (container && !updateMeter(container, input.value)) {
                    event.preventDefault();
                    input.focus();
                    return;
                }
            }

            const matchInputs = form.querySelectorAll('[data-password-match]');
            for (const input of matchInputs) {
                const other = document.getElementById(input.dataset.passwordMatch);
                if (other && input.value !== other.value) {
                    event.preventDefault();
                    input.focus();
                    return;
                }
            }

            const verifyInputs = form.querySelectorAll('[data-verify-password-url]');
            for (const input of verifyInputs) {
                if (input.dataset.verified === 'invalid') {
                    event.preventDefault();
                    input.focus();
                    return;
                }
            }
        });
    }

    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll('[data-password-strength]').forEach(attachStrengthMeter);
        document.querySelectorAll('[data-password-match]').forEach(attachMatchCheck);
        document.querySelectorAll('[data-verify-password-url]').forEach(attachCurrentPasswordCheck);
        document.querySelectorAll('form[data-password-guard]').forEach(attachFormGuard);
    });
})();
