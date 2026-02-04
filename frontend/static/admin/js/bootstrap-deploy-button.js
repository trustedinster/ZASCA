// 部署命令按钮功能
var deployCommandModule = (function() {
    var $;
    
    // 等待django.jQuery可用
    function init() {
        if (typeof django !== 'undefined' && django.jQuery) {
            $ = django.jQuery;
            setupDeployButton();
        } else {
            setTimeout(init, 100); // 等待100毫秒后重试
        }
    }
    
    function setupDeployButton() {
        $(document).ready(function() {
            // 添加部署命令按钮到页面顶部工具栏
            var header = $('.object-tools');
            if (header.length > 0) {
                // 检查当前页面是否为主机编辑页面
                var heading = $('#content h1').text();
                if (heading.includes('主机') || heading.includes('Host')) {
                    var objectIdMatch = window.location.pathname.match(/\/(\d+)\/change\//);
                    if (objectIdMatch && objectIdMatch[1]) {
                        var hostId = objectIdMatch[1];
                        var hostName = $('input[name="name"]').val() || 'Unknown';
                        
                        var deployButtonHtml = `
                            <li>
                                <a href="#" class="button" id="get-deploy-command-btn" 
                                   data-host-id="${hostId}" 
                                   onclick="showDeployCommand(${hostId}, '${hostName}')">
                                    获取部署命令
                                </a>
                            </li>
                        `;
                        
                        header.prepend(deployButtonHtml);
                    }
                }
            }
            
            // 创建模态框HTML
            var modalHtml = `
                <div id="deploy-command-modal">
                    <div id="deploy-command-modal-content">
                        <div id="deploy-command-modal-header">
                            <h3 id="deploy-command-modal-title">H端部署命令</h3>
                            <button id="close-deploy-command-modal">&times;</button>
                        </div>
                        <div id="deploy-command-body">
                            <p>以下是H端初始化所需的部署命令：</p>
                            <div id="deploy-command-output"></div>
                            <div class="deploy-command-actions">
                                <button class="copy-deploy-command-btn" id="copy-deploy-command-btn">
                                    复制命令
                                </button>
                            </div>
                            <div id="deploy-command-info"></div>
                        </div>
                    </div>
                </div>
            `;
            
            $('body').append(modalHtml);
            
            // 绑定关闭按钮事件
            $('#close-deploy-command-modal').click(function() {
                $('#deploy-command-modal').hide();
            });
            
            // 点击模态框背景关闭
            $('#deploy-command-modal').click(function(e) {
                if (e.target === this) {
                    $(this).hide();
                }
            });
            
            // 绑定复制按钮事件
            $(document).on('click', '#copy-deploy-command-btn', function() {
                var commandText = $('#deploy-command-output').text();
                navigator.clipboard.writeText(commandText).then(function() {
                    var btn = $('#copy-deploy-command-btn');
                    btn.text('已复制!').addClass('copied');
                    setTimeout(function() {
                        btn.text('复制命令').removeClass('copied');
                    }, 2000);
                }).catch(function(err) {
                    console.error('复制失败: ', err);
                    alert('复制失败，请手动复制命令');
                });
            });
        });
    }
    
    // 定义全局函数
    window.showDeployCommand = function(hostId, hostName) {
        // 确保jQuery已加载
        if (!$) {
            if (typeof django !== 'undefined' && django.jQuery) {
                $ = django.jQuery;
            } else {
                alert('jQuery未加载完成');
                return;
            }
        }
        
        // 显示加载状态
        $('#deploy-command-output').html('正在生成部署命令...');
        $('#deploy-command-modal').show();
        
        // 发送AJAX请求获取部署命令 - 使用正确的URL模式
        $.ajax({
            url: window.location.pathname.replace(/\/change\/?$/, '') + '/generate-deploy-command/',
            method: 'GET',
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            success: function(response) {
                if (response.success) {
                    var commandText = response.deploy_command;
                    var expiresAt = new Date(response.expires_at).toLocaleString('zh-CN');
                    
                    $('#deploy-command-output').text(commandText);
                    $('#deploy-command-info').html(`
                        <p><strong>说明:</strong></p>
                        <ul>
                            <li>此命令用于在H端执行一次性初始化</li>
                            <li>令牌将在 ${expiresAt} 过期</li>
                            <li>请尽快使用此命令完成H端初始化</li>
                        </ul>
                    `);
                } else {
                    $('#deploy-command-output').html('<span style="color: red;">生成部署命令失败: ' + response.error + '</span>');
                }
            },
            error: function(xhr, status, error) {
                var errorMsg = xhr.responseJSON ? xhr.responseJSON.error : '请求失败';
                $('#deploy-command-output').html('<span style="color: red;">生成部署命令失败: ' + errorMsg + '</span>');
            }
        });
    };
    
    // 初始化模块
    init();
})();