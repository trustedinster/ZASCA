/**
 * Django Admin 移动端交互脚本
 */
(function() {
  'use strict';

  // 等待 DOM 加载完成
  document.addEventListener('DOMContentLoaded', function() {
    initSidebarToggle();
    initFilterToggle();
    initTableDataLabels();
    initTouchOptimizations();
  });

  /**
   * 侧边栏抽屉切换
   */
  function initSidebarToggle() {
    const sidebar = document.getElementById('nav-sidebar');
    if (!sidebar) return;

    // 创建切换按钮
    const toggleBtn = document.createElement('button');
    toggleBtn.className = 'sidebar-toggle';
    toggleBtn.setAttribute('aria-label', '菜单');
    toggleBtn.innerHTML = '<span></span>';

    // 创建遮罩层
    const backdrop = document.createElement('div');
    backdrop.className = 'sidebar-backdrop';

    // 插入到页面
    const header = document.getElementById('header');
    if (header) {
      header.insertBefore(toggleBtn, header.firstChild);
    }
    document.body.appendChild(backdrop);

    // 切换事件
    toggleBtn.addEventListener('click', function(e) {
      e.preventDefault();
      sidebar.classList.toggle('show');
      backdrop.classList.toggle('show');
      document.body.style.overflow = sidebar.classList.contains('show') ? 'hidden' : '';
    });

    // 点击遮罩关闭
    backdrop.addEventListener('click', function() {
      sidebar.classList.remove('show');
      backdrop.classList.remove('show');
      document.body.style.overflow = '';
    });

    // ESC 键关闭
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && sidebar.classList.contains('show')) {
        sidebar.classList.remove('show');
        backdrop.classList.remove('show');
        document.body.style.overflow = '';
      }
    });
  }

  /**
   * 筛选器抽屉切换
   */
  function initFilterToggle() {
    const filter = document.getElementById('changelist-filter');
    if (!filter) return;

    // 创建切换按钮
    const toggleBtn = document.createElement('button');
    toggleBtn.className = 'filter-toggle';
    toggleBtn.textContent = '筛选';

    // 创建关闭按钮
    const closeBtn = document.createElement('button');
    closeBtn.className = 'filter-close';
    closeBtn.innerHTML = '×';
    closeBtn.setAttribute('aria-label', '关闭筛选');

    // 在筛选器标题添加关闭按钮
    const filterTitle = filter.querySelector('h2');
    if (filterTitle) {
      filterTitle.appendChild(closeBtn);
    }

    // 创建遮罩层
    const backdrop = document.createElement('div');
    backdrop.className = 'sidebar-backdrop filter-backdrop';
    document.body.appendChild(backdrop);

    // 插入切换按钮
    const changelist = document.getElementById('changelist');
    if (changelist) {
      changelist.insertBefore(toggleBtn, changelist.firstChild);
    }

    // 切换事件
    toggleBtn.addEventListener('click', function(e) {
      e.preventDefault();
      filter.classList.add('show');
      backdrop.classList.add('show');
      document.body.style.overflow = 'hidden';
    });

    // 关闭事件
    function closeFilter() {
      filter.classList.remove('show');
      backdrop.classList.remove('show');
      document.body.style.overflow = '';
    }

    closeBtn.addEventListener('click', closeFilter);
    backdrop.addEventListener('click', closeFilter);

    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && filter.classList.contains('show')) {
        closeFilter();
      }
    });
  }

  /**
   * 表格添加 data-label 属性
   */
  function initTableDataLabels() {
    const table = document.getElementById('result_list');
    if (!table) return;

    const headers = table.querySelectorAll('thead th');
    const headerTexts = Array.from(headers).map(function(th) {
      // 获取纯文本，去除排序链接等
      const text = th.textContent || th.innerText;
      return text.trim();
    });

    const rows = table.querySelectorAll('tbody tr');
    rows.forEach(function(row) {
      const cells = row.querySelectorAll('td');
      cells.forEach(function(cell, index) {
        if (headerTexts[index]) {
          cell.setAttribute('data-label', headerTexts[index]);
        }
      });
    });
  }

  /**
   * 触控优化
   */
  function initTouchOptimizations() {
    // 检测是否为触控设备
    const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;

    if (isTouchDevice) {
      document.body.classList.add('touch-device');

      // 优化点击响应
      const clickableElements = document.querySelectorAll('a, button, input[type="submit"], .btn');
      clickableElements.forEach(function(el) {
        el.addEventListener('touchstart', function() {
          this.classList.add('touch-active');
        }, { passive: true });

        el.addEventListener('touchend', function() {
          this.classList.remove('touch-active');
        }, { passive: true });
      });
    }

    // 防止 iOS 双击缩放
    let lastTouchEnd = 0;
    document.addEventListener('touchend', function(e) {
      const now = Date.now();
      if (now - lastTouchEnd <= 300) {
        e.preventDefault();
      }
      lastTouchEnd = now;
    }, { passive: false });
  }

  /**
   * 视口高度修复（iOS Safari）
   */
  function setViewportHeight() {
    const vh = window.innerHeight * 0.01;
    document.documentElement.style.setProperty('--vh', vh + 'px');
  }

  window.addEventListener('resize', setViewportHeight);
  setViewportHeight();

})();
