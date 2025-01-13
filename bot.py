import asyncio
import aiohttp
from fake_useragent import UserAgent
import logging
import json
import os
import signal
from datetime import datetime
from colorama import Fore, Style, init
import sys
import pyfiglet
from tabulate import tabulate
from halo import Halo
import pytz

# 初始化 colorama
init(autoreset=True)

# =========================
# 日志记录模块
# =========================

class Logger:
    def __init__(self, timezone="Asia/Shanghai"):
        self.logger = logging.getLogger("DepinedBot")
        self.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.timezone = timezone  # 定义时区

        # 定义日志级别到中文的映射
        self.level_map = {
            'info': '信息',
            'warn': '警告',
            'error': '错误',
            'success': '成功',
            'debug': '调试'
        }

    def log(self, level, message, value=''):
        now = get_timestamp(format="%Y-%m-%d %H:%M:%S", timezone=self.timezone)
        level_lower = level.lower()
        level_cn = self.level_map.get(level_lower, '信息')
        colors = {
            '信息': Fore.CYAN + Style.BRIGHT,
            '警告': Fore.YELLOW + Style.BRIGHT,
            '错误': Fore.RED + Style.BRIGHT,
            '成功': Fore.GREEN + Style.BRIGHT,
            '调试': Fore.MAGENTA + Style.BRIGHT
        }
        color = colors.get(level_cn, Fore.WHITE)
        level_tag = f"[ {level_cn} ]"
        timestamp = f"[ {now} ]"
        formatted_message = f"{Fore.CYAN + Style.BRIGHT}[ DepinedBot ]{Style.RESET_ALL} {Fore.LIGHTBLACK_EX}{timestamp}{Style.RESET_ALL} {color}{level_tag}{Style.RESET_ALL} {message}"
        
        if value:
            if isinstance(value, dict) or isinstance(value, list):
                try:
                    serialized = json.dumps(value, ensure_ascii=False)
                    formatted_value = f" {Fore.GREEN}{serialized}{Style.RESET_ALL}" if level_cn != '错误' else f" {Fore.RED}{serialized}{Style.RESET_ALL}"
                except Exception as e:
                    self.error("序列化日志值时出错:", str(e))
                    formatted_value = f" {Fore.RED}无法序列化的值{Style.RESET_ALL}"
            else:
                if level_cn == '错误':
                    formatted_value = f" {Fore.RED}{value}{Style.RESET_ALL}"
                elif level_cn == '警告':
                    formatted_value = f" {Fore.YELLOW}{value}{Style.RESET_ALL}"
                else:
                    formatted_value = f" {Fore.GREEN}{value}{Style.RESET_ALL}"
            formatted_message += formatted_value

        self.logger.log(getattr(logging, level_upper(level_cn), logging.INFO), formatted_message)

    def info(self, message, value=''):
        self.log('info', message, value)

    def warn(self, message, value=''):
        self.log('warn', message, value)

    def error(self, message, value=''):
        self.log('error', message, value)

    def success(self, message, value=''):
        self.log('success', message, value)

    def debug(self, message, value=''):
        self.log('debug', message, value)

def level_upper(level_cn):
    """辅助函数，将中文级别转换为 logging 模块的级别名"""
    mapping = {
        '信息': 'INFO',
        '警告': 'WARNING',
        '错误': 'ERROR',
        '成功': 'INFO',  # 成功映射为 INFO
        '调试': 'DEBUG'
    }
    return mapping.get(level_cn, 'INFO')

logger = Logger()

# =========================
# 辅助函数模块
# =========================

def get_timestamp(format="%Y-%m-%d %H:%M:%S", timezone="Asia/Shanghai"):
    """获取当前时间的字符串表示"""
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)
    return now.strftime(format)

async def delay(seconds):
    """延迟执行"""
    await asyncio.sleep(seconds)

async def save_to_file(filename, data):
    """将数据保存到文件，每条数据占一行"""
    try:
        with open(filename, 'a', encoding='utf-8') as f:
            if isinstance(data, (dict, list)):
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
            else:
                f.write(str(data) + '\n')
        logger.info(f"数据已保存到 {filename}")
    except Exception as e:
        logger.error(f"保存数据到 {filename} 时失败:", str(e))

