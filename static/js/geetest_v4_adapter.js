(function () {
    function $all(sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); }

    var defaultCaptchaId = window.GEETEST_CAPTCHA_ID || null;

    function initOnTrigger() {
        var triggers = $all('[data-geetest-trigger]:not([data-geetest-email-trigger])');
        triggers.forEach(function (btn) {
            var form = btn.closest('form');
            var captchaId = btn.getAttribute('data-captcha-id') || defaultCaptchaId;
            if (!captchaId) {
                console.error('captchaId not provided for Geetest v4');
                return;
            }

            var captchaInstance = null;
            var ready = false;

            initGeetest4({
                captchaId: captchaId,
                product: 'bind'
            }, function (captchaObj) {
                captchaInstance = captchaObj;

                captchaObj.onReady(function () {
                    ready = true;
                });

                captchaObj.onSuccess(function () {
                    var result = captchaObj.getValidate();
                    if (!result) {
                        alert('验证结果获取失败，请重试');
                        return;
                    }

                    if (form) {
                        var inLot = form.querySelector('input[name="lot_number"]');
                        var inOutput = form.querySelector('input[name="captcha_output"]');
                        var inPass = form.querySelector('input[name="pass_token"]');
                        var inGen = form.querySelector('input[name="gen_time"]');
                        var inCid = form.querySelector('input[name="captcha_id"]');

                        if (inLot) inLot.value = result.lot_number || '';
                        if (inOutput) inOutput.value = result.captcha_output || '';
                        if (inPass) inPass.value = result.pass_token || '';
                        if (inGen) inGen.value = result.gen_time || '';
                        if (inCid) inCid.value = captchaId;
                    }

                    if (form) form.submit();
                });

                captchaObj.onError(function (error) {
                    console.error('Geetest v4 error:', error);
                    alert('验证码加载失败，请稍后重试');
                });
            });

            btn.addEventListener('click', function (e) {
                e.preventDefault();
                if (ready && captchaInstance) {
                    captchaInstance.showCaptcha();
                }
            });

            if (form) {
                form.addEventListener('submit', function (e) {
                    var passTokenInput = form.querySelector('input[name="pass_token"]');
                    var passTokenValue = passTokenInput ? passTokenInput.value : '';
                    if (!passTokenValue && window.CAPTCHA_PROVIDER === 'geetest') {
                        e.preventDefault();
                        if (ready && captchaInstance) {
                            captchaInstance.showCaptcha();
                        }
                    }
                });
            }
        });
    }

    window.initGeetestAdapter = {
        initOnTrigger: initOnTrigger
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            initOnTrigger();
        });
    } else {
        initOnTrigger();
    }
})();
