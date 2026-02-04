/**
 * 主机管理相关JavaScript功能
 */

document.addEventListener('DOMContentLoaded', function() {
    // 页面加载完成后初始化主机管理功能
    
    // 如果在主机详情页面，绑定测试连接按钮事件
    const testConnectionBtn = document.getElementById('test-connection-btn');
    if(testConnectionBtn) {
        testConnectionBtn.addEventListener('click', function(e) {
            e.preventDefault();
            const hostId = this.dataset.hostId;
            testHostConnection(hostId);
        });
    }
});

/**
 * 测试主机连接
 */
async function testHostConnection(hostId) {
    try {
        Utils.showLoading();

        const response = await API.post(`/hosts/api/${hostId}/test-connection/`);

        if(response.status === 'success') {
            Utils.showAlert(response.message, 'success');
            // 更新页面上的状态显示
            updateStatusDisplay(response.status_code);
        } else {
            Utils.showAlert(response.message || '测试连接失败', 'danger');
        }
    } catch (error) {
        console.error('Failed to test host connection:', error);
        Utils.showAlert('测试连接请求失败，请稍后重试', 'danger');
    } finally {
        Utils.hideLoading();
    }
}

/**
 * 更新状态显示
 */
function updateStatusDisplay(statusCode) {
    // 更新状态文本
    const statusText = document.querySelector('.host-status');
    if(statusText) {
        // 移除旧的状态类
        statusText.classList.remove('online', 'offline', 'error');
        
        // 添加新状态类
        if(statusCode === 'online') {
            statusText.classList.add('online');
            statusText.textContent = '在线';
        } else if(statusCode === 'offline') {
            statusText.classList.add('offline');
            statusText.textContent = '离线';
        } else if(statusCode === 'error') {
            statusText.classList.add('error');
            statusText.textContent = '错误';
        }
    }
}

// 导出API相关的函数
window.HostsAPI = {
    testConnection: testHostConnection
};
