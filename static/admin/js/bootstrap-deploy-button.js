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
        } else {
            setTimeout(init, 100);
        }
    }
    
    function setupDeployButton() {
        $(document).ready(function() {
            // 添加部署按钮到页面顶部工具栏
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
                                    <a href="https://github.com/trustedinster/ZASCAHB/releases/latest" 
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
        
        $.ajax({
            url: window.location.pathname.replace(/\/change\/?$/, '') + '/generate-deploy-command/',
            method: 'GET',
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
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