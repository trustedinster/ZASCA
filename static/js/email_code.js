// email_code.js
// Handles "Get code" button on registration page.
// If CAPTCHA_PROVIDER == 'geetest', it will open geetest popup via initGeetest4 and then POST v4 params + email to /accounts/email/send-code/
// Otherwise, it will POST only the email to the endpoint.

(function(){
    function qs(sel){ return document.querySelector(sel); }
    var btn = qs('#get-email-code');
    if(!btn) return;

    btn.addEventListener('click', function(e){
        e.preventDefault();
        var emailInput = document.querySelector('input[name="email"]') || document.querySelector('input[type="email"]');
        var email = emailInput && emailInput.value && emailInput.value.trim();
        if(!email){ alert('请先输入邮箱'); return; }

        // CAPTCHA_PROVIDER is injected in template context as CAPTCHA_PROVIDER
        var provider = window.CAPTCHA_PROVIDER || document.body.getAttribute('data-captcha-provider') || 'none';

        function getCsrfToken() {
            // Try multiple methods to get CSRF token
            return document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
                   document.querySelector('[name="csrf-token"]')?.getAttribute('content') ||
                   document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') ||
                   window.Config?.csrfToken ||
                   '';
        }

        function postCode(payload){
            fetch('/accounts/email/send-code/', {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'X-CSRFToken': getCsrfToken() || document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
                },
                body: payload
            }).then(function(resp){
                if(resp.ok) {
                    alert('验证码已发送，请注意查收');
                } else {
                    resp.json().then(function(j){ alert('发送失败：' + (j.message || JSON.stringify(j))); }).catch(function(){ alert('发送失败'); });
                }
            }).catch(function(err){ console.error(err); alert('网络错误'); });
        }

        if(provider === 'geetest'){
            // show geetest popup, use adapter's mechanism: initGeetest4 and onSuccess
            initGeetest4({ captchaId: window.GEETEST_CAPTCHA_ID || window.GEETEST_CAPTCHA_ID || (document.getElementById('captcha_id') && document.getElementById('captcha_id').value) }, function(captcha){
                var container = document.getElementById('geetest-email-popup');
                if(!container){ container = document.createElement('div'); container.id='geetest-email-popup'; document.body.appendChild(container);}
                container.innerHTML = '';
                try{ captcha.appendTo(container); } catch(e){ captcha.appendTo('#' + container.id); }
                if(typeof captcha.onSuccess === 'function'){
                    captcha.onSuccess(function(){
                        var res = null;
                        try{ if(typeof captcha.getValidate === 'function') res = captcha.getValidate(); else if(typeof captcha.getResponse === 'function') res = captcha.getResponse(); }catch(e){}
                        var form = new FormData();
                        form.append('email', email);
                        if(res){
                            form.append('lot_number', res.lot_number || res.lotNumber || '');
                            form.append('captcha_output', res.captcha_output || res.captchaOutput || '');
                            form.append('pass_token', res.pass_token || res.passToken || '');
                            form.append('gen_time', res.gen_time || res.genTime || '');
                            form.append('captcha_id', document.getElementById('captcha_id') ? document.getElementById('captcha_id').value : '');
                        }
                        postCode(form);
                        try{ container.remove(); } catch(e){ container.style.display='none'; }
                    });
                } else {
                    alert('当前验证码组件不支持回调，请刷新页面');
                }
            });
        } else {
            if(provider === 'turnstile'){
                var sitekey = window.TURNSTILE_SITE_KEY || (document.getElementById('turnstile_site_key') && document.getElementById('turnstile_site_key').value);
                if(!sitekey){ alert('Turnstile site key 未配置'); return; }
                // execute turnstile
                if(typeof window.executeTurnstile === 'function'){
                    window.executeTurnstile(sitekey, function(err, token){
                        if(err){ alert('Turnstile 验证失败'); return; }
                        var fd = new FormData(); fd.append('email', email); fd.append('cf-turnstile-response', token);
                        postCode(fd);
                    });
                } else {
                    alert('Turnstile adapter 未加载');
                }
            } else {
                var fd = new FormData(); fd.append('email', email);
                postCode(fd);
            }
        }
    });
})();