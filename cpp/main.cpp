#include <windows.h>
#include <string>
#include <vector>
#include <iostream>
#include <cwctype>
#include <algorithm>

#define SERVICE_NAME "DjangoGuardSvc"
#define DISPLAY_NAME "Django Environment Guard Service"

// 全局变量
SERVICE_STATUS        g_ServiceStatus = {0};
SERVICE_STATUS_HANDLE g_StatusHandle = NULL;
HANDLE                g_ServiceStopEvent = INVALID_HANDLE_VALUE;
std::string           g_Port = "8000";

// 函数声明
void ShowMessage(const std::string& title, const std::string& msg, UINT type);
bool IsNumber(const std::string& s);
DWORD GetServiceState();
void InstallAndStartService(const std::string& port);
void StopAndUninstallService();
void HandleControlCommand(const std::string& action, const std::string& port);
void HandlePassthrough(const std::vector<std::string>& args);
void HandleInit();

// 服务内部函数
void ServiceMain(DWORD argc, LPTSTR* argv);
void ServiceCtrlHandler(DWORD CtrlCode);
void WorkerThread();
DWORD RunCommand(const std::string& cmd, bool isProtected = false);
void RefreshEnvironment();
PSECURITY_DESCRIPTOR CreateProtectedSD();

// 环境与进程创建
LPVOID CreateChinaMirrorEnvBlock();
void FreeEnvBlock(LPVOID env);
BOOL ExecuteCommand(const std::string& cmd, DWORD flags, bool isProtected, LPHANDLE hProcessOut = NULL);

// ==========================================================
// 工具函数
// ==========================================================
void ShowMessage(const std::string& title, const std::string& msg, UINT type = MB_OK) {
    MessageBoxA(NULL, msg.c_str(), title.c_str(), type | MB_TOPMOST);
}

bool IsNumber(const std::string& s) {
    if (s.empty()) return false;
    for (char c : s) if (!std::isdigit(c)) return false;
    return true;
}

DWORD GetServiceState() {
    SC_HANDLE scm = OpenSCManagerA(NULL, NULL, SC_MANAGER_CONNECT);
    if (!scm) return SERVICE_STOPPED;
    SC_HANDLE svc = OpenServiceA(scm, SERVICE_NAME, SERVICE_QUERY_STATUS);
    if (!svc) { CloseServiceHandle(scm); return SERVICE_STOPPED; }
    SERVICE_STATUS status;
    if (QueryServiceStatus(svc, &status)) { CloseServiceHandle(svc); CloseServiceHandle(scm); return status.dwCurrentState; }
    CloseServiceHandle(svc); CloseServiceHandle(scm);
    return SERVICE_STOPPED;
}

// ==========================================================
// 零信任安全：拒绝普通用户终止
// ==========================================================
PSECURITY_DESCRIPTOR CreateProtectedSD() {
    PACL pACL = NULL;
    PSECURITY_DESCRIPTOR pSD = (PSECURITY_DESCRIPTOR)LocalAlloc(LPTR, SECURITY_DESCRIPTOR_MIN_LENGTH);
    if (!pSD || !InitializeSecurityDescriptor(pSD, SECURITY_DESCRIPTOR_REVISION)) return NULL;
    EXPLICIT_ACCESS ea[3]; ZeroMemory(ea, sizeof(ea));
    
    ea[0].grfAccessPermissions = PROCESS_TERMINATE; ea[0].grfAccessMode = DENY_ACCESS;
    ea[0].grfInheritance = NO_INHERITANCE; ea[0].Trustee.TrusteeForm = TRUSTEE_IS_NAME;
    ea[0].Trustee.TrusteeType = TRUSTEE_IS_GROUP; ea[0].Trustee.ptstrName = (LPTSTR)"INTERACTIVE";

    ea[1].grfAccessPermissions = PROCESS_ALL_ACCESS; ea[1].grfAccessMode = SET_ACCESS;
    ea[1].grfInheritance = NO_INHERITANCE; ea[1].Trustee.TrusteeForm = TRUSTEE_IS_NAME;
    ea[1].Trustee.TrusteeType = TRUSTEE_IS_WELL_KNOWN_GROUP; ea[1].Trustee.ptstrName = (LPTSTR)"SYSTEM";

    ea[2].grfAccessPermissions = PROCESS_ALL_ACCESS; ea[2].grfAccessMode = SET_ACCESS;
    ea[2].grfInheritance = NO_INHERITANCE; ea[2].Trustee.TrusteeForm = TRUSTEE_IS_NAME;
    ea[2].Trustee.TrusteeType = TRUSTEE_IS_WELL_KNOWN_GROUP; ea[2].Trustee.ptstrName = (LPTSTR)"Administrators";

    if (SetEntriesInAcl(3, ea, NULL, &pACL) != ERROR_SUCCESS) return NULL;
    SetSecurityDescriptorDacl(pSD, TRUE, pACL, FALSE);
    return pSD;
}

