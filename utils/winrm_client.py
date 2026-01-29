# Winrm客户端工具
"""
Winrm客户端封装模块

该模块提供了与Windows远程管理（WinRM）服务交互的客户端实现，
用于执行远程命令和PowerShell脚本。

主要功能：
- 建立和管理WinRM会话
- 执行远程命令和PowerShell脚本
- 管理远程用户账户
- 提供连接重试和超时处理

使用示例：
    client = WinrmClient("hostname", "username", "password")
    result = client.execute_command("ipconfig")
    if result.success:
        print(result.std_out)
"""
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any
from winrm import Session
from winrm.exceptions import InvalidCredentialsError
from django.conf import settings
import socket
import time

logger = logging.getLogger("zasca")


@dataclass
class WinrmResult:
    """
    WinRM执行结果的数据类

    属性:
        status_code: 命令执行的状态码，0表示成功
        std_out: 标准输出内容
        std_err: 标准错误内容
        success: 命令是否执行成功的布尔值
    """
    status_code: int
    std_out: str
    std_err: str

    @property
    def success(self) -> bool:
        """判断命令是否执行成功"""
        return self.status_code == 0


class WinrmClient:
    """
    WinRM客户端封装类

    该类封装了与WinRM服务交互的核心功能，包括会话管理、命令执行、
    PowerShell脚本执行和用户管理等操作。

    属性:
        hostname: 主机名或IP地址
        username: 登录用户名
        password: 登录密码
        port: WinRM服务端口，默认为5985
        use_ssl: 是否使用SSL连接，默认为False
        timeout: 操作超时时间（秒）
        max_retries: 最大重试次数
        endpoint: WinRM服务端点URL
        session: WinRM会话对象
    """

    def __init__(
            self,
            hostname: str,
            username: str,
            password: str,
            port: int = 5985,
            use_ssl: bool = False,
            timeout: Optional[int] = None,
            max_retries: Optional[int] = None
    ):
        """
        初始化WinRM客户端

        参数:
            hostname: 主机名或IP地址
            username: 登录用户名
            password: 登录密码
            port: WinRM服务端口，默认为5985
            use_ssl: 是否使用SSL连接，默认为False
            timeout: 操作超时时间（秒），默认使用配置文件中的值
            max_retries: 最大重试次数，默认使用配置文件中的值
        """
        # 检查主机名是否包含端口（例如 "hostname:port" 或 "ip:port" 格式）
        if ':' in hostname and not hostname.startswith('http'):
            # 分离主机名和端口
            parts = hostname.split(':', 1)
            if len(parts) == 2 and parts[1].isdigit():
                # 提取主机名和端口
                actual_hostname = parts[0]
                actual_port = int(parts[1])
                # 更新实例变量
                self.hostname = actual_hostname
                # 如果没有显式指定端口，则使用从主机名中提取的端口
                if port == 5985:  # 5985是默认WinRM端口
                    self.port = actual_port
                else:
                    # 如果已显式指定端口，则使用指定的端口
                    self.port = port
            else:
                self.hostname = hostname
                self.port = port
        else:
            self.hostname = hostname
            self.port = port
        
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self.timeout = timeout or settings.WINRM_TIMEOUT
        self.max_retries = max_retries or settings.WINRM_MAX_RETRIES
        protocol = 'https' if self.use_ssl else 'http'
        self.endpoint = f'{protocol}://{self.hostname}:{self.port}/wsman'

        # 验证主机可达性
        if not self._validate_hostname():
            raise ValueError(f"主机名无法解析: {self.hostname}")

        # 初始化会话对象
        self.session = Session(
            self.endpoint,
            auth=(self.username, self.password),
            transport='basic',
            server_cert_validation='ignore',
            # 设置连接超时
            operation_timeout_sec=self.timeout,
            read_timeout_sec=self.timeout + 10
        )

        logger.info(
            f"初始化WinRM客户端: 主机={self.hostname}, 端口={self.port}, "
            f"SSL={use_ssl}, 超时={self.timeout}秒, 最大重试={self.max_retries}次"
        )

    def _validate_hostname(self) -> bool:
        """
        验证主机名是否可以解析
        
        Returns:
            bool: 如果主机名可以解析则返回True，否则返回False
        """
        try:
            # 尝试解析主机名
            socket.gethostbyname(self.hostname)
            return True
        except socket.gaierror:
            logger.error(f"无法解析主机名: {self.hostname}:{self.port}")
            return False
        except Exception as e:
            logger.error(f"验证主机名时发生未知错误: {str(e)}")
            return False

    def execute_command(
            self,
            command: str,
            arguments: Optional[list] = None
    ) -> WinrmResult:
        """
        执行远程命令

        参数:
            command: 要执行的命令
            arguments: 命令参数列表

        返回:
            WinrmResult对象，包含执行结果

        异常:
            Exception: 当所有重试尝试都失败时抛出
        """
        import os
        # 如果是DEMO模式，模拟执行命令而不实际执行
        if os.environ.get('ZASCA_DEMO', '').lower() == '1':
            logger.info(f"DEMO模式: 模拟执行远程命令: {command}, 参数: {arguments}")
            # 模拟成功执行的结果
            return WinrmResult(
                status_code=0,
                std_out="Command executed successfully in demo mode",
                std_err=""
            )
        
        logger.info(f"执行远程命令: {command}, 参数: {arguments}")

        for attempt in range(self.max_retries):
            try:
                result = self.session.run_cmd(command, arguments or [])
                winrm_result = WinrmResult(
                    status_code=result.status_code,
                    std_out=result.std_out.decode('utf-8', errors='ignore'),
                    std_err=result.std_err.decode('utf-8', errors='ignore')
                )

                if winrm_result.success:
                    logger.info(f"命令执行成功: {command}")
                else:
                    logger.warning(
                        f"命令执行返回非零状态码: {command}, "
                        f"状态码={result.status_code}, 错误={winrm_result.std_err}"
                    )

                return winrm_result
            except Exception as e:
                # 检查是否是网络连接错误
                error_str = str(e)
                if "NameResolutionError" in error_str or "Failed to resolve" in error_str:
                    logger.error(f"主机名解析失败: {self.hostname}")
                    raise Exception(f'主机名解析失败: 无法解析主机名 "{self.hostname}". 请检查主机名拼写或网络连接.')
                
                logger.error(
                    f"命令执行失败 (尝试 {attempt + 1}/{self.max_retries}): "
                    f"{command}, 错误: {str(e)}"
                )

                if attempt == self.max_retries - 1:
                    logger.error(f"命令执行最终失败: {command}")
                    raise Exception(f'命令执行失败: {str(e)}')
                
                # 在重试之间等待一段时间
                time.sleep(1)

    def execute_powershell(
            self,
            script: str,
            arguments: Optional[Dict[str, Any]] = None
    ) -> WinrmResult:
        """
        执行PowerShell脚本

        参数:
            script: 要执行的PowerShell脚本
            arguments: 脚本参数字典

        返回:
            WinrmResult对象，包含执行结果

        异常:
            Exception: 当所有重试尝试都失败时抛出
        """
        import os
        # 如果是DEMO模式，模拟执行PowerShell而不实际执行
        if os.environ.get('ZASCA_DEMO', '').lower() == '1':
            logger.info(f"DEMO模式: 模拟执行PowerShell脚本: {script[:50]}...")
            # 模拟成功执行的结果
            return WinrmResult(
                status_code=0,
                std_out="PowerShell script executed successfully in demo mode",
                std_err=""
            )
        
        logger.info(f"执行PowerShell脚本: {script[:50]}...")

        for attempt in range(self.max_retries):
            try:
                result = self.session.run_ps(script)
                winrm_result = WinrmResult(
                    status_code=result.status_code,
                    std_out=result.std_out.decode('utf-8', errors='ignore'),
                    std_err=result.std_err.decode('utf-8', errors='ignore')
                )

                if winrm_result.success:
                    logger.info(f"PowerShell脚本执行成功")
                else:
                    logger.warning(
                        f"PowerShell脚本执行返回非零状态码: "
                        f"状态码={result.status_code}, 错误={winrm_result.std_err}"
                    )

                return winrm_result
            except Exception as e:
                # 检查是否是网络连接错误
                error_str = str(e)
                if "NameResolutionError" in error_str or "Failed to resolve" in error_str:
                    logger.error(f"主机名解析失败: {self.hostname}")
                    raise Exception(f'主机名解析失败: 无法解析主机名 "{self.hostname}". 请检查主机名拼写或网络连接.')
                
                logger.error(
                    f"PowerShell脚本执行失败 (尝试 {attempt + 1}/{self.max_retries}), "
                    f"错误: {str(e)}"
                )

                if attempt == self.max_retries - 1:
                    logger.error("PowerShell脚本执行最终失败")
                    raise Exception(f'PowerShell执行失败: {str(e)}')
                
                # 在重试之间等待一段时间
                time.sleep(1)

    def create_user(
            self,
            username: str,
            password: str,
            description: Optional[str] = None,
            group: Optional[str] = None
    ) -> WinrmResult:
        """
        创建本地用户

        参数:
            username: 用户名
            password: 密码
            description: 用户描述
            group: 要加入的用户组

        返回:
            WinrmResult对象，包含执行结果
        """
        desc = description or ''
        # 使用变量存储密码，避免在日志中暴露
        script = f'''
        $password = ConvertTo-SecureString "{password}" -AsPlainText -Force
        $user = New-LocalUser -Name "{username}" -Password $password -Description "{desc}" -ErrorAction Stop
        '''

        # 默认将用户添加到Users组，这是Windows系统必需的组
        default_group_script = f'''
        Add-LocalGroupMember -Group "Users" -Member "{username}" -ErrorAction Stop
        '''
        script += default_group_script
        
        # 如果指定了其他组，则也添加到该组
        if group:
            script += f'''
            Add-LocalGroupMember -Group "{group}" -Member "{username}" -ErrorAction Stop
            '''

        logger.info(f"创建用户: {username}, 组: {group}")
        result = self.execute_powershell(script)
        self.add_to_remote_users(username)

        if result.success:
            logger.info(f"用户创建成功: {username}")
        else:
            logger.error(f"用户创建失败: {username}, 错误: {result.std_err}")

        return result

    def create_user_with_reset_password_on_next_login(
            self,
            username: str,
            password: str,
            description: Optional[str] = None,
            group: Optional[str] = None
    ) -> WinrmResult:
        """
        创建本地用户并设置下次登录时修改密码

        参数:
            username: 用户名
            password: 密码
            description: 用户描述
            group: 要加入的用户组

        返回:
            WinrmResult对象，包含执行结果
        """
        desc = description or ''
        # 使用变量存储密码，避免在日志中暴露
        script = f'''
        $password = ConvertTo-SecureString "{password}" -AsPlainText -Force
        $user = New-LocalUser -Name "{username}" -Password $password -Description "{desc}" -ErrorAction Stop
        
        # 设置"下次登录必须修改密码"
        net user "{username}" /logonpasswordchg:YES
        '''

        # 默认将用户添加到Users组，这是Windows系统必需的组
        default_group_script = f'''
        Add-LocalGroupMember -Group "Users" -Member "{username}" -ErrorAction Stop
        '''
        script += default_group_script
        
        # 如果指定了其他组，则也添加到该组
        if group:
            script += f'''
            Add-LocalGroupMember -Group "{group}" -Member "{username}" -ErrorAction Stop
            '''

        logger.info(f"创建用户: {username}, 组: {group}, 并设置下次登录时修改密码")
        result = self.execute_powershell(script)
        self.add_to_remote_users(username)

        if result.success:
            logger.info(f"用户创建成功: {username}，下次登录时需修改密码")
        else:
            logger.error(f"用户创建失败: {username}, 错误: {result.std_err}")

        return result

    def delete_user(self, username: str) -> WinrmResult:
        """
        删除本地用户

        参数:
            username: 要删除的用户名

        返回:
            WinrmResult对象，包含执行结果
        """
        script = f'''
        Remove-LocalUser -Name "{username}" -ErrorAction Stop
        '''

        logger.info(f"删除用户: {username}")
        result = self.execute_powershell(script)

        if result.success:
            logger.info(f"用户删除成功: {username}")
        else:
            logger.error(f"用户删除失败: {username}, 错误: {result.std_err}")

        return result
    def enable_user(self, username: str) -> WinrmResult:
        """
        启用用户

        参数:
            username: 用户名

        返回:
            WinrmResult对象，包含执行结果
        """
        script = f'''
        Enable-LocalUser -Name "{username}" -ErrorAction Stop
        '''

        logger.info(f"启用用户: {username}")
        result = self.execute_powershell(script)

        if result.success:
            logger.info(f"用户启用成功: {username}")

    def disabled_user(self, username: str) -> WinrmResult:
        """
        禁用用户

        参数:
            username: 用户名

        返回:
            WinrmResult对象，包含执行结果
        """
        script = f'''
        Disable-LocalUser -Name "{username}" -ErrorAction Stop
        '''

        logger.info(f"禁用用户: {username}")
        result = self.execute_powershell(script)

        if result.success:
            logger.info(f"用户禁用成功: {username}")

    def get_user_info(self, username: str) -> WinrmResult:
        """
        获取本地用户信息

        参数:
            username: 用户名

        返回:
            WinrmResult对象，包含用户信息的JSON格式数据
        """
        script = f'''
        Get-LocalUser -Name "{username}" | ConvertTo-Json
        '''

        logger.info(f"获取用户信息: {username}")
        return self.execute_powershell(script)

    def list_users(self) -> WinrmResult:
        """
        列出所有本地用户

        返回:
            WinrmResult对象，包含用户列表的JSON格式数据
        """
        script = '''
        Get-LocalUser | ConvertTo-Json
        '''

        logger.info("列出所有本地用户")
        return self.execute_powershell(script)

    def check_user_exists(self, username: str) -> bool:
        """
        检查用户是否存在

        参数:
            username: 要检查的用户名

        返回:
            bool: 用户存在返回True，否则返回False
        """
        try:
            script = f'''
            $user = Get-LocalUser -Name "{username}" -ErrorAction Stop
            $true
            '''
            result = self.execute_powershell(script)
            exists = result.success and 'True' in result.std_out
            logger.info(f"检查用户是否存在: {username}, 结果: {exists}")
            return exists
        except Exception as e:
            logger.error(f"检查用户存在性时出错: {username}, 错误: {str(e)}")
            return False

    def get_password_policy(self) -> Dict[str, Any]:
        """
        动态获取密码策略要求

        返回:
            Dict: 包含密码策略信息的字典
        """
        try:
            script = f'''
            secedit /export /cfg "$env:TEMP\\secpol.cfg" | Out-Null
            Get-Content "$env:TEMP\\secpol.cfg" | Where-Object {{ $_ -match '^(MinimumPasswordLength|PasswordComplexity|PasswordHistorySize|MaximumPasswordAge|MinimumPasswordAge)\s*=' }}
            Remove-Item "$env:TEMP\\secpol.cfg" -ErrorAction SilentlyContinue
            '''
            result = self.execute_powershell(script)
            
            policy = {}
            if result.success:
                lines = result.std_out.strip().split("\n")
                for line in lines:
                    line = line.strip()
                    if line.startswith("MinimumPasswordLength"):
                        try:
                            policy["minimum_length"] = int(line.split("=")[1].strip())
                        except:
                            policy["minimum_length"] = 8  # 默认值
                    elif line.startswith("PasswordComplexity"):
                        try:
                            policy["complexity_required"] = bool(int(line.split("=")[1].strip()))
                        except:
                            policy["complexity_required"] = True  # 默认值
                    elif line.startswith("PasswordHistorySize"):
                        try:
                            policy["history_size"] = int(line.split("=")[1].strip())
                        except:
                            policy["history_size"] = 0  # 默认值
                    elif line.startswith("MaximumPasswordAge"):
                        try:
                            policy["max_age_days"] = int(line.split("=")[1].strip())
                        except:
                            policy["max_age_days"] = 0  # 默认值
                    elif line.startswith("MinimumPasswordAge"):
                        try:
                            policy["min_age_days"] = int(line.split("=")[1].strip())
                        except:
                            policy["min_age_days"] = 0  # 默认值
            
            # 设置默认值
            if "minimum_length" not in policy:
                policy["minimum_length"] = 8
            if "complexity_required" not in policy:
                policy["complexity_required"] = True
            
            logger.info(f"获取密码策略成功: {policy}")
            return policy
        except Exception as e:
            logger.error(f"获取密码策略失败: 错误: {str(e)}")
            # 返回默认密码策略
            return {
                "minimum_length": 8,
                "complexity_required": True,
                "history_size": 0,
                "max_age_days": 42,
                "min_age_days": 1
            }

    def generate_strong_password(self, length: Optional[int] = None) -> str:
        """
        根据密码策略生成强密码

        参数:
            length: 密码长度，默认根据服务器策略确定

        返回:
            str: 生成的强密码
        """
        import secrets
        import string
        
        # 获取服务器密码策略
        policy = self.get_password_policy()
        
        # 确定密码长度
        actual_length = length or max(policy["minimum_length"], 12)  # 默认至少12位
        
        if policy["complexity_required"]:
            # 密码复杂性要求：至少包含大写字母、小写字母、数字和特殊字符
            uppercase = secrets.choice(string.ascii_uppercase)
            lowercase = secrets.choice(string.ascii_lowercase)
            digit = secrets.choice(string.digits)
            special_char = secrets.choice("!@#$%^&*()_+-=[]{}|;:,.<>?")
            
            # 剩余部分随机生成
            remaining_length = max(0, actual_length - 4)
            alphabet = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|;:,.<>?"
            rest = "".join(secrets.choice(alphabet) for i in range(remaining_length))
            
            # 打乱顺序以确保安全
            password_chars = list(uppercase + lowercase + digit + special_char + rest)
            secrets.SystemRandom().shuffle(password_chars)
            password = "".join(password_chars)
        else:
            # 不需要复杂性要求，简单生成随机密码
            alphabet = string.ascii_letters + string.digits
            password = "".join(secrets.choice(alphabet) for i in range(actual_length))
        
        logger.info(f"生成强密码完成，长度: {len(password)}")
        return password
    def op_user(self, username: str) -> bool:
        """
        为指定用户授予管理员权限

        参数:
            username: 用户名

        返回:
            bool: 是否成功授予权限
        """
        try:
            script = f'net localgroup Administrators {username} /add'
            result = self.execute_powershell(script)
            if result.success:
                logger.info(f"为用户{username}授予管理员权限成功")
                return True
            else:
                logger.error(f"为用户{username}授予管理员权限失败: 错误: {result.std_err}")
                return False
        except Exception as e:
            logger.error(f"为用户{username}授予管理员权限失败: 错误: {str(e)}")
            return False
    def deop_user(self, username: str):
        """
        撤销指定用户的管理员权限

        参数:
            username: 用户名

        返回:
            bool: 是否成功撤销权限
        """
        try:
            script = f'net localgroup Administrators {username} /delete'
            result = self.execute_powershell(script)
            if result.success:
                logger.info(f"撤销用户{username}的管理员权限成功")
                return True
            else:
                logger.error(f"撤销用户{username}的管理员权限失败: 错误: {result.std_err}")
                return False
        except Exception as e:
            logger.error(f"撤销用户{username}的管理员权限失败: 错误: {str(e)}")
            return False

    def reset_password(self, username: str, password: str) -> WinrmResult:
        """
        重置指定用户的密码

        参数:
            username: 用户名
            password: 新密码

        返回:
            WinrmResult对象，包含执行结果
        """
        result = WinrmResult(status_code=502, std_out="Unknown Error", std_err="Unknown Error")
        try:
            script = f'''
                $password = ConvertTo-SecureString "{password}" -AsPlainText -Force
                Set-LocalUser -Name "{username}" -Password $password
                Write-Output "Password for user {username} has been reset successfully"
                '''
            result = self.execute_powershell(script)
            self.add_to_remote_users(username)
            if result.success:
                logger.info(f"重置用户{username}的密码成功")
                return result
            else:
                logger.error(f"重置用户{username}的密码失败: 错误: {result.std_err}")
                return result
        except Exception as e:
            logger.error(f"重置用户{username}的密码失败: 错误: {str(e)}")
            return result
    def add_to_remote_users(self, username: str) -> WinrmResult:
        """
        将指定用户添加到远程用户组

        参数:
            username: 用户名

        返回:
            WinrmResult对象，包含执行结果
        """
        result = WinrmResult(status_code=502, std_out="Unknown Error", std_err="Unknown Error")
        try:
            script = f'Add-LocalGroupMember -Group "Remote Desktop Users" -Member "{username}"'
            result = self.execute_powershell(script)
            if result.success:
                logger.info(f"将用户{username}添加到远程用户组成功")
                return result
            else:
                logger.error(f"将用户{username}添加到远程用户组失败: 错误: {result.std_err}")
                return result
        except Exception as e:
            logger.error(f"将用户{username}添加到远程用户组失败: 错误: {str(e)}")
            return result