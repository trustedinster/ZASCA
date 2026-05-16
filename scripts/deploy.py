#!/usr/bin/env python3
"""
ZASCA 交互式部署脚本
根据部署环境动态生成 pyproject.toml，仅安装所需依赖，避免冗余库

用法:
    python3 scripts/deploy.py
"""

import os
import sys
import shutil
import subprocess
import curses
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent

DEPS_CORE = {
    "Django": "Django==4.2.27",
    "djangorestframework": "djangorestframework==3.15.2",
    "django-cors-headers": "django-cors-headers==4.3.1",
    "django-cotton": "django-cotton @ git+https://github.com/2c2a/django-cotton.git@feature/x-prefix-tag-support",
    "django-formtools": "django-formtools>=2.5.1",
    "python-dotenv": "python-dotenv==1.2.1",
    "PyJWT": "PyJWT>=2.8.0",
    "cryptography": "cryptography==46.0.3",
    "requests": "requests==2.32.3",
    "pillow": "pillow==12.1.0",
    "toml": "toml",
}

DEPS_CELERY = {
    "celery": "celery==5.4.0",
}

DEPS_MYSQL = {
    "pymysql": "pymysql>=1.1.2",
}

DEPS_POSTGRESQL = {
    "psycopg": "psycopg[binary]>=3.0",
}

DEPS_REDIS = {
    "redis": "redis>=5.0.0",
}

DEPS_SQLITE_BROKER = {
    "sqlalchemy": "sqlalchemy>=2.0.0",
}

DEPS_WINRM = {
    "pywinrm": "pywinrm==0.4.3",
}

DEPS_KERBEROS = {
    "gssapi": "gssapi>=1.11.1",
    "krb5": "krb5>=0.9.0",
}

DEPS_MARKDOWN = {
    "Markdown": "Markdown==3.10.1",
}

DEPS_2FA = {
    "pyotp": "pyotp",
}

DEPS_DEV = {
    "pytest": "pytest",
    "pytest-django": "pytest-django",
    "black": "black",
    "flake8": "flake8",
    "django-stubs": "django-stubs>=6.0.2",
    "pyrefly": "pyrefly>=0.60.0",
}

DB_OPTIONS = [
    ("sqlite", "SQLite", "零配置本地文件数据库，适合开发/小规模部署"),
    ("mysql", "MySQL / MariaDB", "生产级关系数据库，适合中大规模部署"),
    ("postgresql", "PostgreSQL", "生产级关系数据库，功能最丰富"),
]

FEATURE_OPTIONS = [
    ("celery", "Celery 异步任务队列", "后台任务处理（主机操作、工单通知等）", True),
    ("redis", "Redis 缓存/消息队列", "高性能缓存、会话存储、Celery Broker", False),
    ("winrm", "WinRM Windows 远程管理", "远程管理 Windows 服务器", False),
    ("kerberos", "Kerberos 域认证", "Windows 域环境集成认证", False),
    ("markdown", "Markdown 渲染", "仪表盘/工单中的 Markdown 内容渲染", True),
    ("2fa", "双因素认证 (TOTP)", "基于时间的一次性密码二次验证", True),
]

DEV_OPTION = ("dev", "开发/测试工具", "pytest, black, flake8, django-stubs 等", False)

C_TITLE = 1
C_SUBTITLE = 2
C_HIGHLIGHT = 3
C_SELECTED = 4
C_UNSELECTED = 5
C_RADIO_ON = 6
C_RADIO_OFF = 7
C_CHECK_ON = 8
C_CHECK_OFF = 9
C_DESC = 10
C_HINT = 11
C_BORDER = 12
C_SUCCESS = 13
C_WARN = 14
C_ERROR = 15
C_DEP = 16
C_DEP_DEV = 17
C_BANNER = 18


def _safe_addstr(stdscr, y, x, text, attr=0):
    max_y, max_x = stdscr.getmaxyx()
    if y < 0 or y >= max_y or x < 0 or x >= max_x:
        return
    available = max_x - x - 1
    if available <= 0:
        return
    text = text[:available]
    try:
        stdscr.addstr(y, x, text, attr)
    except curses.error:
        pass


