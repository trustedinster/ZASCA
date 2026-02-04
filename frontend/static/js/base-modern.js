// Modern ZASCA Base JavaScript

// 页面加载动画
document.addEventListener('DOMContentLoaded', function() {
    // 添加淡入效果
    const mainContent = document.querySelector('main');
    if (mainContent) {
        mainContent.classList.add('fade-in');
    }

    // 初始化工具提示
    initializeTooltips();

    // 初始化加载状态
    initializeLoadingStates();

    // 初始化表格增强
    initializeTableEnhancements();

    // 初始化表单增强
    initializeFormEnhancements();
});

// 工具提示初始化
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl, {
            placement: tooltipTriggerEl.dataset.placement || 'top',
            trigger: 'hover'
        });
    });
}

// 加载状态管理
function initializeLoadingStates() {
    // 为所有异步操作添加加载指示器
    document.querySelectorAll('[data-loading-text]').forEach(button => {
        button.addEventListener('click', function() {
            const originalText = this.innerHTML;
            const loadingText = this.dataset.loadingText;
            const spinnerHtml = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>';

            if (this.tagName === 'BUTTON' && !this.disabled) {
                this.innerHTML = spinnerHtml + loadingText;
                this.disabled = true;

                // 重置按钮状态（防止页面未跳转）
                setTimeout(() => {
                    this.innerHTML = originalText;
                    this.disabled = false;
                }, 5000);
            }
        });
    });
}

// 表格增强功能
function initializeTableEnhancements() {
    document.querySelectorAll('table').forEach(table => {
        // 添加行悬停效果
        table.querySelectorAll('tbody tr').forEach(row => {
            row.addEventListener('mouseenter', function() {
                this.style.backgroundColor = '#f8fafc';
            });

            row.addEventListener('mouseleave', function() {
                this.style.backgroundColor = '';
            });
        });

        // 添加排序指示器
        const sortableHeaders = table.querySelectorAll('th[data-sortable]');
        sortableHeaders.forEach(header => {
            header.style.cursor = 'pointer';
            header.innerHTML = header.innerHTML + ' <i class="bi bi-arrow-up-down text-muted"></i>';

            header.addEventListener('click', function() {
                handleTableSort(this);
            });
        });
    });
}

// 表格排序功能
function handleTableSort(header) {
    const table = header.closest('table');
    const columnIndex = Array.from(header.parentElement.children).indexOf(header);

    // 移除其他列的排序状态
    header.parentElement.querySelectorAll('th').forEach(th => {
        if (th !== header) {
            th.classList.remove('sort-asc', 'sort-desc');
            th.innerHTML = th.innerHTML.replace(/<i class=".*?">.*?<\/i>/, ' <i class="bi bi-arrow-up-down text-muted"></i>');
        }
    });

    // 切换排序方向
    const isAsc = !header.classList.contains('sort-asc');
    header.classList.remove('sort-asc', 'sort-desc');
    header.classList.add(isAsc ? 'sort-asc' : 'sort-desc');

    // 更新排序图标
    header.innerHTML = header.innerHTML.replace(/<i class=".*?">.*?<\/i>/,
        ` <i class="bi ${isAsc ? 'bi-sort-up' : 'bi-sort-down'}"></i>`);

    // 执行排序逻辑（这里可以连接到后端API）
    sortTable(table, columnIndex, isAsc);
}

// 客户端表格排序（简单实现）
function sortTable(table, columnIndex, ascending) {
    const rows = Array.from(table.querySelectorAll('tbody tr'));

    rows.sort((a, b) => {
        const valueA = a.children[columnIndex].textContent;
        const valueB = b.children[columnIndex].textContent;

        // 尝试数字比较
        const numA = parseFloat(valueA);
        const numB = parseFloat(valueB);

        if (!isNaN(numA) && !isNaN(numB)) {
            return ascending ? numA - numB : numB - numA;
        }

        // 字符串比较
        return ascending ? valueA.localeCompare(valueB) : valueB.localeCompare(valueA);
    });

    // 重新排列行
    const tbody = table.querySelector('tbody');
    rows.forEach(row => tbody.appendChild(row));
}

// 表单增强功能
function initializeFormEnhancements() {
    // 密码强度指示器
    document.querySelectorAll('input[type="password"][data-strength-indicator]').forEach(input => {
        const indicatorId = input.dataset.strengthIndicator;
        const indicator = document.getElementById(indicatorId);

        if (indicator) {
            input.addEventListener('input', function() {
                updatePasswordStrength(this.value, indicator);
            });
        }
    });

    // 表单验证实时反馈
    document.querySelectorAll('form').forEach(form => {
        form.querySelectorAll('input, select, textarea').forEach(field => {
            if (field.dataset.validate !== 'false') {
                field.addEventListener('blur', function() {
                    validateField(this);
                });
            }
        });
    });

    // 自动保存草稿功能
    document.querySelectorAll('form[data-auto-save]').forEach(form => {
        const saveInterval = parseInt(form.dataset.autoSave) || 30; // 默认30秒
        let saveTimer;

        form.addEventListener('input', function() {
            clearTimeout(saveTimer);
            saveTimer = setTimeout(() => {
                saveFormDraft(form);
            }, saveInterval * 1000);
        });
    });
}

