/**
 * 仪表盘JavaScript功能
 */

// 仪表盘管理器
const Dashboard = {
    charts: {},
    refreshInterval: null,

    /**
     * 初始化仪表盘
     */
    init() {
        this.initCharts();
        this.startAutoRefresh();
        this.bindEvents();
    },

    /**
     * 初始化图表
     */
    initCharts() {
        // 主机状态分布图
        const hostStatusCtx = document.getElementById('hostStatusChart');
        if (hostStatusCtx) {
            this.charts.hostStatus = new Chart(hostStatusCtx, {
                type: 'doughnut',
                data: {
                    labels: ['在线', '离线', '未知'],
                    datasets: [{
                        data: [0, 0, 0],
                        backgroundColor: [
                            '#28a745',
                            '#dc3545',
                            '#6c757d'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });
        }

        // 操作趋势图
        const operationTrendCtx = document.getElementById('operationTrendChart');
        if (operationTrendCtx) {
            this.charts.operationTrend = new Chart(operationTrendCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: '操作次数',
                        data: [],
                        borderColor: '#007bff',
                        fill: false,
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                stepSize: 1
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });
        }
    },

    /**
     * 更新图表数据
     */
    async updateCharts() {
        try {
            const data = await API.get('/dashboard/api/stats/');

            if (this.charts.hostStatus) {
                this.charts.hostStatus.data.datasets[0].data = [
                    data.hosts.online,
                    data.hosts.offline,
                    data.hosts.error
                ];
                this.charts.hostStatus.update();
            }

            if (this.charts.operationTrend) {
                const trendData = await this.getOperationTrend();
                this.charts.operationTrend.data.labels = trendData.labels;
                this.charts.operationTrend.data.datasets[0].data = trendData.data;
                this.charts.operationTrend.update();
            }
        } catch (error) {
            console.error('Failed to update charts:', error);
        }
    },

    /**
     * 获取操作趋势数据
     */
    async getOperationTrend() {
        try {
            const response = await API.get('/dashboard/api/stats/', { type: 'operations' });
            // 这里可以根据实际API返回的数据格式进行调整
            return {
                labels: [],
                data: []
            };
        } catch (error) {
            console.error('Failed to get operation trend:', error);
            return { labels: [], data: [] };
        }
    },

    /**
     * 开始自动刷新
     */
    startAutoRefresh() {
        // 每5分钟刷新一次数据
        this.refreshInterval = setInterval(() => {
            this.updateCharts();
        }, 300000);
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
     * 绑定事件
     */
    bindEvents() {
        // 刷新按钮
        const refreshBtn = document.getElementById('refresh-dashboard');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.updateCharts();
            });
        }

        // 组件配置按钮
        const configBtn = document.getElementById('widget-config-btn');
        if (configBtn) {
            configBtn.addEventListener('click', () => {
                window.location.href = '/dashboard/widget-config/';
            });
        }
    }
};

// 组件配置管理器
const WidgetConfig = {
    /**
     * 初始化组件配置
     */
    init() {
        this.bindEvents();
    },

    /**
     * 保存配置
     */
    async saveConfig() {
        const widgets = [];

        document.querySelectorAll('.widget-item').forEach(item => {
            const widgetId = item.dataset.widgetId;
            const isEnabled = item.querySelector('.widget-enabled').checked;
            const displayOrder = item.querySelector('.widget-order').value;

            widgets.push({
                widget_id: parseInt(widgetId),
                is_enabled: isEnabled,
                display_order: parseInt(displayOrder)
            });
        });

        try {
            Utils.showLoading();

            const response = await API.post('/dashboard/api/widget-config/', { widgets });

            if (response.status === 'success') {
                Utils.showAlert('配置保存成功', 'success');
                setTimeout(() => {
                    window.location.href = '/dashboard/';
                }, 1000);
            } else {
                Utils.showAlert(response.message || '保存失败', 'danger');
            }
        } catch (error) {
            console.error('Failed to save widget config:', error);
            Utils.showAlert('保存失败，请稍后重试', 'danger');
        } finally {
            Utils.hideLoading();
        }
    },

    /**
     * 绑定事件
     */
    bindEvents() {
        const saveBtn = document.getElementById('save-widget-config');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => {
                this.saveConfig();
            });
        }
    }
};

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    const isDashboardPage = document.querySelector('.dashboard-page');
    const isConfigPage = document.querySelector('.widget-config-page');

    if (isDashboardPage) {
        Dashboard.init();
    }

    if (isConfigPage) {
        WidgetConfig.init();
    }
});

// 导出到全局
window.Dashboard = Dashboard;
window.WidgetConfig = WidgetConfig;