def _init_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(C_TITLE, curses.COLOR_CYAN, -1)
    curses.init_pair(C_SUBTITLE, curses.COLOR_WHITE, -1)
    curses.init_pair(C_HIGHLIGHT, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(C_SELECTED, curses.COLOR_CYAN, -1)
    curses.init_pair(C_UNSELECTED, curses.COLOR_WHITE, -1)
    curses.init_pair(C_RADIO_ON, curses.COLOR_GREEN, -1)
    curses.init_pair(C_RADIO_OFF, curses.COLOR_WHITE, -1)
    curses.init_pair(C_CHECK_ON, curses.COLOR_GREEN, -1)
    curses.init_pair(C_CHECK_OFF, curses.COLOR_WHITE, -1)
    curses.init_pair(C_DESC, 8, -1)
    curses.init_pair(C_HINT, curses.COLOR_YELLOW, -1)
    curses.init_pair(C_BORDER, curses.COLOR_CYAN, -1)
    curses.init_pair(C_SUCCESS, curses.COLOR_GREEN, -1)
    curses.init_pair(C_WARN, curses.COLOR_YELLOW, -1)
    curses.init_pair(C_ERROR, curses.COLOR_RED, -1)
    curses.init_pair(C_DEP, curses.COLOR_GREEN, -1)
    curses.init_pair(C_DEP_DEV, curses.COLOR_YELLOW, -1)
    curses.init_pair(C_BANNER, curses.COLOR_CYAN, -1)


def _draw_banner(stdscr, y, max_x):
    title = " ZASCA 交互式部署管理脚本 "
    x = max(0, (max_x - len(title)) // 2)
    _safe_addstr(stdscr, y, x, title, curses.color_pair(C_BANNER) | curses.A_BOLD)


def _draw_box(stdscr, y, x, h, w):
    _safe_addstr(stdscr, y, x, "┌" + "─" * (w - 2) + "┐", curses.color_pair(C_BORDER))
    for i in range(1, h - 1):
        _safe_addstr(stdscr, y + i, x, "│", curses.color_pair(C_BORDER))
        _safe_addstr(stdscr, y + i, x + w - 1, "│", curses.color_pair(C_BORDER))
    _safe_addstr(stdscr, y + h - 1, x, "└" + "─" * (w - 2) + "┘", curses.color_pair(C_BORDER))


def _draw_radio_item(stdscr, y, x, selected, active, label, desc, max_w):
    if selected:
        marker = "◉"
        m_color = C_RADIO_ON | curses.A_BOLD
    else:
        marker = "○"
        m_color = C_RADIO_OFF

    if active:
        bg = curses.color_pair(C_HIGHLIGHT) | curses.A_BOLD
        _safe_addstr(stdscr, y, x, f"  {marker} {label}", bg)
    else:
        _safe_addstr(stdscr, y, x, "  ", curses.color_pair(C_UNSELECTED))
        _safe_addstr(stdscr, y, x + 2, marker, curses.color_pair(m_color))
        _safe_addstr(stdscr, y, x + 4, label, curses.color_pair(C_SELECTED if selected else C_UNSELECTED) | curses.A_BOLD)

    if desc:
        desc_x = x + 6
        remaining = max_w - (desc_x - x) - 1
        if remaining > 3:
            _safe_addstr(stdscr, y + 1, desc_x, desc[:remaining], curses.color_pair(C_DESC) if not active else curses.color_pair(C_HIGHLIGHT))


def _draw_check_item(stdscr, y, x, checked, active, label, desc, max_w):
    if checked:
        marker = "☑"
        m_color = C_CHECK_ON | curses.A_BOLD
    else:
        marker = "☐"
        m_color = C_CHECK_OFF

    if active:
        bg = curses.color_pair(C_HIGHLIGHT) | curses.A_BOLD
        _safe_addstr(stdscr, y, x, f"  {marker} {label}", bg)
    else:
        _safe_addstr(stdscr, y, x, "  ", curses.color_pair(C_UNSELECTED))
        _safe_addstr(stdscr, y, x + 2, marker, curses.color_pair(m_color))
        _safe_addstr(stdscr, y, x + 4, label, curses.color_pair(C_SELECTED if checked else C_UNSELECTED) | curses.A_BOLD)

    if desc:
        desc_x = x + 6
        remaining = max_w - (desc_x - x) - 1
        if remaining > 3:
            _safe_addstr(stdscr, y + 1, desc_x, desc[:remaining], curses.color_pair(C_DESC) if not active else curses.color_pair(C_HIGHLIGHT))


def _draw_hint(stdscr, y, x, hint_text):
    _safe_addstr(stdscr, y, x, hint_text, curses.color_pair(C_HINT))


def _page_db(stdscr, selected):
    _init_colors()
    stdscr.clear()
    max_y, max_x = stdscr.getmaxyx()
    box_w = min(72, max_x - 4)
    box_h = 5 + len(DB_OPTIONS) * 3
    box_x = max(0, (max_x - box_w) // 2)
    box_y = 2

    _draw_banner(stdscr, 0, max_x)
    _draw_box(stdscr, box_y, box_x, box_h, box_w)

    title = " 数据库引擎 (单选) "
    tx = box_x + max(0, (box_w - len(title)) // 2)
    _safe_addstr(stdscr, box_y, tx, title, curses.color_pair(C_TITLE) | curses.A_BOLD)

    for i, (key, label, desc) in enumerate(DB_OPTIONS):
        iy = box_y + 2 + i * 3
        _draw_radio_item(stdscr, iy, box_x + 2, i == selected, i == selected, label, desc, box_w - 4)

    hint_y = box_y + box_h + 1
    _draw_hint(stdscr, hint_y, box_x + 2, "↑↓ 移动  Enter 确认  Esc 退出")

    stdscr.refresh()


def _select_db(stdscr):
    selected = 0
    while True:
        _page_db(stdscr, selected)
        key = stdscr.getch()
        if key == curses.KEY_UP:
            selected = (selected - 1) % len(DB_OPTIONS)
        elif key == curses.KEY_DOWN:
            selected = (selected + 1) % len(DB_OPTIONS)
        elif key in (curses.KEY_ENTER, 10, 13):
            return DB_OPTIONS[selected][0]
        elif key == 27:
            return None
        elif key in (ord('1'), ord('2'), ord('3')):
            idx = key - ord('1')
            if 0 <= idx < len(DB_OPTIONS):
                return DB_OPTIONS[idx][0]


def _page_features(stdscr, cursor, features_state, dev_state, page):
    _init_colors()
    stdscr.clear()
    max_y, max_x = stdscr.getmaxyx()

    if page == 0:
        items = FEATURE_OPTIONS
        total = len(items)
        box_w = min(76, max_x - 4)
        box_h = 5 + total * 3
        box_x = max(0, (max_x - box_w) // 2)
        box_y = 2

        _draw_banner(stdscr, 0, max_x)
        _draw_box(stdscr, box_y, box_x, box_h, box_w)

        title = " 功能模块 (多选) "
        tx = box_x + max(0, (box_w - len(title)) // 2)
        _safe_addstr(stdscr, box_y, tx, title, curses.color_pair(C_TITLE) | curses.A_BOLD)

        for i, (key, label, desc, default) in enumerate(items):
            iy = box_y + 2 + i * 3
            _draw_check_item(stdscr, iy, box_x + 2, features_state[key], i == cursor, label, desc, box_w - 4)

        hint_y = box_y + box_h + 1
        _draw_hint(stdscr, hint_y, box_x + 2, "↑↓ 移动  Space 切换  Enter 下一步  Esc 返回")
    else:
        box_w = min(76, max_x - 4)
        box_h = 7
        box_x = max(0, (max_x - box_w) // 2)
        box_y = 2

        _draw_banner(stdscr, 0, max_x)
        _draw_box(stdscr, box_y, box_x, box_h, box_w)

        title = " 开发环境 "
        tx = box_x + max(0, (box_w - len(title)) // 2)
        _safe_addstr(stdscr, box_y, tx, title, curses.color_pair(C_TITLE) | curses.A_BOLD)

        key, label, desc, default = DEV_OPTION
        iy = box_y + 2
        _draw_check_item(stdscr, iy, box_x + 2, dev_state, True, label, desc, box_w - 4)

        hint_y = box_y + box_h + 1
        _draw_hint(stdscr, hint_y, box_x + 2, "Space 切换  Enter 确认  Esc 返回")

    stdscr.refresh()


def _select_features(stdscr):
    features_state = {key: default for key, _, _, default in FEATURE_OPTIONS}
    dev_state = DEV_OPTION[3]
    cursor = 0
    page = 0

    while True:
        _page_features(stdscr, cursor, features_state, dev_state, page)
        key = stdscr.getch()

        if page == 0:
            if key == curses.KEY_UP:
                cursor = (cursor - 1) % len(FEATURE_OPTIONS)
            elif key == curses.KEY_DOWN:
                cursor = (cursor + 1) % len(FEATURE_OPTIONS)
            elif key == ord(' '):
                fk = FEATURE_OPTIONS[cursor][0]
                features_state[fk] = not features_state[fk]
            elif key in (curses.KEY_ENTER, 10, 13):
                page = 1
                cursor = 0
            elif key == 27:
                return None
        else:
            if key == ord(' '):
                dev_state = not dev_state
            elif key in (curses.KEY_ENTER, 10, 13):
                return features_state, dev_state
            elif key == 27:
                page = 0
                cursor = 0


def _page_summary(stdscr, answers, deps, dev_deps, cursor, scroll=0):
    _init_colors()
    stdscr.clear()
    max_y, max_x = stdscr.getmaxyx()

    db_names = {"sqlite": "SQLite", "mysql": "MySQL / MariaDB", "postgresql": "PostgreSQL"}
    feature_names = {
        "celery": "Celery",
        "redis": "Redis",
        "winrm": "WinRM",
        "kerberos": "Kerberos",
        "markdown": "Markdown",
        "2fa": "2FA",
    }

    lines = []
    lines.append(("title", " 部署摘要 "))
    lines.append(("blank", ""))
    lines.append(("kv", f"  数据库:     {db_names[answers['db']]}"))

    active_features = [feature_names[k] for k in ("celery", "redis", "winrm", "kerberos", "markdown", "2fa") if answers.get(k)]
    if active_features:
        lines.append(("kv", f"  功能模块:   {', '.join(active_features)}"))
    else:
        lines.append(("kv", "  功能模块:   无（仅核心框架）"))

    if answers.get("dev"):
        lines.append(("kv", "  开发工具:   已启用"))
    else:
        lines.append(("kv", "  开发工具:   未启用"))

    lines.append(("blank", ""))
    lines.append(("dep_title", f"  生产依赖 ({len(deps)} 个):"))
    for name, spec in deps.items():
        lines.append(("dep", f"    + {spec}"))

    if dev_deps:
        lines.append(("blank", ""))
        lines.append(("dep_dev_title", f"  开发依赖 ({len(dev_deps)} 个):"))
        for name, spec in dev_deps.items():
            lines.append(("dep_dev", f"    + {spec}"))

    total = len(deps) + len(dev_deps)
    lines.append(("blank", ""))
    lines.append(("total", f"  合计: {total} 个直接依赖（传递依赖由 uv 自动解析）"))

    box_w = min(76, max_x - 4)
    box_h = min(len(lines) + 4, max_y - 6)
    box_x = max(0, (max_x - box_w) // 2)
    box_y = 1

    _draw_banner(stdscr, 0, max_x)
    _draw_box(stdscr, box_y, box_x, box_h, box_w)

    max_visible = box_h - 3
    total_lines = len(lines)
    max_scroll = max(0, total_lines - max_visible)
    scroll = min(scroll, max_scroll)
    scroll = max(0, scroll)

    visible = lines[scroll:scroll + max_visible]
    for i, (kind, text) in enumerate(visible):
        ry = box_y + 1 + i
        rx = box_x + 2
        remaining = box_w - 5
        t = text[:remaining]

        if kind == "title":
            tx = box_x + max(0, (box_w - len(t)) // 2)
            _safe_addstr(stdscr, ry, tx, t, curses.color_pair(C_TITLE) | curses.A_BOLD)
        elif kind == "blank":
            pass
        elif kind == "kv":
            _safe_addstr(stdscr, ry, rx, t, curses.color_pair(C_SUBTITLE) | curses.A_BOLD)
        elif kind == "dep_title":
            _safe_addstr(stdscr, ry, rx, t, curses.color_pair(C_DEP) | curses.A_BOLD)
        elif kind == "dep":
            _safe_addstr(stdscr, ry, rx, t, curses.color_pair(C_DEP))
        elif kind == "dep_dev_title":
            _safe_addstr(stdscr, ry, rx, t, curses.color_pair(C_DEP_DEV) | curses.A_BOLD)
        elif kind == "dep_dev":
            _safe_addstr(stdscr, ry, rx, t, curses.color_pair(C_DEP_DEV))
        elif kind == "total":
            _safe_addstr(stdscr, ry, rx, t, curses.color_pair(C_TITLE) | curses.A_BOLD)

    if max_scroll > 0:
        scroll_info = f" [{scroll + 1}-{min(scroll + max_visible, total_lines)}/{total_lines}] "
        _safe_addstr(stdscr, box_y + box_h - 2, box_x + box_w - len(scroll_info) - 2, scroll_info, curses.color_pair(C_DESC))

    btn_y = box_y + box_h + 1
    btn_labels = ["[✔ 确认生成]", "[✘ 取消]"]
    btn_x = box_x + 4
    for i, label in enumerate(btn_labels):
        if i == cursor:
            _safe_addstr(stdscr, btn_y, btn_x, label, curses.color_pair(C_HIGHLIGHT) | curses.A_BOLD)
        else:
            _safe_addstr(stdscr, btn_y, btn_x, label, curses.color_pair(C_UNSELECTED))
        btn_x += len(label) + 3

    hint_y = btn_y + 2
    hint = "←→ 选择  Enter 确认  Esc 返回"
    if max_scroll > 0:
        hint = "↑↓ 滚动  " + hint
    _draw_hint(stdscr, hint_y, box_x + 2, hint)

    stdscr.refresh()
    return scroll


def _confirm_summary(stdscr, answers, deps, dev_deps):
    cursor = 0
    scroll = 0
    while True:
        scroll = _page_summary(stdscr, answers, deps, dev_deps, cursor, scroll)
        key = stdscr.getch()
        if key == curses.KEY_LEFT:
            cursor = 0
        elif key == curses.KEY_RIGHT:
            cursor = 1
        elif key == curses.KEY_UP:
            scroll = max(0, scroll - 1)
        elif key == curses.KEY_DOWN:
            scroll += 1
        elif key in (curses.KEY_ENTER, 10, 13):
            return cursor == 0
        elif key == 27:
            return None
        elif key == ord('1'):
            return True
        elif key == ord('2'):
            return False


def _page_progress(stdscr, step, total_steps, message):
    _init_colors()
    stdscr.clear()
    max_y, max_x = stdscr.getmaxyx()

    _draw_banner(stdscr, 0, max_x)

    box_w = min(60, max_x - 4)
    box_h = 5
    box_x = max(0, (max_x - box_w) // 2)
    box_y = 3

    _draw_box(stdscr, box_y, box_x, box_h, box_w)

    title = f" Step {step}/{total_steps} "
    tx = box_x + max(0, (box_w - len(title)) // 2)
    _safe_addstr(stdscr, box_y, tx, title, curses.color_pair(C_TITLE) | curses.A_BOLD)

    msg_x = box_x + 3
    _safe_addstr(stdscr, box_y + 2, msg_x, message[:box_w - 6], curses.color_pair(C_SUBTITLE))

    stdscr.refresh()


def _page_result(stdscr, success, answers, backup_name=None):
    _init_colors()
    stdscr.clear()
    max_y, max_x = stdscr.getmaxyx()

    _draw_banner(stdscr, 0, max_x)

    box_w = min(72, max_x - 4)
    box_x = max(0, (max_x - box_w) // 2)
    box_y = 2

    if success:
        title = " ✔ 部署完成 "
        steps = [
            "1. 配置 .env 文件          (参考 .env.example)",
            "2. 初始化数据库            uv run python manage.py migrate",
            "3. 创建管理员              uv run python manage.py createsuperuser",
            "4. 启动服务                uv run python manage.py runserver",
        ]
        if answers.get("celery"):
            steps.append("5. 启动 Celery             uv run celery -A config worker -l info")

        box_h = 4 + len(steps) + (2 if not answers.get("redis") and answers.get("celery") else 0) + (1 if backup_name else 0)
        box_h = max(box_h, 8)

        _draw_box(stdscr, box_y, box_x, box_h, box_w)
        _safe_addstr(stdscr, box_y, box_x + max(0, (box_w - len(title)) // 2), title, curses.color_pair(C_SUCCESS) | curses.A_BOLD)

        for i, step in enumerate(steps):
            ry = box_y + 2 + i
            _safe_addstr(stdscr, ry, box_x + 3, step[:box_w - 6], curses.color_pair(C_SUBTITLE))

        row = box_y + 2 + len(steps)
        if not answers.get("redis") and answers.get("celery"):
            _safe_addstr(stdscr, row, box_x + 3, "⚠ Celery 使用 SQLite Broker，生产环境建议启用 Redis", curses.color_pair(C_WARN))
            row += 2

        if backup_name:
            _safe_addstr(stdscr, row, box_x + 3, f"备份: {backup_name}", curses.color_pair(C_DESC))
    else:
        box_h = 8
        _draw_box(stdscr, box_y, box_x, box_h, box_w)
        title = " ✘ 部署失败 "
        _safe_addstr(stdscr, box_y, box_x + max(0, (box_w - len(title)) // 2), title, curses.color_pair(C_ERROR) | curses.A_BOLD)
        _safe_addstr(stdscr, box_y + 2, box_x + 3, "依赖同步失败，请检查错误信息", curses.color_pair(C_ERROR))
        if backup_name:
            _safe_addstr(stdscr, box_y + 4, box_x + 3, f"恢复: cp {backup_name} pyproject.toml", curses.color_pair(C_WARN))

    hint_y = box_y + box_h + 1
    _draw_hint(stdscr, hint_y, box_x + 2, "按任意键退出")

    stdscr.refresh()
    stdscr.getch()


def _tui_main(stdscr):
    curses.curs_set(0)
    curses.noecho()
    stdscr.keypad(True)
    _init_colors()

    db = _select_db(stdscr)
    if db is None:
        return

    result = _select_features(stdscr)
    if result is None:
        return
    features_state, dev_state = result

    answers = {"db": db}
    answers.update(features_state)
    answers["dev"] = dev_state

    deps, dev_deps = compute_dependencies(answers)

    confirmed = _confirm_summary(stdscr, answers, deps, dev_deps)
    if confirmed is None or not confirmed:
        return

    toml_path = BASE_DIR / "pyproject.toml"
    backup = backup_file(toml_path)
    backup_name = backup.name if backup else None

    _page_progress(stdscr, 1, 2, "正在生成 pyproject.toml ...")
    content = generate_pyproject_toml(answers, deps, dev_deps)
    toml_path.write_text(content, encoding="utf-8")

    _page_progress(stdscr, 2, 2, "正在执行 uv sync ...")
    try:
        proc = subprocess.run(
            ["uv", "sync"],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=300,
        )
        success = proc.returncode == 0
    except FileNotFoundError:
        success = False
    except subprocess.TimeoutExpired:
        success = False

    _page_result(stdscr, success, answers, backup_name)


def compute_dependencies(answers):
    deps = dict(DEPS_CORE)

    if answers.get("celery"):
        deps.update(DEPS_CELERY)

    if answers["db"] == "mysql":
        deps.update(DEPS_MYSQL)
    elif answers["db"] == "postgresql":
        deps.update(DEPS_POSTGRESQL)

    if answers.get("redis"):
        deps.update(DEPS_REDIS)

    if answers.get("celery") and not answers.get("redis"):
        deps.update(DEPS_SQLITE_BROKER)

    if answers.get("winrm"):
        deps.update(DEPS_WINRM)

    if answers.get("kerberos"):
        deps.update(DEPS_KERBEROS)

    if answers.get("markdown"):
        deps.update(DEPS_MARKDOWN)

    if answers.get("2fa"):
        deps.update(DEPS_2FA)

    dev_deps = dict(DEPS_DEV) if answers.get("dev") else {}

    return deps, dev_deps


def generate_pyproject_toml(answers, deps, dev_deps):
    lines = []

    lines.append("[project]")
    lines.append('name = "2c2a"')
    lines.append('version = "1.0.0"')
    lines.append('description = "2c2a - Django Web Application"')
    lines.append('license = "AGPL-3.0-only"')
    lines.append('readme = "README.md"')
    lines.append('requires-python = ">=3.10"')

    sorted_deps = sorted(deps.values(), key=_dep_sort_key)
    lines.append("dependencies = [")
    for spec in sorted_deps:
        lines.append(f'    "{spec}",')
    lines.append("]")

    optional_groups = {}
    if not answers.get("redis"):
        optional_groups["redis"] = sorted(DEPS_REDIS.values())
    if not answers.get("kerberos"):
        optional_groups["kerberos"] = sorted(DEPS_KERBEROS.values())
    if not answers.get("winrm"):
        optional_groups["winrm"] = sorted(DEPS_WINRM.values())

    if optional_groups:
        lines.append("")
        lines.append("[project.optional-dependencies]")
        for group_name, group_deps in optional_groups.items():
            lines.append(f"{group_name} = [")
            for spec in group_deps:
                lines.append(f'    "{spec}",')
            lines.append("]")

    lines.append("")
    lines.append("[build-system]")
    lines.append('requires = ["hatchling"]')
    lines.append('build-backend = "hatchling.build"')

    if dev_deps:
        lines.append("")
        lines.append("[dependency-groups]")
        lines.append("dev = [")
        for spec in sorted(dev_deps.values()):
            lines.append(f'    "{spec}",')
        lines.append("]")

    lines.append("")
    lines.append("[tool.hatch.metadata]")
    lines.append("allow-direct-references = true")

    lines.append("")
    lines.append("[tool.hatch.build.targets.wheel]")
    lines.append('packages = ["."]')

    lines.append("")
    lines.append("[tool.pyright]")
    lines.append('venvPath = "."')
    lines.append('venv = ".venv"')
    lines.append('pythonVersion = "3.13"')
    lines.append('typeCheckingMode = "basic"')

    lines.append("")
    lines.append("[tool.pyrefly]")
    lines.append('python-version = "3.13"')

    lines.append("")
    return "\n".join(lines)


def _dep_sort_key(spec):
    if "@" in spec:
        return (1, spec.lower())
    return (0, spec.lower())


def backup_file(path):
    if not path.exists():
        return None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_name(f"{path.stem}.bak.{ts}{path.suffix}")
    shutil.copy2(path, backup)
    return backup


def main():
    if not sys.stdin.isatty():
        print("错误: 此脚本需要交互式终端")
        sys.exit(1)

    try:
        curses.wrapper(_tui_main)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
