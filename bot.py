

import asyncio
import json
import os
import random
import base64
import uuid
from datetime import datetime
import pytz

from aiohttp import (
    ClientResponseError,
    ClientSession,
    ClientTimeout,
    WSMessage,
)
from aiohttp_socks import ProxyConnector
from colorama import Fore, Style
from fake_useragent import FakeUserAgent



# 时区设置
TIMEZONE = pytz.timezone('Asia/Jakarta')


HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://testnet.openledger.xyz",
    "Referer": "https://testnet.openledger.xyz/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "User-Agent": "Your User Agent Here"  # 运行时动态生成
}

# 代理列表 URL 和文件路径
PROXY_LIST_URL = "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/all.txt"
PROXY_FILE_AUTO = 'proxy.txt'
PROXY_FILE_MANUAL = 'manual_proxy.txt'

# 扩展 ID
EXTENSION_ID = "chrome-extension://ekbbplmjjgoobhdlffmgeokalelnmjjc"


CONSTANTS = {
    "API": {
        "BASE_URL": "https://api.depined.org/api",
        "ENDPOINTS": {
            "USER_DETAILS": "/user/details",
            "WIDGET_CONNECT": "/user/widget-connect",
            "EPOCH_EARNINGS": "/stats/epoch-earnings",
        },
        "HEADERS": {
            "CONTENT_TYPE": "application/json",
        },
    },
    "FILES": {
        "JWT_PATH": "./data.txt",
    },
    "DELAYS": {
        "MIN": 300,    # 最小延迟（秒）
        "MAX": 2700,   # 最大延迟（秒）
    },
    "MESSAGES": {
        "ERRORS": {
            "FILE_READ": "读取JWT文件时出错",
            "NO_JWT": "data.txt中未找到JWT",
            "INITIAL_SETUP": "初始设置失败",
            "UNCAUGHT": "未捕获的异常",
            "UNHANDLED": "未处理的拒绝",
        },
        "INFO": {
            "CONNECTED": "已连接",
            "FOUND_ACCOUNTS": "找到",
            "ACCOUNTS": "个JWT",
        },
        "LOG_FORMAT": {
            "EARNINGS": "收益",
            "EPOCH": "纪元",
            "ERROR": "错误",
        },
    },
}



class Logger:
    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().astimezone(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')
        if level == "INFO":
            color = Fore.GREEN
            prefix = "[信息]"
        elif level == "ERROR":
            color = Fore.RED
            prefix = "[错误]"
        elif level == "SUCCESS":
            color = Fore.CYAN
            prefix = "[成功]"
        else:
            color = Fore.WHITE
            prefix = "[日志]"
        
        print(
            f"{Fore.CYAN + Style.BRIGHT}[ {timestamp} ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}"
            f"{color + Style.BRIGHT}{prefix} {message}{Style.RESET_ALL}",
            flush=True
        )



class ProxyManager:
    def __init__(self, logger: Logger):
        self.logger = logger
        self.proxies = []
        self.proxy_index = 0

    async def load_auto_proxies(self):
        try:
            async with ClientSession(timeout=ClientTimeout(total=20)) as session:
                async with session.get(url=PROXY_LIST_URL) as response:
                    response.raise_for_status()
                    content = await response.text()
                    with open(PROXY_FILE_AUTO, 'w') as f:
                        f.write(content)
                    self.proxies = content.splitlines()
                    if not self.proxies:
                        self.logger.log("未在下载的列表中找到代理！", "ERROR")
                        return False
                    self.logger.log("代理下载成功。", "INFO")
                    self.logger.log(f"加载了 {len(self.proxies)} 个代理。", "INFO")
                    return True
        except Exception as e:
            self.logger.log(f"加载代理失败: {e}", "ERROR")
            return False

    async def load_manual_proxies(self):
        try:
            with open(PROXY_FILE_MANUAL, "r") as f:
                proxies = f.read().splitlines()
            self.proxies = proxies
            self.logger.log(f"加载了 {len(self.proxies)} 个手动代理。", "INFO")
            return True
        except Exception as e:
            self.logger.log(f"加载手动代理失败: {e}", "ERROR")
            return False

    def check_proxy_scheme(self, proxy: str) -> str:
        schemes = ["http://", "https://", "socks4://", "socks5://"]
        if any(proxy.startswith(scheme) for scheme in schemes):
            return proxy
        return f"http://{proxy}"  # 默认使用http

    def get_next_proxy(self) -> str:
        if not self.proxies:
            self.logger.log("没有可用的代理！", "ERROR")
            return None
        proxy = self.proxies[self.proxy_index]
        self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return self.check_proxy_scheme(proxy)


class AccountManager:
    def __init__(self, logger: Logger, proxy_manager: ProxyManager):
        self.logger = logger
        self.proxy_manager = proxy_manager
        self.headers = HEADERS.copy()
        self.headers["User-Agent"] = FakeUserAgent().random

    def generate_id(self) -> str:
        return str(uuid.uuid4())

    def generate_worker_id(self, account: str) -> str:
        return base64.b64encode(account.encode("utf-8")).decode("utf-8")

    def hide_account(self, account: str) -> str:
        return account[:6] + '*' * 6 + account[-6:]

    async def generate_token(self, account: str, connector: ProxyConnector = None, retries: int = 5) -> str:
        url = "https://apitn.openledger.xyz/api/v1/auth/generate_token"
        data = json.dumps({"address": account})
        headers = {
            **self.headers,
            "Content-Length": str(len(data)),
            "Content-Type": "application/json"
        }
        for attempt in range(retries):
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url=url, headers=headers, data=data) as response:
                        response.raise_for_status()
                        result = await response.json()
                        return result['data']['token']
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(2)
                else:
                    self.logger.log(f"生成令牌失败: {e}", "ERROR")
                    return None

    async def renew_token(self, account: str, connector: ProxyConnector = None) -> str:
        token = await self.generate_token(account, connector)
        if not token:
            self.logger.log(
                f"[ 账户 {self.hide_account(account)} ] 续订访问令牌失败",
                "ERROR"
            )
            return None

        self.logger.log(
            f"[ 账户 {self.hide_account(account)} ] 访问令牌已续订",
            "SUCCESS"
        )
        return token

 

