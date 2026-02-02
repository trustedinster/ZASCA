// turnstile_adapter.js
// Minimal adapter to render Cloudflare Turnstile widgets programmatically.
// Usage:
// - For login button, add data-turnstile-trigger to the button; adapter will render an invisible widget and submit the form when token is obtained.
// - For custom flows (like email code), call window.executeTurnstile(callback) to run an invisible widget and receive token.

(function(){
    function loadScript(src, cb){
        if(window.turnstile) return cb();
        var s = document.createElement('script');
        s.src = src;
        s.async = true;
        s.onload = cb;
        s.onerror = function(){ console.error('Failed to load turnstile script'); };
        document.head.appendChild(s);
    }

    function ensureContainer(){
        var id = 'turnstile-popup-container';
        var c = document.getElementById(id);
        if(!c){ c = document.createElement('div'); c.id = id; c.style.display='none'; document.body.appendChild(c); }
        return c;
    }

    function renderInvisible(sitekey, callback){
        loadScript('https://challenges.cloudflare.com/turnstile/v0/api.js', function(){
            var container = ensureContainer();
            container.innerHTML = '';
            // render invisible widget
            var widgetId = window.turnstile.render(container, {
                sitekey: sitekey,
                size: 'invisible',
                callback: function(token){
                    callback(null, token);
                },
                'error-callback': function(){ callback(new Error('turnstile error')); },
                'expired-callback': function(){ callback(new Error('turnstile expired')); }
            });
            // execute
            try{ window.turnstile.execute(widgetId); }catch(e){ console.error(e); }
        });
    }

    window.executeTurnstile = function(sitekey, cb){
        if(!sitekey){ return cb(new Error('missing sitekey')); }
        renderInvisible(sitekey, cb);
    };

    // attach to buttons with data-turnstile-trigger
    document.addEventListener('DOMContentLoaded', function(){
        var btns = document.querySelectorAll('[data-turnstile-trigger]');
        Array.prototype.forEach.call(btns, function(btn){
            btn.addEventListener('click', function(e){
                e.preventDefault();
                var form = btn.closest('form');
                var sitekey = window.TURNSTILE_SITE_KEY || btn.getAttribute('data-turnstile-sitekey');
                if(!sitekey){ alert('Turnstile site key 未配置'); return; }
                executeTurnstile(sitekey, function(err, token){
                    if(err){ alert('Turnstile 验证失败'); return; }
                    // put token into hidden input
                    var input = form.querySelector('input[name="cf-turnstile-response"]');
                    if(!input){ input = document.createElement('input'); input.type='hidden'; input.name='cf-turnstile-response'; form.appendChild(input); }
                    input.value = token;
                    // submit form
                    form.submit();
                });
            });
        });
    });
})();
