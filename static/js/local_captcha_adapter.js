class LocalCaptchaAdapter {
    constructor(options = {}) {
        this.options = {
            product: options.product || 'popup',
            ...options
        };
        this.captchaId = null;
        this.modal = null;
        this.resolveCallback = null;
    }

    async showBox() {
        return new Promise((resolve) => {
            this.resolveCallback = resolve;
            this._createModal();
        });
    }

    _createModal() {
        const existing = document.getElementById('local-captcha-overlay');
        if (existing) existing.remove();

        const overlay = document.createElement('div');
        overlay.id = 'local-captcha-overlay';
        overlay.className = 'fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 backdrop-blur-md';

        const modal = document.createElement('div');
        modal.id = 'local-captcha-modal';
        modal.className = 'bg-black/90 backdrop-blur-2xl border border-white/10 rounded-md-lg shadow-2xl p-6 w-[320px] max-w-[90vw] relative';

        const title = document.createElement('h3');
        title.className = 'text-lg font-medium text-white mb-4 flex items-center gap-2';
        title.innerHTML = '<span class="material-symbols-rounded text-cyan-400">verified_user</span>请输入验证码';

        const imgRow = document.createElement('div');
        imgRow.className = 'flex items-center gap-3 mb-4';

        const captchaImg = document.createElement('img');
        captchaImg.id = 'captcha-image';
        captchaImg.className = 'h-10 w-[120px] border border-slate-700/50 rounded-md cursor-pointer hover:opacity-80 transition';
        captchaImg.alt = '验证码';
        captchaImg.title = '点击刷新验证码';
        captchaImg.addEventListener('click', () => this._refreshCaptcha());

        const refreshBtn = document.createElement('button');
        refreshBtn.type = 'button';
        refreshBtn.className = 'flex items-center justify-center w-9 h-9 rounded-full bg-slate-800/50 border border-slate-700/50 text-slate-400 hover:text-cyan-400 transition cursor-pointer';
        refreshBtn.title = '刷新验证码';
        refreshBtn.innerHTML = '<span class="material-symbols-rounded text-xl">refresh</span>';
        refreshBtn.addEventListener('click', () => this._refreshCaptcha());

        imgRow.appendChild(captchaImg);
        imgRow.appendChild(refreshBtn);

        const input = document.createElement('input');
        input.type = 'text';
        input.id = 'captcha-input';
        input.placeholder = '请输入验证码';
        input.maxLength = 4;
        input.autocomplete = 'off';
        input.className = 'w-full bg-slate-900/50 border border-slate-700/50 rounded-md px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 transition text-center text-lg tracking-[0.3em] uppercase';

        const errorMsg = document.createElement('p');
        errorMsg.id = 'captcha-error';
        errorMsg.className = 'text-sm text-red-400 mt-1 hidden';

        const btnRow = document.createElement('div');
        btnRow.className = 'flex gap-3 mt-4';

        const cancelBtn = document.createElement('button');
        cancelBtn.type = 'button';
        cancelBtn.className = 'flex-1 bg-slate-800/50 border border-slate-700/50 rounded-md px-4 py-2.5 text-slate-300 hover:bg-slate-700/50 transition font-medium cursor-pointer';
        cancelBtn.textContent = '取消';
        cancelBtn.addEventListener('click', () => {
            this._closeModal();
            if (this.resolveCallback) {
                this.resolveCallback({ status: 'closed' });
            }
        });

        const confirmBtn = document.createElement('button');
        confirmBtn.type = 'button';
        confirmBtn.className = 'flex-1 bg-cyan-600 hover:bg-cyan-500 text-white rounded-md px-4 py-2.5 shadow-[0_0_15px_-3px_rgba(34,211,238,0.3)] transition font-medium cursor-pointer';
        confirmBtn.textContent = '确认';
        confirmBtn.addEventListener('click', () => this._verifyCaptcha());

        btnRow.appendChild(cancelBtn);
        btnRow.appendChild(confirmBtn);

        modal.appendChild(title);
        modal.appendChild(imgRow);
        modal.appendChild(input);
        modal.appendChild(errorMsg);
        modal.appendChild(btnRow);
        overlay.appendChild(modal);

        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                this._closeModal();
                if (this.resolveCallback) {
                    this.resolveCallback({ status: 'closed' });
                }
            }
        });

        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this._verifyCaptcha();
        });

        document.body.appendChild(overlay);

        this._generateCaptcha();

        setTimeout(() => input.focus(), 100);
    }

    async _generateCaptcha() {
        try {
            const resp = await fetch('/accounts/captcha/generate/');
            const data = await resp.json();
            if (data.captcha_id) {
                this.captchaId = data.captcha_id;
                const img = document.getElementById('captcha-image');
                if (img) {
                    img.src = `/accounts/captcha/image/${this.captchaId}/?t=${Date.now()}`;
                }
            }
        } catch (err) {
            console.error('生成验证码失败:', err);
            this._showError('验证码生成失败，请稍后重试');
        }
    }

    async _refreshCaptcha() {
        const input = document.getElementById('captcha-input');
        if (input) input.value = '';
        this._hideError();
        await this._generateCaptcha();
    }

    async _verifyCaptcha() {
        const input = document.getElementById('captcha-input');
        const userInput = input ? input.value.trim() : '';

        if (!userInput) {
            this._showError('请输入验证码');
            return;
        }

        if (!this.captchaId) {
            this._showError('验证码已过期，请重新获取');
            await this._generateCaptcha();
            return;
        }

        this._closeModal();

        const result = {
            status: 'success',
            lot_number: this.captchaId,
            captcha_output: userInput,
            pass_token: 'local_captcha_pass_token',
            gen_time: Date.now().toString(),
            captcha_id: this.captchaId
        };

        window._localCaptchaResult = result;

        if (this.resolveCallback) {
            this.resolveCallback(result);
        }
    }

    _showError(msg) {
        const el = document.getElementById('captcha-error');
        if (el) {
            el.textContent = msg;
            el.classList.remove('hidden');
        }
    }

    _hideError() {
        const el = document.getElementById('captcha-error');
        if (el) el.classList.add('hidden');
    }

    _closeModal() {
        const overlay = document.getElementById('local-captcha-overlay');
        if (overlay) overlay.remove();
        this.modal = null;
    }

    getCsrfToken() {
        return window.getCsrfToken ? window.getCsrfToken() :
            (document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
                document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1] || '');
    }

    static initGeetest(config, callback) {
        const adapter = new LocalCaptchaAdapter(config);
        callback(adapter);
    }
}