class WebSocketClient:
    def __init__(self, logger: Logger):
        self.logger = logger

    async def send_json_message(self, wss, message: dict):
        try:
            await wss.send_json(message)
        except Exception as e:
            self.logger.log(f"发送消息失败: {e}", "ERROR")

    async def handle_messages(self, wss, account: str, identity: str):
        async for msg in wss:
            if isinstance(msg, WSMessage):
                message = json.loads(msg.data)
                if message.get("MsgType") != "JOB":
                    response = {
                        "type": "WEBSOCKET_RESPONSE",
                        "data": message
                    }
                    await self.send_json_message(wss, response)
                    self.logger.log(
                        f"[ 账户 {account} ] 接收到消息: {message}",
                        "INFO"
                    )
                elif message.get("MsgType") == "JOB":
                    response = {
                        "workerID": identity,
                        "msgType": "JOB_ASSIGNED",
                        "workerType": "LWEXT",
                        "message": {
                            "Status": True,
                            "Ref": message["UUID"]
                        }
                    }
                    await self.send_json_message(wss, response)
                    self.logger.log(
                        f"[ 账户 {account} ] 任务已分配: {message}",
                        "SUCCESS"
                    )



class BotFramework:
    def __init__(self):
        self.logger = Logger()
        self.proxy_manager = ProxyManager(self.logger)
        self.account_manager = AccountManager(self.logger, self.proxy_manager)
        self.websocket_client = WebSocketClient(self.logger)

    def clear_terminal(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def welcome(self):
        print(
            f"""
{Fore.GREEN + Style.BRIGHT}自动 Ping {Fore.BLUE + Style.BRIGHT}Open Ledger - 机器人
{Fore.GREEN + Style.BRIGHT}Rey? {Fore.YELLOW + Style.BRIGHT}<INI 水印>
            """
        )

    def format_number(self, number: float) -> str:
        if number >= 1_000_000_000:
            return f"{number / 1_000_000_000:.2f}B"
        elif number >= 1_000_000:
            return f"{number / 1_000_000:.2f}M"
        elif number >= 1_000:
            return f"{number / 1_000:.2f}K"
        return f"{number:.2f}"

    def get_random_delay(self) -> int:
        return random.randint(CONSTANTS["DELAYS"]["MIN"], CONSTANTS["DELAYS"]["MAX"])

    async def load_proxies(self, choice: int) -> bool:
        if choice == 1:
            return await self.proxy_manager.load_auto_proxies()
        elif choice == 2:
            return await self.proxy_manager.load_manual_proxies()
        return False

    async def prompt_proxy_choice(self) -> int:
        while True:
            try:
                print("1. 使用自动代理")
                print("2. 使用手动代理")
                print("3. 不使用代理")
                choice = int(input("请选择 [1/2/3] -> ").strip())
                if choice in [1, 2, 3]:
                    proxy_type = (
                        "自动代理" if choice == 1 else 
                        "手动代理" if choice == 2 else 
                        "不使用代理"
                    )
                    print(f"{Fore.GREEN + Style.BRIGHT}选择了 {proxy_type}。{Style.RESET_ALL}")
                    await asyncio.sleep(1)
                    return choice
                else:
                    print(f"{Fore.RED + Style.BRIGHT}请输入 1、2 或 3。{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED + Style.BRIGHT}输入无效。请输入数字 (1, 2 或 3)。{Style.RESET_ALL}")

    async def read_jwt_file(self) -> list:
        try:
            with open(CONSTANTS["FILES"]["JWT_PATH"], "r") as f:
                jwts = [line.strip() for line in f if line.strip()]
            self.logger.log(
                f"{CONSTANTS['MESSAGES']['INFO']['FOUND_ACCOUNTS']} {len(jwts)} {CONSTANTS['MESSAGES']['INFO']['ACCOUNTS']}",
                "INFO"
            )
            return jwts
        except Exception as e:
            self.logger.log(f"{CONSTANTS['MESSAGES']['ERRORS']['FILE_READ']}: {e}", "ERROR")
            return []

    async def process_jwt(self, jwt: str, use_proxy: bool):
        proxy = self.proxy_manager.get_next_proxy() if use_proxy else None

        if not jwt:
            self.logger.log("JWT为空，跳过处理。", "ERROR")
            return

        await self.run_jwt_flow(jwt, proxy, use_proxy)

    async def run_jwt_flow(self, jwt: str, proxy: str, use_proxy: bool):
        api_base_url = CONSTANTS["API"]["BASE_URL"]
        endpoints = CONSTANTS["API"]["ENDPOINTS"]

        connector = ProxyConnector.from_url(proxy) if proxy else None

        async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
            try:
                # 获取用户详情
                async with session.get(
                    url=api_base_url + endpoints["USER_DETAILS"],
                    headers={
                        "Authorization": f"Bearer {jwt}",
                        "Content-Type": CONSTANTS["API"]["HEADERS"]["CONTENT_TYPE"]
                    }
                ) as response:
                    response.raise_for_status()
                    user_details = await response.json()
                    username = user_details["data"]["username"]
                    self.logger.log(
                        f"[{username}] {CONSTANTS['MESSAGES']['INFO']['CONNECTED']}",
                        "INFO"
                    )

                while True:
                    try:
                        delay = self.get_random_delay()
                        await asyncio.sleep(delay)

                        # 连接小部件
                        async with session.post(
                            url=api_base_url + endpoints["WIDGET_CONNECT"],
                            headers={
                                "Authorization": f"Bearer {jwt}",
                                "Content-Type": CONSTANTS["API"]["HEADERS"]["CONTENT_TYPE"]
                            },
                            json={"connected": True}
                        ) as post_response:
                            post_response.raise_for_status()

                       
                        async with session.get(
                            url=api_base_url + endpoints["EPOCH_EARNINGS"],
                            headers={
                                "Authorization": f"Bearer {jwt}",
                                "Content-Type": CONSTANTS["API"]["HEADERS"]["CONTENT_TYPE"]
                            }
                        ) as earnings_response:
                            earnings_response.raise_for_status()
                            earnings = await earnings_response.json()
                            formatted_earnings = self.format_number(earnings["data"]["earnings"])

                        self.logger.log(
                            f"[{username}] {CONSTANTS['MESSAGES']['INFO']['CONNECTED']} | "
                            f"{CONSTANTS['MESSAGES']['LOG_FORMAT']['EARNINGS']}: {formatted_earnings} "
                            f"({CONSTANTS['MESSAGES']['LOG_FORMAT']['EPOCH']}: {earnings['data']['epoch']})",
                            "SUCCESS"
                        )
                    except Exception as error:
                        self.logger.log(
                            f"[{username}] {CONSTANTS['MESSAGES']['LOG_FORMAT']['ERROR']}: {error}",
                            "ERROR"
                        )
                        await asyncio.sleep(CONSTANTS["DELAYS"]["MIN"])

            except Exception as error:
                self.logger.log(
                    f"[JWT {jwt[:6]}...] {CONSTANTS['MESSAGES']['ERRORS']['INITIAL_SETUP']}: {error}",
                    "ERROR"
                )
                await asyncio.sleep(CONSTANTS["DELAYS"]["MAX"])
                if use_proxy:
                    proxy = self.proxy_manager.get_next_proxy()
                await self.run_jwt_flow(jwt, proxy, use_proxy)

    async def connect_websocket(self, account: str, token: str, use_proxy: bool, proxy: str):
        wss_url = f"wss://apitn.openledger.xyz/ws/v1/orch?authToken={token}"
        headers = {
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Cache-Control": "no-cache",
            "Connection": "Upgrade",
            "Host": "apitn.openledger.xyz",
            "Origin": EXTENSION_ID,
            "Pragma": "no-cache",
            "Sec-Websocket-Extensions": "permessage-deflate; client_max_window_bits",
            "Sec-Websocket-Key": "pyAFsQgNHYvbq16if2s6Bw==",
            "Sec-Websocket-Version": "13",
            "Upgrade": "websocket",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        }
        registered = False

        id = self.account_manager.generate_id()
        identity = self.account_manager.generate_worker_id(account)
        memory = round(random.uniform(0, 32), 2)
        storage = str(round(random.uniform(0, 500), 2))

        connector = ProxyConnector.from_url(proxy) if proxy else None

        async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
            while True:
                try:
                    async with session.ws_connect(wss_url, headers=headers) as wss:
                        self.logger.log(
                            f"[ 账户 {self.account_manager.hide_account(account)} ] Websocket 已连接",
                            "SUCCESS"
                        )

                        if not registered:
                            register_message = {
                                "workerID": identity,
                                "msgType": "REGISTER",
                                "workerType": "LWEXT",
                                "message": {
                                    "id": id,
                                    "type": "REGISTER",
                                    "worker": {
                                        "host": EXTENSION_ID,
                                        "identity": identity,
                                        "ownerAddress": account,
                                        "type": "LWEXT"
                                    }
                                }
                            }
                            await self.websocket_client.send_json_message(wss, register_message)
                            registered = True

                        async def send_heartbeat():
                            while not wss.closed:
                                await asyncio.sleep(30)
                                heartbeat_message = {
                                    "message": {
                                        "Worker": {
                                            "Identity": identity,
                                            "ownerAddress": account,
                                            "type": "LWEXT",
                                            "Host": EXTENSION_ID
                                        },
                                        "Capacity": {
                                            "AvailableMemory": memory,
                                            "AvailableStorage": storage,
                                            "AvailableGPU": "",
                                            "AvailableModels": []
                                        }
                                    },
                                    "msgType": "HEARTBEAT",
                                    "workerType": "LWEXT",
                                    "workerID": identity
                                }
                                await self.websocket_client.send_json_message(wss, heartbeat_message)
                                self.logger.log(
                                    f"[ 账户 {self.account_manager.hide_account(account)} ] 发送心跳",
                                    "SUCCESS"
                                )

                        heartbeat_task = asyncio.create_task(send_heartbeat())

                        try:
                            await self.websocket_client.handle_messages(wss, account, identity)
                        except Exception as e:
                            self.logger.log(f"Websocket 通信错误: {e}", "ERROR")
                        finally:
                            if not wss.closed:
                                await wss.close()
                            heartbeat_task.cancel()
                            try:
                                await heartbeat_task
                            except asyncio.CancelledError:
                                pass

                except Exception as e:
                    self.logger.log(f"Websocket 未连接: {e}", "ERROR")
                    if use_proxy:
                        proxy = self.proxy_manager.get_next_proxy()
                        connector = ProxyConnector.from_url(proxy) if proxy else None
                        session.connector = connector
                    await asyncio.sleep(5)

   

    async def main(self):
        try:
            jwts = await self.read_jwt_file()

            if not jwts:
                self.logger.log(CONSTANTS['MESSAGES']['ERRORS']['NO_JWT'], "ERROR")
                return

            proxy_choice = await self.prompt_proxy_choice()
            use_proxy = proxy_choice in [1, 2]

            self.clear_terminal()
            self.welcome()
            self.logger.log(
                f"账户总数: {len(jwts)}",
                "INFO"
            )
            self.logger.log(f"{'-'*75}", "INFO")

            if use_proxy:
                loaded = await self.load_proxies(proxy_choice)
                if not loaded:
                    self.logger.log("代理加载失败。", "ERROR")
                    if proxy_choice in [1, 2]:
                        use_proxy = False  # 如果代理加载失败，选择不使用代理

            tasks = []
            for jwt in jwts:
                tasks.append(self.process_jwt(jwt, use_proxy))

            await asyncio.gather(*tasks)

        except Exception as e:
            self.logger.log(f"错误: {e}", "ERROR")

  

    async def run_jwt_flow(self, jwt: str, proxy: str, use_proxy: bool):
        api_base_url = CONSTANTS["API"]["BASE_URL"]
        endpoints = CONSTANTS["API"]["ENDPOINTS"]

        connector = ProxyConnector.from_url(proxy) if proxy else None

        async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
            try:
                # 获取用户详情
                async with session.get(
                    url=api_base_url + endpoints["USER_DETAILS"],
                    headers={
                        "Authorization": f"Bearer {jwt}",
                        "Content-Type": CONSTANTS["API"]["HEADERS"]["CONTENT_TYPE"]
                    }
                ) as response:
                    response.raise_for_status()
                    user_details = await response.json()
                    username = user_details["data"]["username"]
                    self.logger.log(
                        f"[{username}] {CONSTANTS['MESSAGES']['INFO']['CONNECTED']}",
                        "INFO"
                    )

                while True:
                    try:
                        delay = self.get_random_delay()
                        await asyncio.sleep(delay)

                        # 连接小部件
                        async with session.post(
                            url=api_base_url + endpoints["WIDGET_CONNECT"],
                            headers={
                                "Authorization": f"Bearer {jwt}",
                                "Content-Type": CONSTANTS["API"]["HEADERS"]["CONTENT_TYPE"]
                            },
                            json={"connected": True}
                        ) as post_response:
                            post_response.raise_for_status()

                        # 获取 epoch 收益
                        async with session.get(
                            url=api_base_url + endpoints["EPOCH_EARNINGS"],
                            headers={
                                "Authorization": f"Bearer {jwt}",
                                "Content-Type": CONSTANTS["API"]["HEADERS"]["CONTENT_TYPE"]
                            }
                        ) as earnings_response:
                            earnings_response.raise_for_status()
                            earnings = await earnings_response.json()
                            formatted_earnings = self.format_number(earnings["data"]["earnings"])

                        self.logger.log(
                            f"[{username}] {CONSTANTS['MESSAGES']['INFO']['CONNECTED']} | "
                            f"{CONSTANTS['MESSAGES']['LOG_FORMAT']['EARNINGS']}: {formatted_earnings} "
                            f"({CONSTANTS['MESSAGES']['LOG_FORMAT']['EPOCH']}: {earnings['data']['epoch']})",
                            "SUCCESS"
                        )
                    except Exception as error:
                        self.logger.log(
                            f"[{username}] {CONSTANTS['MESSAGES']['LOG_FORMAT']['ERROR']}: {error}",
                            "ERROR"
                        )
                        await asyncio.sleep(CONSTANTS["DELAYS"]["MIN"])

            except Exception as error:
                self.logger.log(
                    f"[JWT {jwt[:6]}...] {CONSTANTS['MESSAGES']['ERRORS']['INITIAL_SETUP']}: {error}",
                    "ERROR"
                )
                await asyncio.sleep(CONSTANTS["DELAYS"]["MAX"])
                if use_proxy:
                    proxy = self.proxy_manager.get_next_proxy()
                await self.run_jwt_flow(jwt, proxy, use_proxy)



if __name__ == "__main__":
    try:
        bot = BotFramework()
        asyncio.run(bot.main())
    except KeyboardInterrupt:
        print(
            f"{Fore.CYAN + Style.BRIGHT}[ {datetime.now().astimezone(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')} ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}"
            f"{Fore.RED + Style.BRIGHT}[ 退出 ] 自动 Ping Open Ledger - 机器人{Style.RESET_ALL}"
        )
    except Exception as e:
        Logger().log(f"未处理的异常: {e}", "ERROR")