// ==========================================================
// 核心新增：构建【全链路】国内镜像环境变量块
// ==========================================================
LPVOID CreateChinaMirrorEnvBlock() {
    LPCH parentEnv = GetEnvironmentStrings();
    std::string envBlock;
    
    // 遍历当前环境变量，剔除已有的 uv 相关配置防止冲突
    for (LPCH p = parentEnv; *p; p += strlen(p) + 1) {
        std::string entry = p;
        if (entry.find("UV_INDEX_URL=") == 0 || entry.find("UV_EXTRA_INDEX_URL=") == 0) continue;
        if (entry.find("UV_PYTHON_INSTALL_MIRROR=") == 0) continue;
        if (entry.find("UV_INSTALLER_GITHUB_BASE_URL=") == 0) continue;
        
        envBlock += entry + '\0';
    }
    FreeEnvironmentStrings(parentEnv);

    // 强制注入全链路加速镜像
    // 1. uv 本体下载加速 (通过 GitHub 代理)
    envBlock += "UV_INSTALLER_GITHUB_BASE_URL=https://ghfast.top/https://github.com/\0";
    // 2. Python 解释器下载加速
    envBlock += "UV_PYTHON_INSTALL_MIRROR=https://mirrors.tuna.tsinghua.edu.cn/python/\0";
    // 3. pip 依赖包下载加速
    envBlock += "UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple\0";
    
    envBlock += '\0'; // 环境块结尾

    LPVOID envMem = LocalAlloc(LPTR, envBlock.length());
    if (envMem) memcpy(envMem, envBlock.c_str(), envBlock.length());
    return envMem;
}

void FreeEnvBlock(LPVOID env) { if (env) LocalFree(env); }

// ==========================================================
// 统一底层进程创建 (强制注入环境变量)
// ==========================================================
BOOL ExecuteCommand(const std::string& cmd, DWORD flags, bool isProtected, LPHANDLE hProcessOut) {
    STARTUPINFOA si; PROCESS_INFORMATION pi;
    ZeroMemory(&si, sizeof(si)); si.cb = sizeof(si);
    if (flags & CREATE_NO_WINDOW) { si.dwFlags = STARTF_USESHOWWINDOW; si.wShowWindow = SW_HIDE; }
    ZeroMemory(&pi, sizeof(pi));

    SECURITY_ATTRIBUTES sa = {0}; PSECURITY_DESCRIPTOR pSD = NULL;
    if (isProtected) {
        pSD = CreateProtectedSD();
        if (pSD) { sa.nLength = sizeof(SECURITY_ATTRIBUTES); sa.lpSecurityDescriptor = pSD; sa.bInheritHandle = FALSE; }
    }

    LPVOID envBlock = CreateChinaMirrorEnvBlock();
    char* cmdBuf = new char[cmd.length() + 1]; strcpy_s(cmdBuf, cmd.length() + 1, cmd.c_str());

    BOOL success = CreateProcessA(NULL, cmdBuf, isProtected ? &sa : NULL, NULL, FALSE, flags, envBlock, NULL, &si, &pi);
    
    delete[] cmdBuf;
    FreeEnvBlock(envBlock);
    if (pSD) LocalFree(pSD);

    if (success) {
        CloseHandle(pi.hThread);
        if (hProcessOut) *hProcessOut = pi.hProcess; else CloseHandle(pi.hProcess);
    }
    return success;
}

// ==========================================================
// 核心指令处理 (无变化)
// ==========================================================
void InstallAndStartService(const std::string& port) {
    char exePath[MAX_PATH]; GetModuleFileNameA(NULL, exePath, MAX_PATH);
    std::string cmdLine = std::string("\"") + exePath + "\" --run " + port;
    SC_HANDLE schSCManager = OpenSCManagerA(NULL, NULL, SC_MANAGER_ALL_ACCESS);
    if (!schSCManager) { ShowMessage("错误", "无法打开服务控制管理器，请确保以管理员身份运行。", MB_ICONERROR); return; }

    SC_HANDLE schService = CreateServiceA(schSCManager, SERVICE_NAME, DISPLAY_NAME, SERVICE_ALL_ACCESS, SERVICE_WIN32_OWN_PROCESS, SERVICE_AUTO_START, SERVICE_ERROR_IGNORE, cmdLine.c_str(), NULL, NULL, NULL, NULL, NULL);
    if (!schService && GetLastError() == ERROR_SERVICE_EXISTS) {
        schService = OpenServiceA(schSCManager, SERVICE_NAME, SERVICE_ALL_ACCESS);
        ChangeServiceConfigA(schService, SERVICE_WIN32_OWN_PROCESS, SERVICE_AUTO_START, SERVICE_ERROR_IGNORE, cmdLine.c_str(), NULL, NULL, NULL, NULL, NULL, NULL);
    }
    if (schService) {
        std::string dir = exePath; dir = dir.substr(0, dir.find_last_of("\\"));
        std::string icaclsCmd = "icacls \"" + dir + "\" /deny \"Users:(OI)(CI)(DE,DC)\" /deny \"INTERACTIVE:(OI)(CI)(DE,DC)\" /T /C /Q";
        WinExec(icaclsCmd.c_str(), SW_HIDE);
        StartServiceA(schService, 0, NULL);
        ShowMessage("成功", "服务已启动并在后台守护运行。", MB_ICONINFORMATION);
        CloseServiceHandle(schService);
    } else { ShowMessage("错误", "无法创建或打开服务。", MB_ICONERROR); }
    CloseServiceHandle(schSCManager);
}