window.initGeetest4 = LocalCaptchaAdapter.initGeetest;

function _fillHiddenFields(result) {
    const suffixes = ['login', 'reg', 'forgot'];
    suffixes.forEach(suffix => {
        const lotEl = document.getElementById(`lot_number_${suffix}`);
        const outEl = document.getElementById(`captcha_output_${suffix}`);
        const passEl = document.getElementById(`pass_token_${suffix}`);
        const genEl = document.getElementById(`gen_time_${suffix}`);
        if (lotEl) lotEl.value = result.lot_number;
        if (outEl) outEl.value = result.captcha_output;
        if (passEl) passEl.value = result.pass_token;
        if (genEl) genEl.value = result.gen_time;
    });
}

function _sendEmailCodeRequest(button) {
    const emailField = document.querySelector('input[type="email"]');
    if (!emailField || !emailField.value) {
        alert('请先填写邮箱地址');
        return;
    }

    let endpoint;
    if (window.location.pathname.includes('/register/')) {
        endpoint = '/accounts/email/send-code/';
    } else if (window.location.pathname.includes('/forgot-password/')) {
        endpoint = '/accounts/email/send-forgot-password-code/';
    } else {
        alert('无法确定当前页面类型');
        return;
    }

    const result = window._localCaptchaResult;
    const formData = new FormData();
    formData.append('email', emailField.value);
    if (result) {
        if (result.lot_number) formData.append('lot_number', result.lot_number);
        if (result.captcha_output) formData.append('captcha_output', result.captcha_output);
        if (result.pass_token) formData.append('pass_token', result.pass_token);
        if (result.gen_time) formData.append('gen_time', result.gen_time);
    }

    fetch(endpoint, {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': window.getCsrfToken ? window.getCsrfToken() : (document.querySelector('[name=csrfmiddlewaretoken]')?.value || '')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            alert('验证码已发送到您的邮箱');
            _startCountdown(button, '获取验证码');
        } else {
            alert(data.message || '发送验证码失败');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('发送验证码时发生错误');
    });
}

let _countdownTimer = null;

function _startCountdown(button, initialText) {
    if (_countdownTimer) clearInterval(_countdownTimer);

    let count = 60;
    const originalText = initialText || '获取验证码';
    button.disabled = true;
    button.textContent = `${originalText} (${count}s)`;

    _countdownTimer = setInterval(() => {
        count--;
        button.textContent = `${originalText} (${count}s)`;
        if (count <= 0) {
            clearInterval(_countdownTimer);
            _countdownTimer = null;
            button.disabled = false;
            button.textContent = originalText;
        }
    }, 1000);
}

document.addEventListener('DOMContentLoaded', function () {
    if (window.CAPTCHA_PROVIDER !== 'local') return;

    document.querySelectorAll('#get-email-code[data-local-captcha-trigger]').forEach(button => {
        const newBtn = button.cloneNode(true);
        button.parentNode.replaceChild(newBtn, button);

        newBtn.addEventListener('click', async function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            if (this.disabled) return;

            const emailField = document.querySelector('input[type="email"]');
            if (!emailField || !emailField.value) {
                alert('请先填写邮箱地址');
                emailField?.focus();
                return;
            }

            const adapter = new LocalCaptchaAdapter({ product: 'popup' });
            const result = await adapter.showBox();

            if (result && result.status === 'success') {
                _fillHiddenFields(result);
                _sendEmailCodeRequest(this);
            }
        });
    });

    document.querySelectorAll('[data-local-captcha-trigger]:not(#get-email-code)').forEach(button => {
        button.addEventListener('click', async function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();

            const adapter = new LocalCaptchaAdapter({ product: 'popup' });
            const result = await adapter.showBox();

            if (result && result.status === 'success') {
                _fillHiddenFields(result);

                const action = this.dataset.action;
                if (action === 'submit') {
                    let form = this.closest('form');
                    if (form) form.submit();
                }
            }
        });
    });
});
