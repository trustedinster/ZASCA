/**
 * 本地图形验证码适配器
 * 提供与Geetest和Turnstile类似的功能接口
 */

class LocalCaptchaAdapter {
    constructor(options = {}) {
        this.options = {
            container: options.container || 'body',
            product: options.product || 'popup', // popup or bind
            ...options
        };
        this.captchaId = null;
        this.modal = null;
        this.resolveCallback = null;
    }

    /**
     * 显示验证码模态框
     */
    async showBox() {
        return new Promise((resolve) => {
            this.resolveCallback = resolve;
            this.createModal();
        });
    }

    /**
     * 创建验证码模态框
     */
    createModal() {
        // 移除已存在的模态框
        const existingModal = document.querySelector('#local-captcha-modal');
        if (existingModal) {
            existingModal.remove();
        }

        // 创建遮罩层
        const overlay = document.createElement('div');
        overlay.id = 'local-captcha-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            z-index: 9999;
            display: flex;
            justify-content: center;
            align-items: center;
        `;

        // 创建模态框
        this.modal = document.createElement('div');
        this.modal.id = 'local-captcha-modal';
        this.modal.style.cssText = `
            background: white;
            border-radius: 8px;
            padding: 20px;
            width: 300px;
            max-width: 90vw;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            position: relative;
        `;

        // 创建标题
        const title = document.createElement('h3');
        title.textContent = '请输入验证码';
        title.style.cssText = `
            margin: 0 0 15px 0;
            color: #333;
            font-size: 16px;
        `;

        // 创建验证码图片容器
        const imageContainer = document.createElement('div');
        imageContainer.id = 'captcha-image-container';
        imageContainer.style.cssText = `
            text-align: center;
            margin-bottom: 15px;
        `;

        // 创建验证码图片
        const captchaImg = document.createElement('img');
        captchaImg.id = 'captcha-image';
        captchaImg.style.cssText = `
            width: 120px;
            height: 40px;
            border: 1px solid #ddd;
            border-radius: 4px;
            cursor: pointer;
        `;
        captchaImg.alt = '验证码';

        // 点击图片刷新验证码
        captchaImg.addEventListener('click', () => {
            this.refreshCaptcha();
        });

        // 创建刷新图标
        const refreshIcon = document.createElement('span');
        refreshIcon.innerHTML = '🔄';
        refreshIcon.style.cssText = `
            margin-left: 10px;
            cursor: pointer;
            font-size: 16px;
        `;
        refreshIcon.title = '刷新验证码';
        refreshIcon.addEventListener('click', () => {
            this.refreshCaptcha();
        });

        // 创建验证码输入框
        const input = document.createElement('input');
        input.type = 'text';
        input.id = 'captcha-input';
        input.placeholder = '请输入验证码';
        input.maxLength = 4;
        input.style.cssText = `
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
            margin-bottom: 10px;
            text-transform: uppercase;
        `;

        // 创建按钮容器
        const buttonContainer = document.createElement('div');
        buttonContainer.style.cssText = `
            display: flex;
            gap: 10px;
        `;

        // 创建取消按钮
        const cancelButton = document.createElement('button');
        cancelButton.type = 'button';
        cancelButton.textContent = '取消';
        cancelButton.style.cssText = `
            flex: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            background: #f5f5f5;
            cursor: pointer;
        `;
        cancelButton.addEventListener('click', () => {
            this.closeModal();
            if (this.resolveCallback) {
                this.resolveCallback({ status: 'closed' });
            }
        });

        // 创建确认按钮
        const confirmButton = document.createElement('button');
        confirmButton.type = 'button';
        confirmButton.textContent = '确认';
        confirmButton.style.cssText = `
            flex: 1;
            padding: 10px;
            border: none;
            border-radius: 4px;
            background: #007bff;
            color: white;
            cursor: pointer;
        `;
        confirmButton.addEventListener('click', () => {
            this.verifyCaptcha();
        });

        // 组装模态框
        imageContainer.appendChild(captchaImg);
        imageContainer.appendChild(refreshIcon);

        buttonContainer.appendChild(cancelButton);
        buttonContainer.appendChild(confirmButton);

        this.modal.appendChild(title);
        this.modal.appendChild(imageContainer);
        this.modal.appendChild(input);
        this.modal.appendChild(buttonContainer);

        // 绑定回车键确认
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.verifyCaptcha();
            }
        });

        overlay.appendChild(this.modal);

        // 添加到页面
        document.body.appendChild(overlay);

        // 生成并显示验证码
        this.generateCaptcha();
    }

    /**
     * 生成验证码
     */
    async generateCaptcha() {
        try {
            const response = await fetch('/accounts/captcha/generate/');
            const data = await response.json();
            
            if (data.captcha_id) {
                this.captchaId = data.captcha_id;
                
                // 设置验证码图片
                const captchaImg = document.getElementById('captcha-image');
                if (captchaImg) {
                    captchaImg.src = `/accounts/captcha/image/${this.captchaId}/?t=${Date.now()}`;
                }
            }
        } catch (error) {
            console.error('生成验证码失败:', error);
            alert('验证码生成失败，请稍后重试');
        }
    }

    /**
     * 刷新验证码
     */
    async refreshCaptcha() {
        await this.generateCaptcha();
        
        // 清空输入框
        const input = document.getElementById('captcha-input');
        if (input) {
            input.value = '';
        }
    }

    /**
     * 验证验证码
     */
    async verifyCaptcha() {
        const input = document.getElementById('captcha-input');
        const userInput = input ? input.value.trim() : '';

        if (!userInput) {
            alert('请输入验证码');
            return;
        }

        if (!this.captchaId) {
            alert('验证码已过期，请重新获取');
            await this.generateCaptcha();
            return;
        }

        // 直接返回结果，不调用后端验证接口
        // 验证码的最终验证将在表单提交时由后端完成
        this.closeModal();
        
        // 返回模拟的Geetest v4数据格式
        const result = {
            status: 'success',
            lot_number: this.captchaId, // 使用captchaId作为lot_number
            captcha_output: userInput,  // 用户输入作为captcha_output
            pass_token: 'local_captcha_pass_token',
            gen_time: Date.now().toString(),
            captcha_id: this.captchaId
        };

        if (this.resolveCallback) {
            this.resolveCallback(result);
        }
    }

    /**
     * 关闭模态框
     */
    closeModal() {
        const overlay = document.querySelector('#local-captcha-overlay');
        if (overlay) {
            overlay.remove();
        }
        this.modal = null;
    }

    /**
     * 获取CSRF令牌
     */
    getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
               document.querySelector('[name=csrf-token]')?.value ||
               document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1];
    }

    /**
     * 初始化并返回实例
     */
    static initGeetest(config, callback) {
        const adapter = new LocalCaptchaAdapter(config);
        callback(adapter);
    }
}

// 注册到全局作用域，以便与现有的Geetest代码兼容
window.initGeetest4 = LocalCaptchaAdapter.initGeetest;

// 倒计时功能
let countdownTimer = null;

// 开始倒计时
function startCountdown(button, initialText = null) {
    if (countdownTimer) {
        clearInterval(countdownTimer); // 清除任何现有的倒计时
    }
    
    let count = 60;
    const originalText = initialText || button.textContent || button.innerText;
    button.disabled = true;
    
    // 更新按钮文本显示倒计时
    button.textContent = `${originalText} (${count}s)`;
    
    countdownTimer = setInterval(() => {
        count--;
        button.textContent = `${originalText} (${count}s)`;
        
        if (count <= 0) {
            clearInterval(countdownTimer);
            button.disabled = false;
            button.textContent = originalText;
            countdownTimer = null;
        }
    }, 1000);
}

// 在DOM准备好后，处理本地验证码触发按钮
document.addEventListener('DOMContentLoaded', function() {
    // 检查是否使用本地验证码
    const captchaProvider = window.CAPTCHA_PROVIDER;
    
    // 只有当明确使用本地验证码时才处理
    if (captchaProvider === 'local') {
        // 如果使用本地验证码，移除email_code.js可能添加的事件监听器
        // 通过克隆并替换按钮来清除所有事件监听器
        const emailCodeButtons = document.querySelectorAll('#get-email-code[data-local-captcha-trigger]');
        emailCodeButtons.forEach(button => {
            const newButton = button.cloneNode(true);
            button.parentNode.replaceChild(newButton, button);
        });
        
        // 现在为本地验证码触发按钮添加事件监听器
        document.querySelectorAll('[data-local-captcha-trigger]').forEach(button => {
            // 根据按钮的类型执行不同的操作
            if (button.id === 'get-email-code') {
                // 如果是获取邮箱验证码的按钮，需要先检查邮箱
                button.addEventListener('click', async function(e) {
                    e.preventDefault();
                    e.stopPropagation(); // 阻止事件冒泡，防止email_code.js也处理此事件
                    
                    // 检查是否正在进行倒计时
                    if (this.disabled) {
                        return; // 如果按钮被禁用（倒计时中），则不执行任何操作
                    }
                    
                    // 首先检查邮箱是否已填写
                    const emailField = document.querySelector('input[type="email"]');
                    if (!emailField || !emailField.value) {
                        alert('请先填写邮箱地址');
                        emailField?.focus(); // 聚焦到邮箱输入框
                        return; // 退出函数，不再继续执行
                    }
                    
                    const adapter = new LocalCaptchaAdapter({
                        product: 'popup'
                    });
                    
                    const result = await adapter.showBox();
                    
                    if (result && result.status === 'success') {
                        // 将结果存储到隐藏字段中（模拟Geetest字段）
                        document.getElementById('lot_number_login')?.setAttribute('value', result.lot_number);
                        document.getElementById('captcha_output_login')?.setAttribute('value', result.captcha_output);
                        document.getElementById('pass_token_login')?.setAttribute('value', result.pass_token);
                        document.getElementById('gen_time_login')?.setAttribute('value', result.gen_time);
                        
                        document.getElementById('lot_number_reg')?.setAttribute('value', result.lot_number);
                        document.getElementById('captcha_output_reg')?.setAttribute('value', result.captcha_output);
                        document.getElementById('pass_token_reg')?.setAttribute('value', result.pass_token);
                        document.getElementById('gen_time_reg')?.setAttribute('value', result.gen_time);
                        
                        document.getElementById('lot_number_forgot')?.setAttribute('value', result.lot_number);
                        document.getElementById('captcha_output_forgot')?.setAttribute('value', result.captcha_output);
                        document.getElementById('pass_token_forgot')?.setAttribute('value', result.pass_token);
                        document.getElementById('gen_time_forgot')?.setAttribute('value', result.gen_time);
                        
                        // 发送邮箱验证码请求
                        sendEmailCodeRequest(this); // 传递按钮引用以启用倒计时
                    }
                });
            } else {
                // 如果是其他类型的按钮（如提交按钮），直接执行相应操作
                button.addEventListener('click', async function(e) {
                    e.preventDefault();
                    e.stopPropagation(); // 阻止事件冒泡
                    
                    const adapter = new LocalCaptchaAdapter({
                        product: 'popup'
                    });
                    
                    const result = await adapter.showBox();
                    
                    if (result && result.status === 'success') {
                        // 将结果存储到隐藏字段中（模拟Geetest字段）
                        document.getElementById('lot_number_login')?.setAttribute('value', result.lot_number);
                        document.getElementById('captcha_output_login')?.setAttribute('value', result.captcha_output);
                        document.getElementById('pass_token_login')?.setAttribute('value', result.pass_token);
                        document.getElementById('gen_time_login')?.setAttribute('value', result.gen_time);
                        
                        document.getElementById('lot_number_reg')?.setAttribute('value', result.lot_number);
                        document.getElementById('captcha_output_reg')?.setAttribute('value', result.captcha_output);
                        document.getElementById('pass_token_reg')?.setAttribute('value', result.pass_token);
                        document.getElementById('gen_time_reg')?.setAttribute('value', result.gen_time);
                        
                        document.getElementById('lot_number_forgot')?.setAttribute('value', result.lot_number);
                        document.getElementById('captcha_output_forgot')?.setAttribute('value', result.captcha_output);
                        document.getElementById('pass_token_forgot')?.setAttribute('value', result.pass_token);
                        document.getElementById('gen_time_forgot')?.setAttribute('value', result.gen_time);
                        
                        // 触发原始按钮的后续操作
                        if (this.dataset.action === 'get-code') {
                            // 如果是获取邮箱验证码的按钮，现在可以发送请求
                            sendEmailCodeRequest(this); // 传递按钮引用以启用倒计时
                        } else if (this.dataset.action === 'submit') {
                            // 如果是提交按钮，直接提交表单
                            // 找到最近的表单或者页面中的表单
                            let form = this.closest('form');
                            if (!form) {
                                form = document.querySelector('form');
                            }
                            if (form) {
                                // 提交表单
                                form.submit();
                            }
                        }
                    }
                });
            }
        });
    }
    // 对于非本地验证码（如Geetest或Turnstile），不执行任何特殊处理，让原有逻辑处理
});

// 确保只有当使用本地验证码时才处理本地验证码逻辑
// 其他验证码提供商（如Geetest/Turnstile）会由其各自适配器处理

// 辅助函数：发送邮箱验证码请求
function sendEmailCodeRequest(button) {
    // 注意：在这个函数中，邮箱应该已经被检查过了，所以这里不再重复检查
    const emailField = document.querySelector('input[type="email"]');
    // 注意：这里我们假定邮箱已经被检查过了，所以不再显示alert
    
    // 根据当前页面判断是注册还是找回密码
    let endpoint;
    if (window.location.pathname.includes('/register/')) {
        endpoint = '/accounts/email/send-code/';
    } else if (window.location.pathname.includes('/forgot-password/')) {
        endpoint = '/accounts/email/send-forgot-password-code/';
    } else {
        alert('无法确定当前页面类型');
        return;
    }

    // 收集Geetest字段值（即使使用本地验证码也可能需要这些字段）
    const lotNumber = document.getElementById('lot_number_login')?.value || 
                      document.getElementById('lot_number_reg')?.value ||
                      document.getElementById('lot_number_forgot')?.value;
    const captchaOutput = document.getElementById('captcha_output_login')?.value ||
                          document.getElementById('captcha_output_reg')?.value ||
                          document.getElementById('captcha_output_forgot')?.value;
    const passToken = document.getElementById('pass_token_login')?.value ||
                      document.getElementById('pass_token_reg')?.value ||
                      document.getElementById('pass_token_forgot')?.value;
    const genTime = document.getElementById('gen_time_login')?.value ||
                    document.getElementById('gen_time_reg')?.value ||
                    document.getElementById('gen_time_forgot')?.value;

    const formData = new FormData();
    formData.append('email', emailField.value);
    
    // 添加可能需要的验证字段
    if (lotNumber) formData.append('lot_number', lotNumber);
    if (captchaOutput) formData.append('captcha_output', captchaOutput);
    if (passToken) formData.append('pass_token', passToken);
    if (genTime) formData.append('gen_time', genTime);

    fetch(endpoint, {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            alert('验证码已发送到您的邮箱');
            // 开始倒计时
            if (button) {
                startCountdown(button, '获取验证码');
            }
        } else {
            alert(data.message || '发送验证码失败');
            // 即使发送失败，也应该恢复按钮状态
            if (button && countdownTimer) {
                clearInterval(countdownTimer);
                countdownTimer = null;
                button.disabled = false;
                const originalText = '获取验证码';
                button.textContent = originalText;
            }
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('发送验证码时发生错误');
        // 发生错误时也要恢复按钮状态
        if (button && countdownTimer) {
            clearInterval(countdownTimer);
            countdownTimer = null;
            button.disabled = false;
            const originalText = '获取验证码';
            button.textContent = originalText;
        }
    });
}