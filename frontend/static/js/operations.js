/**
 * 操作记录JavaScript功能
 */

// 操作日志管理器
const OperationLog = {
    /**
     * 初始化操作日志
     */
    init() {
        this.bindEvents();
        this.initFilters();
    },

    /**
     * 绑定事件
     */
    bindEvents() {
        // 导出按钮
        const exportBtn = document.getElementById('export-logs-btn');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => {
                this.exportLogs();
            });
        }

        // 筛选表单
        const filterForm = document.getElementById('filter-form');
        if (filterForm) {
            filterForm.addEventListener('submit', (e) => {
                this.handleFilterSubmit(e);
            });
        }

        // 重置筛选按钮
        const resetBtn = document.getElementById('reset-filter-btn');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                this.resetFilters();
            });
        }

        // 查看详情按钮
        document.querySelectorAll('.view-log-detail-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const logId = e.target.dataset.logId;
                this.showLogDetail(logId);
            });
        });
    },

    /**
     * 初始化筛选器
     */
    initFilters() {
        // 初始化日期选择器
        const dateInputs = document.querySelectorAll('.date-picker');
        dateInputs.forEach(input => {
            // 这里可以集成日期选择器库
            // 例如：flatpickr、bootstrap-datepicker等
        });
    },

    /**
     * 处理筛选表单提交
     */
    async handleFilterSubmit(event) {
        event.preventDefault();

        const form = event.target;
        const formData = new FormData(form);
        const params = Object.fromEntries(formData.entries());

        try {
            Utils.showLoading();

            // 构建查询字符串
            const queryString = new URLSearchParams(params).toString();
            window.location.href = `${window.location.pathname}?${queryString}`;
        } catch (error) {
            console.error('Failed to filter logs:', error);
            Utils.showAlert('筛选失败，请稍后重试', 'danger');
        } finally {
            Utils.hideLoading();
        }
    },

    /**
     * 重置筛选器
     */
    resetFilters() {
        const filterForm = document.getElementById('filter-form');
        if (filterForm) {
            filterForm.reset();
            window.location.href = window.location.pathname;
        }
    },

    /**
     * 显示操作日志详情
     */
    async showLogDetail(logId) {
        try {
            Utils.showLoading();

            const response = await API.get(`/operations/api/logs/${logId}/`);

            if (response.status === 'success') {
                this.showLogDetailModal(response.data);
            } else {
                Utils.showAlert(response.message || '获取详情失败', 'danger');
            }
        } catch (error) {
            console.error('Failed to get log detail:', error);
            Utils.showAlert('获取详情失败，请稍后重试', 'danger');
        } finally {
            Utils.hideLoading();
        }
    },

    /**
     * 显示操作日志详情模态框
     */
    showLogDetailModal(logData) {
        const modalHtml = `
            <div class="modal fade" id="logDetailModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">操作日志详情</h5>
                            <button type="button" class="close" data-dismiss="modal">
                                <span>&times;</span>
                            </button>
                        </div>
                        <div class="modal-body">
                            <div class="log-detail">
                                <div class="detail-row">
                                    <span class="detail-label">操作类型：</span>
                                    <span class="detail-value">${logData.operation_type}</span>
                                </div>
                                <div class="detail-row">
                                    <span class="detail-label">操作描述：</span>
                                    <span class="detail-value">${logData.description}</span>
                                </div>
                                <div class="detail-row">
                                    <span class="detail-label">操作用户：</span>
                                    <span class="detail-value">${logData.user || '系统'}</span>
                                </div>
                                <div class="detail-row">
                                    <span class="detail-label">操作时间：</span>
                                    <span class="detail-value">${Utils.formatDateTime(logData.created_at)}</span>
                                </div>
                                <div class="detail-row">
                                    <span class="detail-label">IP地址：</span>
                                    <span class="detail-value">${logData.ip_address || '-'}</span>
                                </div>
                                <div class="detail-row">
                                    <span class="detail-label">状态：</span>
                                    <span class="detail-value">${this.getStatusBadge(logData.status)}</span>
                                </div>
                                ${logData.error_message ? `
                                <div class="detail-row">
                                    <span class="detail-label">错误信息：</span>
                                    <span class="detail-value text-danger">${logData.error_message}</span>
                                </div>
                                ` : ''}
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-dismiss="modal">关闭</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        const modalContainer = document.createElement('div');
        modalContainer.innerHTML = modalHtml;
        document.body.appendChild(modalContainer);

        const modal = new bootstrap.Modal(document.getElementById('logDetailModal'));
        modal.show();

        document.getElementById('logDetailModal').addEventListener('hidden.bs.modal', () => {
            modalContainer.remove();
        });
    },

    /**
     * 获取状态徽章HTML
     */
    getStatusBadge(status) {
        const statusMap = {
            success: '<span class="badge badge-success">成功</span>',
            failed: '<span class="badge badge-danger">失败</span>',
            pending: '<span class="badge badge-warning">进行中</span>'
        };
        return statusMap[status] || status;
    },

    /**
     * 导出操作日志
     */
    async exportLogs() {
        try {
            Utils.showLoading();

            // 获取当前筛选条件
            const filterForm = document.getElementById('filter-form');
            const formData = filterForm ? new FormData(filterForm) : new FormData();
            const params = Object.fromEntries(formData.entries());

            // 调用导出API
            const response = await fetch('/operations/api/export/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': Config.csrfToken,
                },
                body: JSON.stringify(params),
            });

            if (response.ok) {
                // 下载文件
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `operation_logs_${new Date().getTime()}.xlsx`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);

                Utils.showAlert('导出成功', 'success');
            } else {
                Utils.showAlert('导出失败，请稍后重试', 'danger');
            }
        } catch (error) {
            console.error('Failed to export logs:', error);
            Utils.showAlert('导出失败，请稍后重试', 'danger');
        } finally {
            Utils.hideLoading();
        }
    }
};

// 任务管理器
const TaskManager = {
    /**
     * 初始化任务管理
     */
    init() {
        this.bindEvents();
        this.startAutoRefresh();
    },

    /**
     * 绑定事件
     */
    bindEvents() {
        // 取消任务按钮
        document.querySelectorAll('.cancel-task-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const taskId = e.target.dataset.taskId;
                this.cancelTask(taskId);
            });
        });

        // 重试任务按钮
        document.querySelectorAll('.retry-task-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const taskId = e.target.dataset.taskId;
                this.retryTask(taskId);
            });
        });

        // 查看任务详情按钮
        document.querySelectorAll('.view-task-detail-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const taskId = e.target.dataset.taskId;
                this.showTaskDetail(taskId);
            });
        });
    },

    /**
     * 开始自动刷新
     */
    startAutoRefresh() {
        // 每30秒刷新一次任务状态
        this.refreshInterval = setInterval(() => {
            this.updateTaskStatus();
        }, 30000);
    },

    /**
     * 停止自动刷新
     */
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    },

    /**
     * 更新任务状态
     */
    async updateTaskStatus() {
        const taskItems = document.querySelectorAll('.task-item[data-status="running"]');

        for (const item of taskItems) {
            const taskId = item.dataset.taskId;
            try {
                const response = await API.get(`/operations/api/tasks/${taskId}/`);

                if (response.status === 'success') {
                    this.updateTaskItem(item, response.data);
                }
            } catch (error) {
                console.error(`Failed to update task ${taskId}:`, error);
            }
        }
    },

    /**
     * 更新任务项
     */
    updateTaskItem(item, data) {
        // 更新状态
        const statusBadge = item.querySelector('.task-status');
        if (statusBadge) {
            statusBadge.className = `task-status ${data.status}`;
            statusBadge.textContent = this.getStatusText(data.status);
        }

        // 更新进度
        const progressBar = item.querySelector('.progress-bar .progress');
        if (progressBar) {
            progressBar.style.width = `${data.progress}%`;
        }

        // 更新数据属性
        item.dataset.status = data.status;
    },

    /**
     * 获取状态文本
     */
    getStatusText(status) {
        const statusMap = {
            pending: '等待中',
            running: '执行中',
            success: '成功',
            failed: '失败',
            cancelled: '已取消'
        };
        return statusMap[status] || status;
    },

    /**
     * 取消任务
     */
    async cancelTask(taskId) {
        if (!Utils.confirm('确定要取消此任务吗？')) {
            return;
        }

        try {
            Utils.showLoading();

            const response = await API.post(`/operations/api/tasks/${taskId}/cancel/`);

            if (response.status === 'success') {
                Utils.showAlert('任务已取消', 'success');
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                Utils.showAlert(response.message || '取消失败', 'danger');
            }
        } catch (error) {
            console.error('Failed to cancel task:', error);
            Utils.showAlert('取消失败，请稍后重试', 'danger');
        } finally {
            Utils.hideLoading();
        }
    },

    /**
     * 重试任务
     */
    async retryTask(taskId) {
        if (!Utils.confirm('确定要重试此任务吗？')) {
            return;
        }

        try {
            Utils.showLoading();

            const response = await API.post(`/operations/api/tasks/${taskId}/retry/`);

            if (response.status === 'success') {
                Utils.showAlert('任务已重新开始', 'success');
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                Utils.showAlert(response.message || '重试失败', 'danger');
            }
        } catch (error) {
            console.error('Failed to retry task:', error);
            Utils.showAlert('重试失败，请稍后重试', 'danger');
        } finally {
            Utils.hideLoading();
        }
    },

    /**
     * 显示任务详情
     */
    async showTaskDetail(taskId) {
        try {
            Utils.showLoading();

            const response = await API.get(`/operations/api/tasks/${taskId}/`);

            if (response.status === 'success') {
                this.showTaskDetailModal(response.data);
            } else {
                Utils.showAlert(response.message || '获取详情失败', 'danger');
            }
        } catch (error) {
            console.error('Failed to get task detail:', error);
            Utils.showAlert('获取详情失败，请稍后重试', 'danger');
        } finally {
            Utils.hideLoading();
        }
    },

    /**
     * 显示任务详情模态框
     */
    showTaskDetailModal(taskData) {
        const modalHtml = `
            <div class="modal fade" id="taskDetailModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">任务详情</h5>
                            <button type="button" class="close" data-dismiss="modal">
                                <span>&times;</span>
                            </button>
                        </div>
                        <div class="modal-body">
                            <div class="task-detail">
                                <div class="detail-row">
                                    <span class="detail-label">任务名称：</span>
                                    <span class="detail-value">${taskData.name}</span>
                                </div>
                                <div class="detail-row">
                                    <span class="detail-label">任务类型：</span>
                                    <span class="detail-value">${taskData.task_type}</span>
                                </div>
                                <div class="detail-row">
                                    <span class="detail-label">状态：</span>
                                    <span class="detail-value">${this.getStatusText(taskData.status)}</span>
                                </div>
                                <div class="detail-row">
                                    <span class="detail-label">进度：</span>
                                    <span class="detail-value">${taskData.progress}%</span>
                                </div>
                                <div class="detail-row">
                                    <span class="detail-label">创建时间：</span>
                                    <span class="detail-value">${Utils.formatDateTime(taskData.created_at)}</span>
                                </div>
                                ${taskData.started_at ? `
                                <div class="detail-row">
                                    <span class="detail-label">开始时间：</span>
                                    <span class="detail-value">${Utils.formatDateTime(taskData.started_at)}</span>
                                </div>
                                ` : ''}
                                ${taskData.completed_at ? `
                                <div class="detail-row">
                                    <span class="detail-label">完成时间：</span>
                                    <span class="detail-value">${Utils.formatDateTime(taskData.completed_at)}</span>
                                </div>
                                ` : ''}
                                ${taskData.result ? `
                                <div class="detail-row">
                                    <span class="detail-label">执行结果：</span>
                                    <span class="detail-value">${taskData.result}</span>
                                </div>
                                ` : ''}
                                ${taskData.error_message ? `
                                <div class="detail-row">
                                    <span class="detail-label">错误信息：</span>
                                    <span class="detail-value text-danger">${taskData.error_message}</span>
                                </div>
                                ` : ''}
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-dismiss="modal">关闭</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        const modalContainer = document.createElement('div');
        modalContainer.innerHTML = modalHtml;
        document.body.appendChild(modalContainer);

        const modal = new bootstrap.Modal(document.getElementById('taskDetailModal'));
        modal.show();

        document.getElementById('taskDetailModal').addEventListener('hidden.bs.modal', () => {
            modalContainer.remove();
        });
    }
};

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    if (document.querySelector('.operation-logs-page')) {
        OperationLog.init();
    }

    if (document.querySelector('.tasks-page')) {
        TaskManager.init();
    }
});

// 导出到全局
window.OperationLog = OperationLog;
window.TaskManager = TaskManager;