async def read_file(path_file):
    """读取文件并返回非空行的列表"""
    try:
        if not os.path.exists(path_file):
            logger.warn(f"文件 {path_file} 不存在。")
            return []
        with open(path_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        return [line.strip() for line in lines if line.strip()]
    except Exception as e:
        logger.error(f"读取文件 {path_file} 时出错:", str(e))
        return []

def new_agent(proxy=None):
    """根据代理类型创建代理字典"""
    if proxy:
        if proxy.startswith('http://') or proxy.startswith('https://'):
            return proxy
        elif proxy.startswith('socks4://') or proxy.startswith('socks5://'):
            return proxy
        else:
            logger.warn(f"不支持的代理类型: {proxy}")
            return None
    return None

# =========================
# API 模块
# =========================

ua = UserAgent()
headers = {
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "User-Agent": ua.random
}

def make_headers(token=None):
    """生成请求头"""
    hdr = headers.copy()
    hdr['Content-Type'] = 'application/json'
    if token:
        hdr['Authorization'] = f'Bearer {token}'
    return hdr

async def register_user(session, email, password):
    """注册用户"""
    url = 'https://api.depined.org/api/user/register'
    payload = {
        'email': email,
        'password': password
    }
    try:
        async with session.post(url, json=payload, headers=make_headers()) as response:
            if response.status == 200:
                data = await response.json()
                logger.success('用户注册成功:', data.get('message', ''))
                return data
            else:
                error_data = await response.json()
                logger.error('注册用户时出错:', error_data)
                return None
    except aiohttp.ClientError as e:
        logger.error('注册用户时出错:', str(e))
        return None

async def login_user(session, email, password):
    """用户登录"""
    url = 'https://api.depined.org/api/user/login'
    payload = {
        'email': email,
        'password': password
    }
    try:
        async with session.post(url, json=payload, headers=make_headers()) as response:
            if response.status == 200:
                data = await response.json()
                logger.success('用户登录成功:', data.get('message', ''))
                return data
            else:
                error_data = await response.json()
                logger.error('用户登录时出错:', error_data)
                return None
    except aiohttp.ClientError as e:
        logger.error('用户登录时出错:', str(e))
        return None

async def create_user_profile(session, token, payload):
    """创建用户资料"""
    url = 'https://api.depined.org/api/user/profile-creation'
    try:
        async with session.post(url, json=payload, headers=make_headers(token)) as response:
            if response.status == 200:
                data = await response.json()
                logger.success('用户资料创建成功:', data.get('message', ''))
                return data
            else:
                error_data = await response.json()
                logger.error('创建用户资料时出错:', error_data)
                return None
    except aiohttp.ClientError as e:
        logger.error('创建用户资料时出错:', str(e))
        return None

async def confirm_user_reff(session, token, referral_code):
    """确认用户推荐码"""
    url = 'https://api.depined.org/api/access-code/referal'
    payload = {
        'referral_code': referral_code
    }
    try:
        async with session.post(url, json=payload, headers=make_headers(token)) as response:
            if response.status == 200:
                data = await response.json()
                logger.success('确认用户推荐码成功:', data.get('message', ''))
                return data
            else:
                error_data = await response.json()
                logger.error('确认用户推荐码时出错:', error_data)
                return None
    except aiohttp.ClientError as e:
        logger.error('确认用户推荐码时出错:', str(e))
        return None

async def get_user_info(session, token, proxy=None):
    """获取用户信息"""
    url = 'https://api.depined.org/api/user/details'
    try:
        proxy_url = new_agent(proxy)
        async with session.get(url, headers=make_headers(token), proxy=proxy_url) as response:
            if response.status == 200:
                data = await response.json()
                logger.info('获取用户信息成功')
                return data
            else:
                error_data = await response.json()
                logger.error('获取用户信息时出错:', error_data)
                return None
    except aiohttp.ClientError as e:
        logger.error('获取用户信息时出错:', str(e))
        return None

async def get_earnings(session, token, proxy=None):
    """获取收益信息"""
    url = 'https://api.depined.org/api/stats/epoch-earnings'
    try:
        proxy_url = new_agent(proxy)
        async with session.get(url, headers=make_headers(token), proxy=proxy_url) as response:
            if response.status == 200:
                data = await response.json()
                logger.info('获取收益信息成功')
                logger.debug(f"收益信息数据: {data}")  # 添加调试日志
                return data
            else:
                error_data = await response.json()
                logger.error('获取收益信息时出错:', error_data)
                return None
    except aiohttp.ClientError as e:
        logger.error('获取收益信息时出错:', str(e))
        return None

async def connect(session, token, proxy=None):
    """连接用户"""
    url = 'https://api.depined.org/api/user/widget-connect'
    payload = {
        'connected': True
    }
    try:
        proxy_url = new_agent(proxy)
        async with session.post(url, json=payload, headers=make_headers(token), proxy=proxy_url) as response:
            if response.status == 200:
                data = await response.json()
                logger.success('连接用户成功:', data.get('message', ''))
                return data
            else:
                error_data = await response.json()
                logger.error('连接用户时出错:', error_data)
                return None
    except aiohttp.ClientError as e:
        logger.error('连接用户时出错:', str(e))
        return None

# =========================
# 主程序类
# =========================

class DepinedBot:
    def __init__(self):
        self.accounts = []
        self.loop = asyncio.get_event_loop()

    def display_banner(self):
        """显示 ASCII 艺术横幅"""
        banner = pyfiglet.figlet_format("DepinedBot")
        print(Fore.GREEN + banner)

    def create_stats_table(self):
        """创建账户状态表格"""
        table = []
        headers = ['账户', '用户名', '邮箱', '状态', '今日积分', '总积分', '最后更新时间']
        for account in self.accounts:
            table.append([
                account['token'][:8] + '...',
                account.get('username', '未设置'),
                account.get('email', '未绑定'),
                account.get('status', '未知'),
                f"{account.get('pointsToday', 0.0):.2f}",
                f"{account.get('totalPoints', 0.0):.2f}",
                account.get('lastUpdate', '-')
            ])
        return tabulate(table, headers, tablefmt='fancy_grid', stralign='center')

    def log_success(self, account_id, message, points_today, total_points, username, email):
        """记录成功的活动日志"""
        current_time = get_timestamp(format="%Y-%m-%d %H:%M:%S", timezone="Asia/Shanghai")

        log_message = (
            f"{Fore.GREEN}[{current_time}] 账户 {account_id}: {message}"
            f"{Fore.BLUE} | 用户名: {username or '未知'}"
            f"{Fore.YELLOW} | 邮箱: {email or '未绑定'}"
            f"{Fore.MAGENTA} | 今日积分: {points_today:.2f}"
            f"{Fore.CYAN} | 总积分: {total_points:.2f}{Style.RESET_ALL}"
        )
        print(log_message)

    async def process_account(self, session, account, index):
        """处理单个账户，包括获取用户信息和设置定时任务"""
        try:
            # 获取用户信息
            user_data = await get_user_info(session, account['token'], account['proxyConfig'])
            if user_data and 'data' in user_data:
                email = user_data['data'].get('email', '')
                verified = user_data['data'].get('verified', False)
                current_tier = user_data['data'].get('current_tier', '')
                points_balance = user_data['data'].get('points_balance', 0)
                account['username'] = user_data['data'].get('username', '-')
                account['email'] = email
                logger.info(f"账户 {index + 1} 信息:", {
                    'email': email,
                    'verified': verified,
                    'current_tier': current_tier,
                    'points_balance': points_balance
                })
            
            # Ping server
            await connect(session, account['token'], account['proxyConfig'])
            account['status'] = Fore.GREEN + '已连接' + Style.RESET_ALL
            
            # 获取收益信息
            earnings_res = await get_earnings(session, account['token'], account['proxyConfig'])
            if earnings_res and 'data' in earnings_res:
                account['pointsToday'] = earnings_res['data'].get('earnings', 0)
                # 使用 user_data 中的 points_balance 作为总积分
                account['totalPoints'] = user_data['data'].get('points_balance', 0)
                account['lastUpdate'] = get_timestamp(timezone="Asia/Shanghai")
                self.log_success(
                    index + 1,
                    f"Ping 成功 ({account['proxyConfig']['type']})" if account['proxyConfig'] else "Ping 成功 (直接连接)",
                    account['pointsToday'],
                    account['totalPoints'],
                    account['username'],
                    account['email']
                )
            else:
                logger.warn(f"账户 {index + 1} 收益信息获取失败。")
        
        except Exception as e:
            account['status'] = Fore.RED + '错误' + Style.RESET_ALL
            account['lastUpdate'] = get_timestamp(timezone="Asia/Shanghai")
            logger.error(f"账户 {index + 1} 出现错误:", str(e))

    async def main(self):
        """主函数"""
        self.display_banner()

        spinner = Halo(text='读取输入文件...', spinner='dots')
        spinner.start()
        tokens, proxies = await read_input_files()
        spinner.succeed(f"加载了 {len(tokens)} 个令牌和 {len(proxies)} 个代理")

        self.accounts = [
            {
                'token': token,
                'proxyConfig': proxies[index % len(proxies)] if proxies else None,
                'status': '初始化中',
                'username': None,
                'email': None,
                'pointsToday': 0,
                'totalPoints': 0,
                'lastUpdate': None
            }
            for index, token in enumerate(tokens)
        ]

        while True:
            # 清屏并显示横幅
            os.system('cls' if os.name == 'nt' else 'clear')
            self.display_banner()
            print(Fore.YELLOW + '加入我们 : https://t.me/ksqxszq\n')
            print(Fore.CYAN + '=== Depined 多账户管理 ===\n')
            print(self.create_stats_table())
            print(Fore.CYAN + '\n=== 活动日志 ===')

            async with aiohttp.ClientSession() as session:
                tasks = [self.process_account(session, account, index) for index, account in enumerate(self.accounts)]
                await asyncio.gather(*tasks)
            
            # 等待30秒后刷新
            await delay(30)

    def shutdown(self):
        """优雅地关闭程序"""
        current_time = get_timestamp(format="%Y-%m-%d %H:%M:%S", timezone="Asia/Shanghai")
        exit_message = (
            f"{Fore.CYAN + Style.BRIGHT}[ {current_time} ]{Style.RESET_ALL} "
            f"{Fore.WHITE + Style.BRIGHT}| {Style.RESET_ALL}"
            f"{Fore.RED + Style.BRIGHT}[ EXIT ] DepinedBot 已退出{Style.RESET_ALL}"
        )
        print(exit_message)
        # 取消所有挂起的任务
        tasks = asyncio.all_tasks(loop=self.loop)
        for task in tasks:
            task.cancel()
        # 等待任务取消
        try:
            self.loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        except Exception:
            pass
        self.loop.stop()
        sys.exit(0)

    def setup_signal_handlers(self):
        """设置信号处理器"""
        signal.signal(signal.SIGINT, lambda s, f: self.shutdown())
        signal.signal(signal.SIGTERM, lambda s, f: self.shutdown())

# =========================
# 文件读取与验证
# =========================

async def read_input_files():
    """读取并验证输入文件"""
    try:
        tokens = await read_file("tokens.txt")
        if not tokens:
            logger.error('在 tokens.txt 中未找到任何令牌。')
            sys.exit(1)
        
        proxies = []
        try:
            proxy_strings = await read_file("proxy.txt")
            for proxy_str in proxy_strings:
                try:
                    proxy_config = parse_proxy_string(proxy_str)
                    proxies.append(proxy_config)
                except Exception as e:
                    logger.warn(f"代理解析失败: {proxy_str} - {str(e)}")
        except Exception as e:
            logger.warn('未找到 proxy.txt 或读取代理时出错。程序将不使用代理。')
        
        return tokens, proxies
    except Exception as e:
        logger.error(f"读取输入文件时出错:", str(e))
        sys.exit(1)

def parse_proxy_string(proxy_string):
    """解析代理字符串"""
    try:
        protocol, rest = proxy_string.strip().split("://", 1)
        if '@' in rest:
            credentials, host_port = rest.split('@', 1)
            username, password = credentials.split(':', 1)
            auth = {'username': username, 'password': password}
            proxy_url = f"{protocol}://{username}:{password}@{host_port}"
        else:
            host_port = rest
            proxy_url = f"{protocol}://{host_port}"
        return proxy_url
    except Exception as e:
        raise ValueError(f"无效的代理格式: {proxy_string}") from e

# =========================
# 运行主程序
# =========================

if __name__ == "__main__":
    bot = DepinedBot()
    bot.setup_signal_handlers()
    try:
        asyncio.run(bot.main())
    except KeyboardInterrupt:
        bot.shutdown()
    except Exception as e:
        logger.error("程序运行时出错:", str(e))
        sys.exit(1)