// 密码强度更新
function updatePasswordStrength(password, indicator) {
    let strength = 0;

    if (password.length >= 8) strength++;
    if (password.match(/[a-z]/)) strength++;
    if (password.match(/[A-Z]/)) strength++;
    if (password.match(/[0-9]/)) strength++;
    if (password.match(/[^a-zA-Z0-9]/)) strength++;

    indicator.className = 'password-strength';
    let color, text;

    switch(strength) {
        case 0:
        case 1:
            color = 'danger';
            text = '弱';
            break;
        case 2:
        case 3:
            color = 'warning';
            text = '中等';
            break;
        case 4:
            color = 'info';
            text = '良好';
            break;
        case 5:
            color = 'success';
            text = '强';
            break;
    }

    indicator.classList.add(`text-${color}`);
    indicator.innerHTML = `<small>密码强度: <strong>${text}</strong></small>`;
}

// 自动保存草稿
function saveFormDraft(form) {
    const formId = form.id || form.name || location.pathname;
    const formData = new FormData(form);
    const data = {};

    for (let [key, value] of formData.entries()) {
        if (value) data[key] = value;
    }

    localStorage.setItem(`draft_${formId}`, JSON.stringify(data));

    // 显示保存提示
    showToast('草稿已自动保存', 'info');
}

// 恢复草稿
function restoreFormDraft(form) {
    const formId = form.id || form.name || location.pathname;
    const draft = localStorage.getItem(`draft_${formId}`);

    if (draft) {
        const data = JSON.parse(draft);

        for (let key in data) {
            const field = form.querySelector(`[name="${key}"]`);
            if (field) field.value = data[key];
        }

        showToast('草稿已恢复', 'success');
    }
}

// Toast 提示
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container') || createToastContainer();

    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <i class="bi ${type === 'success' ? 'bi-check-circle' : type === 'error' ? 'bi-x-circle' : 'bi-info-circle'} me-2"></i>
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;

    toastContainer.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();

    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    container.style.zIndex = '9999';
    document.body.appendChild(container);
    return container;
}

// 实时数据更新（WebSocket 模拟）
function initializeRealTimeUpdates() {
    // 查找需要实时更新的元素
    document.querySelectorAll('[data-real-time]').forEach(element => {
        const updateInterval = parseInt(element.dataset.updateInterval) || 5000;

        // 使用长轮询模拟实时更新
        const updateData = async () => {
            try {
                const response = await fetch(element.dataset.realTime);
                const data = await response.json();

                // 更新界面（这里需要根据具体数据结构自定义）
                updateUIElement(element, data);
            } catch (error) {
                console.error('Real-time update failed:', error);
            }

            // 下次更新
            setTimeout(updateData, updateInterval);
        };

        // 开始第一次更新
        updateData();
    });
}

// 更新UI元素（根据实际需要定制）
function updateUIElement(element, data) {
    // 这里根据返回的数据结构来更新对应的DOM元素
    if (data.status) {
        element.textContent = data.status;
        element.className = element.className.replace(/status-\w+/, `status-${data.status.toLowerCase()}`);
    }
}

// 暗黑模式检测
if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    document.body.classList.add('dark-mode');
}

window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
    if (e.matches) {
        document.body.classList.add('dark-mode');
    } else {
        document.body.classList.remove('dark-mode');
    }
});

// 全局搜索功能（可选实现）
function initializeGlobalSearch() {
    const searchInput = document.getElementById('globalSearch');
    if (searchInput) {
        let searchTimeout;

        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const query = this.value.trim();

            if (query.length > 2) {
                searchTimeout = setTimeout(() => {
                    performGlobalSearch(query);
                }, 300);
            }
        });
    }
}

// 全局搜索实现
function performGlobalSearch(query) {
    // 这里可以实现全局搜索功能
    // 可以通过 AJAX 请求后端搜索 API
    console.log('Searching for:', query);
}

// 键盘快捷键支持
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + K 打开搜索
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.getElementById('globalSearch');
        if (searchInput) {
            searchInput.focus();
        }
    }

    // ESC 关闭模态框
    if (e.key === 'Escape') {
        const openModals = document.querySelectorAll('.modal.show');
        openModals.forEach(modal => {
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) bsModal.hide();
        });
    }
});