void StopAndUninstallService() {
    SC_HANDLE scm = OpenSCManagerA(NULL, NULL, SC_MANAGER_ALL_ACCESS); if (!scm) return;
    SC_HANDLE svc = OpenServiceA(scm, SERVICE_NAME, SERVICE_STOP | DELETE);
    if (svc) {
        SERVICE_STATUS status; ControlService(svc, SERVICE_CONTROL_STOP, &status);
        while (GetServiceState() != SERVICE_STOPPED) Sleep(500);
        DeleteService(svc); CloseHandle(svc);
        ShowMessage("成功", "服务已停止并卸载。", MB_ICONINFORMATION);
    } else { ShowMessage("提示", "服务未运行或未安装。", MB_ICONINFORMATION); }
    CloseServiceHandle(scm);
}

void HandleControlCommand(const std::string& action, const std::string& port) {
    if (action == "stop") { StopAndUninstallService(); return; }
    if (action == "restart") { StopAndUninstallService(); while (GetServiceState() != SERVICE_STOPPED) Sleep(200); InstallAndStartService(port); return; }
    
    if (action == "start") {
        DWORD state = GetServiceState();
        if (state == SERVICE_RUNNING) {
            std::string msg = "检测到服务已在运行。\n\n【是】：关闭现有服务并重新启动。\n【否】：忽略警告，单开一个黑框前台运行(用于多端口调试，不守护)。\n【取消】：放弃操作。";
            int res = ShowMessage("冲突警告", msg, MB_YESNOCANCEL | MB_ICONWARNING);
            if (res == IDYES) { StopAndUninstallService(); while (GetServiceState() != SERVICE_STOPPED) Sleep(200); InstallAndStartService(port); return; }
            else if (res == IDNO) { ExecuteCommand("uv run python manage.py runserver " + port, CREATE_NEW_CONSOLE, false); return; }
            else return;
        } else { InstallAndStartService(port); }
    }
}

// ==========================================================
// 透传模式执行 (单开黑框，全链路国内源)
// ==========================================================
void HandlePassthrough(const std::vector<std::string>& args) {
    std::string fullCmd = "uv run python manage.py";
    for (const auto& arg : args) fullCmd += " " + arg;
    if (!ExecuteCommand(fullCmd, CREATE_NEW_CONSOLE, false)) {
        ShowMessage("执行出错", "无法启动进程，请检查 uv 和 python 环境。", MB_ICONERROR);
    }
}

// ==========================================================
// init 初始化环境 (全链路国内源)
// ==========================================================
void HandleInit() {
    // 这里的 where uv 和 powershell 安装都会继承强制注入的环境变量
    if (RunCommand("where uv") != 0) {
        ShowMessage("提示", "未检测到 uv，正在通过国内代理自动安装...", MB_ICONINFORMATION);
        if (RunCommand("powershell -ExecutionPolicy ByPass -NoProfile -Command \"irm https://astral.sh/uv/install.ps1 | iex\"") != 0) {
            ShowMessage("错误", "uv 安装失败。可能是 GitHub 代理失效，请尝试手动安装 uv。", MB_ICONERROR); return;
        }
        RefreshEnvironment();
    }
    
    ShowMessage("提示", "即将弹出黑框执行 uv sync...\n(Python解释器和依赖包均使用国内镜像加速)", MB_ICONINFORMATION);
    
    HANDLE hProcess = NULL;
    if (ExecuteCommand("uv sync", CREATE_NEW_CONSOLE, false, &hProcess)) {
        WaitForSingleObject(hProcess, INFINITE);
        DWORD exitCode; GetExitCodeProcess(hProcess, &exitCode);
        CloseHandle(hProcess);
        if (exitCode == 0) ShowMessage("成功", "环境初始化 完成。", MB_ICONINFORMATION);
        else ShowMessage("警告", "uv sync 执行异常，请查看弹出的黑框日志。", MB_ICONWARNING);
    } else { ShowMessage("错误", "无法执行 uv sync。", MB_ICONERROR); }
}

