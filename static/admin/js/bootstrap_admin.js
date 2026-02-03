/**
 * Bootstrap Admin前端功能 - 配对码认证版本
 */

document.addEventListener('DOMContentLoaded', function() {
    // 初始化所有功能
    initCopyButtons();
    initRefreshPairingCode();
    initAutoRefresh();
});

/**
 * 初始化复制按钮功能
 */
function initCopyButtons() {
    // 为复制按钮添加点击事件
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('copy-btn')) {
            copyToClipboard(e.target);
        }
    });
}

/**
 * 复制到剪贴板功能
 */
function copyToClipboard(button) {
    const value = button.getAttribute('data-value');
    if (!value) return;
    
    // 创建临时textarea元素
    const textarea = document.createElement('textarea');
    textarea.value = value;
    textarea.style.position = 'fixed';
    textarea.style.left = '-9999px';
    textarea.style.top = '-9999px';
    document.body.appendChild(textarea);
    
    // 选中并复制
    textarea.select();
    textarea.setSelectionRange(0, 99999); // 移动端兼容
    
    try {
        const successful = document.execCommand('copy');
        if (successful) {
            // 显示成功提示
            showNotification('配置信息已复制到剪贴板', 'success');
            // 更改按钮状态
            const originalText = button.textContent;
            button.textContent = '已复制!';
            button.classList.add('btn-success');
            setTimeout(() => {
                button.textContent = originalText;
                button.classList.remove('btn-success');
            }, 2000);
        } else {
            showNotification('复制失败，请手动复制', 'error');
        }
    } catch (err) {
        console.error('复制失败:', err);
        showNotification('复制失败，请手动复制', 'error');
    }
    
    // 清理
    document.body.removeChild(textarea);
}

/**
 * 初始化刷新配对码功能
 */
function initRefreshPairingCode() {
    window.refreshPairingCode = function(tokenId) {
        if (!confirm('确定要刷新配对码吗？旧的配对码将失效。')) {
            return;
        }
        
        // 发送AJAX请求
        const xhr = new XMLHttpRequest();
        const url = `/admin/bootstrap/initialtoken/${tokenId}/refresh-pairing-code/`;
        
        xhr.open('POST', url, true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.setRequestHeader('X-CSRFToken', getCookie('csrftoken'));
        
        xhr.onreadystatechange = function() {
            if (xhr.readyState === 4) {
                if (xhr.status === 200) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        if (response.success) {
                            showNotification(`配对码已刷新为: ${response.pairing_code}`, 'success');
                            // 刷新页面以显示新配对码
                            setTimeout(() => {
                                location.reload();
                            }, 1500);
                        } else {
                            showNotification(`刷新失败: ${response.error}`, 'error');
                        }
                    } catch (e) {
                        showNotification('响应解析失败', 'error');
                    }
                } else {
                    showNotification(`请求失败: ${xhr.status}`, 'error');
                }
            }
        };
        
        xhr.send(JSON.stringify({}));
    };
}

/**
 * 初始化自动刷新功能
 */
function initAutoRefresh() {
    // 每30秒检查一次配对码状态
    setInterval(function() {
        const pairingCodeElements = document.querySelectorAll('[id^="pairing_code_"]');
        pairingCodeElements.forEach(element => {
            const tokenId = element.id.replace('pairing_code_', '');
            updatePairingCodeStatus(tokenId, element);
        });
        
        // 同时更新倒计时显示
        updateAllCountdowns();
    }, 30000);
}

/**
 * 更新所有倒计时显示
 */
function updateAllCountdowns() {
    document.querySelectorAll('.countdown-timer').forEach(timer => {
        const parent = timer.closest('.pairing-code-display');
        if (parent && parent.dataset.expiry) {
            const expiryTime = parent.dataset.expiry;
            const timeRemaining = formatTimeRemaining(expiryTime);
            timer.textContent = timeRemaining;
        }
    });
}

/**
 * 更新配对码状态
 */
function updatePairingCodeStatus(tokenId, element) {
    // 这里可以实现配对码状态的实时更新
    // 目前作为预留功能
    console.log(`检查令牌 ${tokenId} 的配对码状态`);
}

