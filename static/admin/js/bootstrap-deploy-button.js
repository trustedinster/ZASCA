// 三步骤部署流程模态框
var deployFlowModule = (function() {
    var $;
    var currentStep = 1;
    var deployData = {};
    
    // 等待django.jQuery可用
    function init() {
        if (typeof django !== 'undefined' && django.jQuery) {
            $ = django.jQuery;
            setupDeployButton();
            setupQuickDeployButton();
        } else {
            setTimeout(init, 100);
        }
    }
    
    function setupDeployButton() {
        $(document).ready(function() {
            // 添加部署按钮到页面顶部工具栏（修改页面）
            var header = $('.object-tools');
            if (header.length > 0) {
                var heading = $('#content h1').text();
                if (heading.includes('主机') || heading.includes('Host')) {
                    var objectIdMatch = window.location.pathname.match(/\/(\d+)\/change\//);
                    if (objectIdMatch && objectIdMatch[1]) {
                        var hostId = objectIdMatch[1];
                        var hostName = $('input[name="name"]').val() || 'Unknown';
                        
                        var deployButtonHtml = `
                            <li>
                                <a href="#" class="button" id="start-deploy-flow-btn" 
                                   data-host-id="${hostId}" 
                                   onclick="startDeployFlow(${hostId}, '${hostName}')">
                                    开始部署
                                </a>
                            </li>
                        `;
                        
                        header.prepend(deployButtonHtml);
                    }
                }
            }
            
            // 创建三步骤模态框
            createDeployModal();
            bindModalEvents();
        });
    }
    
    function setupQuickDeployButton() {
        $(document).ready(function() {
            // 检查是否在主机列表页面
            var heading = $('#content h1').text();
            var isHostListPage = heading.includes('选择要修改的主机') || 
                                  heading.includes('Select host to change') ||
                                  window.location.pathname.includes('/admin/hosts/host/');
            
            if (isHostListPage && !window.location.pathname.includes('/change/')) {
                // 在列表页面添加一键注册按钮到右上角
                var objectTools = $('.object-tools');
                if (objectTools.length > 0) {
                    // 添加验证主机按钮
                    var verifyButton = `
                        <li>
                            <a href="#" class="button" id="verify-host-btn" onclick="showVerifyDialog()">
                                验证主机
                            </a>
                        </li>
                    `;
                    objectTools.prepend(verifyButton);
                    
                    // 添加一键注册按钮
                    var quickRegisterButton = `
                        <li>
                            <a href="#" class="button" id="quick-register-btn" onclick="showQuickRegisterDialog()">
                                一键注册主机
                            </a>
                        </li>
                    `;
                    objectTools.prepend(quickRegisterButton);
                }
                
                // 创建快速注册对话框
                createQuickRegisterDialog();
                
                // 创建验证对话框
                createVerifyDialog();
            }
        });
    }
    
    function createVerifyDialog() {
        var dialogHtml = `
            <div id="verify-host-dialog" style="display: none;">
                <div id="verify-host-dialog-content">
                    <div id="verify-host-dialog-header">
                        <h3>验证主机</h3>
                        <button id="close-verify-host-dialog">&times;</button>
                    </div>
                    <div id="verify-host-dialog-body">
                        <div class="verify-section">
                            <h4>待验证主机列表</h4>
                            <div id="pending-hosts-list">
                                <p>正在加载...</p>
                            </div>
                        </div>
                        <div class="verify-form" id="verify-form" style="display: none;">
                            <h4>输入TOTP验证码</h4>
                            <p>主机: <strong id="verify-hostname"></strong></p>
                            <div class="form-group">
                                <label for="totp-code">TOTP验证码:</label>
                                <input type="text" id="totp-code" maxlength="6" placeholder="请输入6位数字验证码" />
                            </div>
                            <button class="button default" id="submit-verify-btn">验证</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        $('body').append(dialogHtml);
        
        // 绑定关闭事件
        $('#close-verify-host-dialog').click(function() {
            $('#verify-host-dialog').hide();
        });
        
        $('#verify-host-dialog').click(function(e) {
            if (e.target === this) {
                $(this).hide();
            }
        });
        
        // 绑定验证按钮事件
        $(document).on('click', '#submit-verify-btn', function() {
            submitVerification();
        });
        
        // TOTP输入框自动格式化
        $(document).on('input', '#totp-code', function() {
            this.value = this.value.replace(/[^0-9]/g, '').substring(0, 6);
        });
    }
    
    window.showVerifyDialog = function() {
        loadPendingHosts();
        $('#verify-host-dialog').show();
    };
    
    function loadPendingHosts() {
        var baseUrl = window.location.origin;
        $.ajax({
            url: baseUrl + '/bootstrap/api/pending-hosts/',
            method: 'GET',
            success: function(response) {
                if (response.success) {
                    displayPendingHosts(response.data.hosts);
                } else {
                    $('#pending-hosts-list').html('<p>加载失败: ' + response.error + '</p>');
                }
            },
            error: function() {
                $('#pending-hosts-list').html('<p>加载失败</p>');
            }
        });
    }
    
    function displayPendingHosts(hosts) {
        if (hosts.length === 0) {
            $('#pending-hosts-list').html('<p>当前没有待验证的主机</p>');
            return;
        }
        
        var html = '<div class="pending-hosts-grid">';
        hosts.forEach(function(host) {
            html += `
                <div class="pending-host-item">
                    <div class="host-info" onclick="selectHostForVerify('${host.token}', '${host.hostname}')">
                        <strong>${host.hostname}</strong>
                        <span class="host-time">${host.created_at}</span>
                    </div>
                    <div class="host-actions">
                        <button class="verify-btn-small" onclick="selectHostForVerify('${host.token}', '${host.hostname}')">验证</button>
                        <button class="revoke-btn-small" onclick="revokePendingHost('${host.token}', '${host.hostname}')">吊销</button>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        
        $('#pending-hosts-list').html(html);
    }
    
    window.selectHostForVerify = function(token, hostname) {
        $('#verify-hostname').text(hostname);
        $('#verify-form').data('token', token);
        $('#verify-form').show();
        $('#totp-code').val('').focus();
    };
    
    function submitVerification() {
        var token = $('#verify-form').data('token');
        var totpCode = $('#totp-code').val();
        
        if (!totpCode || totpCode.length !== 6) {
            alert('请输入6位数字验证码');
            return;
        }
        
        var baseUrl = window.location.origin;
        $.ajax({
            url: baseUrl + '/bootstrap/api/verify-pairing-code/',
            method: 'POST',
            data: JSON.stringify({
                token: token,
                pairing_code: totpCode
            }),
            contentType: 'application/json',
            success: function(response) {
                if (response.success) {
                    alert('验证成功！主机已激活');
                    $('#verify-host-dialog').hide();
                    location.reload();
                } else {
                    alert('验证失败: ' + response.error);
                }
            },
            error: function() {
                alert('验证请求失败');
            }
        });
    }
    
    window.revokePendingHost = function(token, hostname) {
        if (!confirm('确定要吊销主机 "' + hostname + '" 吗？\n\n吊销后将删除该主机记录及其令牌，此操作不可恢复。')) {
            return;
        }
        
        var baseUrl = window.location.origin;
        $.ajax({
            url: baseUrl + '/bootstrap/api/revoke-pending-host/',
            method: 'POST',
            data: JSON.stringify({
                token: token
            }),
            contentType: 'application/json',
            success: function(response) {
                if (response.success) {
                    alert('吊销成功！\n' + response.message);
                    loadPendingHosts();
                    $('#verify-form').hide();
                } else {
                    alert('吊销失败: ' + response.error);
                }
            },
            error: function(xhr) {
                var errorMsg = '吊销请求失败';
                if (xhr.responseJSON && xhr.responseJSON.error) {
                    errorMsg = xhr.responseJSON.error;
                }
                alert(errorMsg);
            }
        });
    };
    
    function createQuickRegisterDialog() {
        var dialogHtml = `
            <div id="quick-register-dialog" style="display: none;">
                <div id="quick-register-dialog-content">
                    <div id="quick-register-dialog-header">
                        <h3>一键注册主机</h3>
                        <button id="close-quick-register-dialog">&times;</button>
                    </div>
                    <div id="quick-register-dialog-body">
                        <div class="register-instructions">
                            <h4>使用说明</h4>
                            <p>在目标Windows主机上以管理员身份运行PowerShell，然后执行以下命令：</p>
                        </div>
                        <div class="command-section">
                            <div id="register-command-display" class="command-display"></div>
                            <button class="copy-btn" id="copy-register-command-btn">复制命令</button>
                        </div>
                        <div class="register-info">
                            <p><strong>命令说明：</strong></p>
                            <ul>
                                <li>自动下载并运行2c2a主机初始化程序</li>
                                <li>自动收集主机信息并注册到系统</li>
                                <li>完成后会显示配对码，请在下方输入完成验证</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        $('body').append(dialogHtml);
        
        // 绑定关闭事件
        $('#close-quick-register-dialog').click(function() {
            $('#quick-register-dialog').hide();
        });
        
        $('#quick-register-dialog').click(function(e) {
            if (e.target === this) {
                $(this).hide();
            }
        });
        
        // 绑定复制按钮事件
        $(document).on('click', '#copy-register-command-btn', function() {
            var commandText = $('#register-command-display').text();
            copyToClipboard(commandText, $(this));
        });
    }
    
    window.showQuickRegisterDialog = function() {
        // 生成一键注册命令
        generateRegisterCommand();
        $('#quick-register-dialog').show();
    };
    
    function generateRegisterCommand() {
        // 获取当前站点URL
        var baseUrl = window.location.origin;
        
        // 生成极简的一行命令
        var psCommand = `iex (irm ${baseUrl}/bootstrap/api/auto-register/?hostname=$env:COMPUTERNAME).data.script`;
        
        $('#register-command-display').text(psCommand);
    }
    
    function createDeployModal() {
        var modalHtml = `
            <div id="deploy-flow-modal" style="display: none;">
                <div id="deploy-flow-modal-content">
                    <div id="deploy-flow-header">
                        <h3 id="deploy-flow-title">H端部署流程</h3>
                        <button id="close-deploy-flow-modal">&times;</button>
                    </div>
                    
                    <!-- 步骤指示器 -->
                    <div id="step-indicator">
                        <div class="step-item active" data-step="1">
                            <div class="step-number">1</div>
                            <div class="step-text">下载客户端</div>
                        </div>
                        <div class="step-item" data-step="2">
                            <div class="step-number">2</div>
                            <div class="step-text">执行命令</div>
                        </div>
                        <div class="step-item" data-step="3">
                            <div class="step-number">3</div>
                            <div class="step-text">输入配对码</div>
                        </div>
                    </div>
                    
                    <!-- 步骤内容 -->
                    <div id="step-content">
                        <!-- 步骤1：下载客户端 -->
                        <div class="step-panel active" id="step-panel-1">
                            <h4>第一步：下载一键部署程序并导入主机</h4>
                            <div class="step-instructions">
                                <p>请下载最新版本的H端部署客户端：</p>
                                <div class="download-section">
                                    <a href="https://github.com/2c2a/2c2aHB/releases/latest" 
                                       target="_blank" 
                                       class="download-btn" 
                                       id="download-client-btn">
                                        下载客户端
                                    </a>
                                    <span class="download-hint">点击下载最新版本</span>
                                </div>
                                <p class="note">下载完成后，请将客户端放置在目标主机的任意目录中</p>
                            </div>
                            <div class="step-actions">
                                <button class="next-btn" onclick="nextStep()">下一步</button>
                            </div>
                        </div>
                        
                        <!-- 步骤2：执行命令 -->
                        <div class="step-panel" id="step-panel-2">
                            <h4>第二步：在主机当前目录打开CMD（或Powershell）执行</h4>
                            <div class="step-instructions">
                                <p>在目标主机上打开命令行工具，执行以下部署命令：</p>
                                <div class="command-section">
                                    <div id="deploy-command-display" class="command-display"></div>
                                    <button class="copy-btn" id="copy-command-btn">复制命令</button>
                                </div>
                                <div class="command-info">
                                    <p><strong>说明：</strong></p>
                                    <ul>
                                        <li>此命令将初始化H端并与服务器建立连接</li>
                                        <li>执行过程中请勿关闭命令行窗口</li>
                                        <li>等待命令执行完成后再进行下一步</li>
                                    </ul>
                                </div>
                            </div>
                            <div class="step-actions">
                                <button class="prev-btn" onclick="prevStep()">上一步</button>
                                <button class="next-btn" onclick="nextStep()">下一步</button>
                            </div>
                        </div>
                        
                        <!-- 步骤3：输入配对码 -->
                        <div class="step-panel" id="step-panel-3">
                            <h4>第三步：输入下方的配对码</h4>
                            <div class="step-instructions">
                                <p>在H端执行命令后，请输入以下配对码完成验证：</p>
                                <div class="pairing-section">
                                    <div id="pairing-code-display" class="pairing-code"></div>
                                    <div class="pairing-info">
                                        <p>配对码有效期：<span id="pairing-expiry"></span></p>
                                        <p class="warning">请确保在有效期内完成配对</p>
                                    </div>
                                </div>
                                <div class="status-section">
                                    <div id="pairing-status">等待配对...</div>
                                </div>
                            </div>
                            <div class="step-actions">
                                <button class="prev-btn" onclick="prevStep()">上一步</button>
                                <button class="finish-btn" onclick="finishDeploy()">完成部署</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        $('body').append(modalHtml);
    }
    
    function bindModalEvents() {
        // 关闭按钮事件
        $('#close-deploy-flow-modal').click(function() {
            closeDeployFlow();
        });
        
        // 点击背景关闭
        $('#deploy-flow-modal').click(function(e) {
            if (e.target === this) {
                closeDeployFlow();
            }
        });
        
        // 复制命令按钮事件
        $(document).on('click', '#copy-command-btn', function() {
            var commandText = $('#deploy-command-display').text();
            copyToClipboard(commandText, $(this));
        });
        
        // ESC键关闭
        $(document).keydown(function(e) {
            if (e.keyCode === 27 && $('#deploy-flow-modal').is(':visible')) {
                closeDeployFlow();
            }
        });
    }
    
    function copyToClipboard(text, button) {
        navigator.clipboard.writeText(text).then(function() {
            var originalText = button.text();
            button.text('已复制!').addClass('copied');
            setTimeout(function() {
                button.text(originalText).removeClass('copied');
            }, 2000);
        }).catch(function(err) {
            console.error('复制失败: ', err);
            // 备选方案
            fallbackCopyTextToClipboard(text, button);
        });
    }
    
    function fallbackCopyTextToClipboard(text, button) {
        var textArea = document.createElement("textarea");
        textArea.value = text;
        textArea.style.cssText = 'position: fixed; top: -1000px; left: -1000px; opacity: 0;';
        
        document.body.appendChild(textArea);
        textArea.select();
        
        try {
            var successful = document.execCommand('copy');
            if (successful) {
                var originalText = button.text();
                button.text('已复制!').addClass('copied');
                setTimeout(function() {
                    button.text(originalText).removeClass('copied');
                }, 2000);
            } else {
                alert('复制失败，请手动选择文本并复制');
            }
        } catch (err) {
            console.error('复制命令失败: ', err);
            alert('复制失败，请手动选择文本并复制');
        }
        
        document.body.removeChild(textArea);
    }
    
    // 全局函数
    window.startDeployFlow = function(hostId, hostName) {
        if (!$) {
            if (typeof django !== 'undefined' && django.jQuery) {
                $ = django.jQuery;
            } else {
                alert('页面加载中，请稍后重试');
                return;
            }
        }
        
        // 重置状态
        currentStep = 1;
        deployData = {};
        updateStepIndicator(1);
        showStepPanel(1);
        
        // 显示模态框
        $('#deploy-flow-modal').show();
        
        // 获取部署数据
        fetchDeployData(hostId);
    };
    
    window.nextStep = function() {
        if (currentStep < 3) {
            currentStep++;
            updateStepIndicator(currentStep);
            showStepPanel(currentStep);
        }
    };
    
    window.prevStep = function() {
        if (currentStep > 1) {
            currentStep--;
            updateStepIndicator(currentStep);
            showStepPanel(currentStep);
        }
    };
    
    window.finishDeploy = function() {
        closeDeployFlow();
        alert('部署流程已完成！');
    };
    
    function closeDeployFlow() {
        $('#deploy-flow-modal').hide();
        currentStep = 1;
        deployData = {};
        updateStepIndicator(1);
        showStepPanel(1);
    }
    
    function fetchDeployData(hostId) {
        // 显示加载状态
        $('#deploy-command-display').html('<div class="loading">正在生成部署信息...</div>');
        $('#pairing-code-display').html('<div class="loading">正在生成配对码...</div>');
        
        // 构建API URL - 支持列表页面和修改页面
        var apiUrl;
        if (window.location.pathname.includes('/change/')) {
            // 修改页面：使用相对路径
            apiUrl = window.location.pathname.replace(/\/change\/?$/, '') + '/generate-deploy-command/';
        } else {
            // 列表页面：使用绝对路径
            apiUrl = '/admin/hosts/host/quick-deploy/' + hostId + '/';
        }
        
        $.ajax({
            url: apiUrl,
            method: 'GET',
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                               document.querySelector('input[name="csrfmiddlewaretoken"]')?.value || ''
            },
            success: function(response) {
                if (response.success) {
                    deployData = response;
                    updateDeployInfo();
                } else {
                    showError('生成部署信息失败: ' + response.error);
                }
            },
            error: function(xhr) {
                var errorMsg = xhr.responseJSON ? xhr.responseJSON.error : '请求失败';
                showError('获取部署信息失败: ' + errorMsg);
            }
        });
    }
    
    function updateDeployInfo() {
        // 更新部署命令
        $('#deploy-command-display').text(deployData.deploy_command);
        
        // 更新配对码
        $('#pairing-code-display').text(deployData.pairing_code);
        
        // 更新配对码过期时间
        var expiryTime = new Date(deployData.pairing_code_expiry);
        $('#pairing-expiry').text(expiryTime.toLocaleString('zh-CN'));
        
        // 启动配对状态检查
        startPairingCheck();
    }
    
    function showError(message) {
        $('#deploy-command-display').html(`<span class="error">${message}</span>`);
        $('#pairing-code-display').html(`<span class="error">${message}</span>`);
    }
    
    function updateStepIndicator(step) {
        $('.step-item').removeClass('active completed');
        $('.step-item').each(function() {
            var itemStep = parseInt($(this).data('step'));
            if (itemStep < step) {
                $(this).addClass('completed');
            } else if (itemStep === step) {
                $(this).addClass('active');
            }
        });
    }
    
    function showStepPanel(step) {
        $('.step-panel').removeClass('active');
        $('#step-panel-' + step).addClass('active');
    }
    
    function startPairingCheck() {
        // 每5秒检查一次配对状态
        setInterval(function() {
            if ($('#deploy-flow-modal').is(':visible') && currentStep === 3) {
                checkPairingStatus();
            }
        }, 5000);
    }
    
    function checkPairingStatus() {
        // 这里可以添加实际的配对状态检查逻辑
        // 目前只是示例
        var statusElement = $('#pairing-status');
        var currentTime = new Date();
        var expiryTime = new Date(deployData.pairing_code_expiry);
        
        if (currentTime > expiryTime) {
            statusElement.html('<span class="error">配对码已过期，请重新开始部署流程</span>');
        } else {
            // 模拟检查状态
            var timeLeft = Math.floor((expiryTime - currentTime) / 1000 / 60);
            statusElement.text(`等待配对... (${timeLeft}分钟有效)`);
        }
    }
    
    // 初始化模块
    init();
})();