// ==========================================================
// 服务内部核心逻辑 (无交互，静默运行，全链路国内源)
// ==========================================================
DWORD RunCommand(const std::string& cmd, bool isProtected) {
    HANDLE hProcess = NULL;
    if (!ExecuteCommand(cmd, CREATE_NO_WINDOW, isProtected, &hProcess)) return GetLastError();
    WaitForSingleObject(hProcess, INFINITE);
    DWORD exitCode = 0; GetExitCodeProcess(hProcess, &exitCode);
    CloseHandle(hProcess);
    return exitCode;
}

void RefreshEnvironment() { SendMessageTimeout(HWND_BROADCAST, WM_SETTINGCHANGE, 0, (LPARAM)"Environment", SMTO_ABORTIFHUNG, 5000, NULL); }

void WorkerThread() {
    if (RunCommand("where uv") != 0) {
        if (RunCommand("powershell -ExecutionPolicy ByPass -NoProfile -Command \"irm https://astral.sh/uv/install.ps1 | iex\"") != 0) return;
        RefreshEnvironment();
    }
    if (RunCommand("uv sync", true) != 0) return;

    std::string serverCmd = "uv run python manage.py runserver " + g_Port;
    while (WaitForSingleObject(g_ServiceStopEvent, 0) == WAIT_TIMEOUT) {
        HANDLE hProcess = NULL;
        if (ExecuteCommand(serverCmd, CREATE_NO_WINDOW, true, &hProcess)) {
            HANDLE handles[2] = { hProcess, g_ServiceStopEvent };
            WaitForMultipleObjects(2, handles, FALSE, INFINITE);
            CloseHandle(hProcess);
        }
        if (WaitForSingleObject(g_ServiceStopEvent, 0) == WAIT_TIMEOUT) Sleep(3000);
    }
}

void ServiceCtrlHandler(DWORD CtrlCode) {
    if (CtrlCode == SERVICE_CONTROL_STOP) { g_ServiceStatus.dwCurrentState = SERVICE_STOP_PENDING; SetServiceStatus(g_StatusHandle, &g_ServiceStatus); SetEvent(g_ServiceStopEvent); }
}

void ServiceMain(DWORD argc, LPTSTR* argv) {
    g_StatusHandle = RegisterServiceCtrlHandlerA(SERVICE_NAME, ServiceCtrlHandler);
    g_ServiceStopEvent = CreateEvent(NULL, TRUE, FALSE, NULL);
    g_ServiceStatus.dwServiceType = SERVICE_WIN32_OWN_PROCESS; g_ServiceStatus.dwCurrentState = SERVICE_START_PENDING;
    SetServiceStatus(g_StatusHandle, &g_ServiceStatus);
    g_ServiceStatus.dwCurrentState = SERVICE_RUNNING;
    SetServiceStatus(g_StatusHandle, &g_ServiceStatus);
    WorkerThread();
    CloseHandle(g_ServiceStopEvent);
    g_ServiceStatus.dwCurrentState = SERVICE_STOPPED;
    SetServiceStatus(g_StatusHandle, &g_ServiceStatus);
}

// ==========================================================
// 主入口：路由分发
// ==========================================================
int main(int argc, char* argv[]) {
    if (argc > 1 && std::string(argv[1]) == "--run") {
        g_Port = (argc > 2) ? argv[2] : "8000";
        SERVICE_TABLE_ENTRYA ServiceTable[] = { {(LPSTR)SERVICE_NAME, (LPSERVICE_MAIN_FUNCTIONA)ServiceMain}, {NULL, NULL} };
        StartServiceCtrlDispatcherA(ServiceTable);
        return 0;
    }

    std::string action = "start"; std::string port = "8000"; std::vector<std::string> passthrough_args;
    if (argc > 1) {
        std::string arg1 = argv[1];
        if (IsNumber(arg1)) { port = arg1; }
        else if (arg1 == "start" || arg1 == "restart") { if (argc > 2 && IsNumber(argv[2])) port = argv[2]; }
        else if (arg1 == "stop" || arg1 == "init") { /* 不处理端口 */ }
        else { action = "passthrough"; passthrough_args.assign(argv + 1, argv + argc); }
    }

    if (action == "stop") StopAndUninstallService();
    else if (action == "start" || action == "restart") HandleControlCommand(action, port);
    else if (action == "init") HandleInit();
    else if (action == "passthrough") HandlePassthrough(passthrough_args);

    return 0;
}