/**
 * 显示通知消息
 */
function showNotification(message, type = 'info') {
    // 创建通知元素
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show`;
    notification.style.position = 'fixed';
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '9999';
    notification.style.minWidth = '300px';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // 添加到页面
    document.body.appendChild(notification);
    
    // 3秒后自动消失
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 3000);
}

/**
 * 获取Cookie值
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

/**
 * 格式化时间显示
 */
function formatTimeRemaining(expiryTime) {
    const now = new Date();
    const expiry = new Date(expiryTime);
    const diffMs = expiry - now;
    
    if (diffMs <= 0) {
        return '已过期';
    }
    
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
    const diffSeconds = Math.floor((diffMs % (1000 * 60)) / 1000);
    
    if (diffHours > 0) {
        return `${diffHours}小时${diffMinutes}分钟`;
    } else if (diffMinutes > 0) {
        return `${diffMinutes}分钟${diffSeconds}秒`;
    } else {
        return `${diffSeconds}秒`;
    }
}

/**
 * 批量刷新配对码
 */
window.batchRefreshPairingCodes = function(selectedIds) {
    if (!selectedIds || selectedIds.length === 0) {
        showNotification('请选择要刷新的令牌', 'warning');
        return;
    }
    
    if (!confirm(`确定要刷新选中的 ${selectedIds.length} 个令牌的配对码吗？`)) {
        return;
    }
    
    let successCount = 0;
    let failCount = 0;
    
    selectedIds.forEach((tokenId, index) => {
        setTimeout(() => {
            refreshSinglePairingCode(tokenId, () => {
                successCount++;
                if (successCount + failCount === selectedIds.length) {
                    showNotification(`批量刷新完成: 成功${successCount}个，失败${failCount}个`, 
                                   successCount > 0 ? 'success' : 'error');
                    if (successCount > 0) {
                        setTimeout(() => location.reload(), 2000);
                    }
                }
            }, () => {
                failCount++;
                if (successCount + failCount === selectedIds.length) {
                    showNotification(`批量刷新完成: 成功${successCount}个，失败${failCount}个`, 
                                   successCount > 0 ? 'success' : 'error');
                    if (successCount > 0) {
                        setTimeout(() => location.reload(), 2000);
                    }
                }
            });
        }, index * 500); // 间隔500ms发送请求
    });
};

/**
 * 刷新单个配对码
 */
function refreshSinglePairingCode(tokenId, onSuccess, onError) {
    const xhr = new XMLHttpRequest();
    const url = `/admin/bootstrap/initialtoken/${tokenId}/refresh-pairing-code/`;
    
    xhr.open('POST', url, true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.setRequestHeader('X-CSRFToken', getCookie('csrftoken'));
    
    xhr.onreadystatechange = function() {
        if (xhr.readyState === 4) {
            if (xhr.status === 200) {
                try {
                    const response = JSON.parse(xhr.responseText);
                    if (response.success) {
                        onSuccess && onSuccess(response);
                    } else {
                        onError && onError(response);
                    }
                } catch (e) {
                    onError && onError({error: '响应解析失败'});
                }
            } else {
                onError && onError({error: `请求失败: ${xhr.status}`});
            }
        }
    };
    
    xhr.send(JSON.stringify({}));
}

/**
 * 高亮显示即将过期的配对码
 */
function highlightExpiringCodes() {
    const codeElements = document.querySelectorAll('.pairing-code-display');
    codeElements.forEach(element => {
        const expiryAttr = element.getAttribute('data-expiry');
        if (expiryAttr) {
            const expiryTime = new Date(expiryAttr);
            const now = new Date();
            const minutesRemaining = (expiryTime - now) / (1000 * 60);
            
            if (minutesRemaining <= 1) {
                element.style.backgroundColor = '#ffebee';
                element.style.borderColor = '#ffcdd2';
                element.style.color = '#c62828';
            } else if (minutesRemaining <= 3) {
                element.style.backgroundColor = '#fff8e1';
                element.style.borderColor = '#ffecb3';
                element.style.color = '#f57f17';
            }
        }
    });
}

// 页面加载完成后执行高亮
document.addEventListener('DOMContentLoaded', highlightExpiringCodes);