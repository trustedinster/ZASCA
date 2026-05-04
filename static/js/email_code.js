// email_code.js
// Handles "Get code" button on registration and forgot password pages.
// If CAPTCHA_PROVIDER == 'geetest', it will open geetest popup via initGeetest4 and then POST v4 params + email to /accounts/email/send-code/ or /accounts/email/send-forgot-password-code/
// Otherwise, it will POST only the email to the endpoint.

(function(){
    function qs(sel){ return document.querySelector(sel); }
    var btn = qs('#get-email-code');
    if(!btn) return;

    // 倒计时功能
    var countdownTimers = {};
    
    function startCountdown(button, initialText = null) {
        var buttonId = button.id || 'unknown-button';
        
        // 清除之前的倒计时
        if (countdownTimers[buttonId]) {
            clearInterval(countdownTimers[buttonId]);
        }
        
        let count = 60;
        const originalText = initialText || button.textContent || button.innerText;
        button.disabled = true;
        
        // 更新按钮文本显示倒计时
        button.textContent = `${originalText} (${count}s)`;
        
        countdownTimers[buttonId] = setInterval(() => {
            count--;
            button.textContent = `${originalText} (${count}s)`;
            
            if (count <= 0) {
                clearInterval(countdownTimers[buttonId]);
                delete countdownTimers[buttonId];
                button.disabled = false;
                button.textContent = originalText;
            }
        }, 1000);
    }

    btn.addEventListener('click', function(e){
        e.preventDefault();
        var emailInput = document.querySelector('input[name="email"]') || document.querySelector('input[type="email"]');
        var email = emailInput && emailInput.value && emailInput.value.trim();
        if(!email){ alert('请先输入邮箱'); return; }

        // Check if we're on the forgot password page
        var isForgotPassword = window.location.pathname.includes('forgot-password');
        var endpoint = isForgotPassword ? '/accounts/email/send-forgot-password-code/' : '/accounts/email/send-code/';

        // CAPTCHA_PROVIDER is injected in template context as CAPTCHA_PROVIDER
        var provider = window.CAPTCHA_PROVIDER || document.body.getAttribute('data-captcha-provider') || 'none';

        function postCode(payload, buttonRef){
            fetch(endpoint, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'X-CSRFToken': window.getCsrfToken ? window.getCsrfToken() : (document.querySelector('[name=csrfmiddlewaretoken]')?.value || '')
                },
                body: payload
            }).then(function(resp){
                if(resp.ok) {
                    alert('验证码已发送，请注意查收');
                    // 开始倒计时
                    if(buttonRef) {
                        startCountdown(buttonRef, '获取验证码');
                    }
                } else {
                    // 请求失败时恢复按钮状态
                    if(buttonRef) {
                        buttonRef.disabled = false;
                        buttonRef.textContent = '获取验证码';
                    }
                    resp.json().then(function(j){ alert('发送失败：' + (j.message || JSON.stringify(j))); }).catch(function(){ alert('发送失败'); });
                }
            }).catch(function(err){ 
                console.error(err); 
                // 请求失败时恢复按钮状态
                if(buttonRef) {
                    buttonRef.disabled = false;
                    buttonRef.textContent = '获取验证码';
                }
                alert('网络错误'); 
            });
        }

        if(provider === 'geetest'){
            var emailCaptchaId = btn.getAttribute('data-captcha-id') || window.GEETEST_CAPTCHA_ID;
            if(!emailCaptchaId){
                alert('Geetest captcha ID 未配置');
                return;
            }
            initGeetest4({
                captchaId: emailCaptchaId,
                product: 'bind'
            }, function(captchaObj){
                captchaObj.onReady(function(){
                    captchaObj.showCaptcha();
                });
                captchaObj.onSuccess(function(){
                    var result = captchaObj.getValidate();
                    if(!result){
                        alert('验证结果获取失败，请重试');
                        return;
                    }
                    var form = new FormData();
                    form.append('email', email);
                    form.append('lot_number', result.lot_number || '');
                    form.append('captcha_output', result.captcha_output || '');
                    form.append('pass_token', result.pass_token || '');
                    form.append('gen_time', result.gen_time || '');
                    form.append('captcha_id', emailCaptchaId);
                    postCode(form, btn);
                });
                captchaObj.onError(function(error){
                    console.error('Geetest v4 error:', error);
                    alert('验证码加载失败，请稍后重试');
                });
                captchaObj.onClose(function(){
                });
            });
        } else if(provider === 'local') {
            // 如果是本地验证码，不应该到达这里，因为local_captcha_adapter.js会处理
            // 但为了兼容性，我们也可以处理
            alert('本地验证码需要先完成验证');
        } else {
            if(provider === 'turnstile'){
                var sitekey = window.TURNSTILE_SITE_KEY || (document.getElementById('turnstile_site_key') && document.getElementById('turnstile_site_key').value);
                if(!sitekey){ alert('Turnstile site key 未配置'); return; }
                // execute turnstile
                if(typeof window.executeTurnstile === 'function'){
                    window.executeTurnstile(sitekey, function(err, token){
                        if(err){ alert('Turnstile 验证失败'); return; }
                        var fd = new FormData(); fd.append('email', email); fd.append('cf-turnstile-response', token);
                        postCode(fd, btn); // Pass button reference for countdown
                    });
                } else {
                    alert('Turnstile adapter 未加载');
                }
            } else {
                var fd = new FormData(); fd.append('email', email);
                postCode(fd, btn); // Pass button reference for countdown
            }
        }
    });
})();