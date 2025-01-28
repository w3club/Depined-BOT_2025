import cloudscraper from 'cloudscraper';
import fs from 'fs/promises';
import chalk from 'chalk';
import ora from 'ora';
import Table from 'cli-table3';
import { SocksProxyAgent } from 'socks-proxy-agent';
import { HttpsProxyAgent } from 'https-proxy-agent';
import figlet from 'figlet';

// 配置文件路径
const TOKEN_FILE = 'tokens.txt'; // 存储账户 Token 的文件
const PROXY_FILE = 'proxy.txt'; // 存储代理信息的文件

// API 基础地址
const BASE_URL = 'https://api.depined.org/api';

// 显示欢迎横幅
const displayBanner = () => {
  console.log(chalk.green(figlet.textSync('空投助手', { horizontalLayout: 'full' })));
  console.log(chalk.yellow('欢迎使用空投助手 - 多账户管理工具\n'));
};

// 获取当前北京时间
const getTimestamp = () => {
  const now = new Date();
  const beijingOffset = 8 * 60; // 北京时间为 UTC+8
  const localOffset = now.getTimezoneOffset(); // 本地时间与 UTC 的偏移量（分钟）
  const beijingTime = new Date(now.getTime() + (beijingOffset + localOffset) * 60 * 1000);
  return beijingTime.toLocaleTimeString('zh-CN', { hour12: false });
};

// 创建统计表格
const createStatsTable = (accounts) => {
  const table = new Table({
    head: ['账户', '用户名', '邮箱', '代理', '状态', '今日积分', '总积分', '最后更新'],
    style: {
      head: ['cyan'],
      border: ['gray'],
    },
  });

  accounts.forEach((account) => {
    table.push([
      account.token.substring(0, 8) + '...',
      account.username || '-',
      account.email || '-',
      account.proxyConfig
        ? `${account.proxyConfig.type}://${account.proxyConfig.host}:${account.proxyConfig.port}`.substring(0, 20) + '...'
        : '直连',
      account.status,
      account.pointsToday?.toFixed(2) || '0.00',
      account.totalPoints?.toFixed(2) || '0.00',
      account.lastUpdate || '-',
    ]);
  });

  return table;
};

// 解析代理字符串
const parseProxyString = (proxyString) => {
  try {
    const [protocol, rest] = proxyString.trim().split('://');
    if (!rest) throw new Error('代理格式错误');

    let [credentials, hostPort] = rest.split('@');
    if (!hostPort) {
      hostPort = credentials;
      credentials = null;
    }

    const [host, port] = hostPort.split(':');
    if (!host || !port) throw new Error('代理地址或端口错误');

    let auth = null;
    if (credentials) {
      const [username, password] = credentials.split(':');
      if (username && password) {
        auth = { username, password };
      }
    }

    return {
      type: protocol.toLowerCase(),
      host,
      port: parseInt(port),
      auth,
    };
  } catch (error) {
    throw new Error(`解析代理失败: ${proxyString}`);
  }
};

// 创建代理 Agent
const createProxyAgent = (proxyConfig) => {
  const { type, host, port, auth } = proxyConfig;
  const proxyUrl = auth ? `${type}://${auth.username}:${auth.password}@${host}:${port}` : `${type}://${host}:${port}`;

  if (type === 'socks5' || type === 'socks4') {
    return new SocksProxyAgent(proxyUrl);
  } else if (type === 'http' || type === 'https') {
    return new HttpsProxyAgent(proxyUrl);
  } else {
    throw new Error(`不支持的代理类型: ${type}`);
  }
};

// 获取用户统计数据
const getStats = async (token, proxyConfig = null) => {
  const headers = {
    Accept: 'application/json',
    Authorization: `Bearer ${token}`,
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    Referer: 'https://depined.org/',
    Origin: 'https://depined.org/',
    'Accept-Language': 'en-US,en;q=0.9',
    Connection: 'keep-alive',
  };

  const options = {
    uri: `${BASE_URL}/stats/earnings`,
    headers,
    method: 'GET',
    resolveWithFullResponse: true,
  };

  if (proxyConfig) {
    options.agent = createProxyAgent(proxyConfig);
  }

  try {
    const response = await cloudscraper(options);
    console.log(chalk.blue(`获取积分响应: ${response.body}`)); // 添加此行
    const data = JSON.parse(response.body).data;
    return {
      pointsToday: data.total_points_today || 0,
      totalPoints: data.total_points_balance || 0,
    };
  } catch (error) {
    console.error(chalk.red(`获取积分失败: ${error.message}`));
    throw error;
  }
};

// 获取用户信息
const getUserProfile = async (token, proxyConfig = null) => {
  const headers = {
    Accept: 'application/json',
    Authorization: `Bearer ${token}`,
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    Referer: 'https://depined.org/',
    Origin: 'https://depined.org/',
    'Accept-Language': 'en-US,en;q=0.9',
    Connection: 'keep-alive',
  };

  const options = {
    uri: `${BASE_URL}/user/overview/profile`,
    headers,
    method: 'GET',
    resolveWithFullResponse: true,
  };

  if (proxyConfig) {
    options.agent = createProxyAgent(proxyConfig);
  }

  try {
    const response = await cloudscraper(options);
    console.log(chalk.blue(`获取用户信息响应: ${response.body}`)); // 添加此行
    const data = JSON.parse(response.body).data;
    return {
      username: data.profile.username || '-',
      email: data.user_details.email || '-',
    };
  } catch (error) {
    console.error(chalk.red(`获取用户信息失败: ${error.message}`));
    throw error;
  }
};

// Ping 功能：发送心跳请求
const ping = async (token, proxyConfig = null) => {
  const headers = {
    Accept: 'application/json',
    Authorization: `Bearer ${token}`,
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    Referer: 'https://depined.org/',
    Origin: 'https://depined.org/',
    'Accept-Language': 'en-US,en;q=0.9',
    Connection: 'keep-alive',
  };

  const options = {
    uri: `${BASE_URL}/user/widget-connect`,
    headers,
    method: 'POST',
    body: { connected: true },
    json: true,
    resolveWithFullResponse: true,
  };

  if (proxyConfig) {
    options.agent = createProxyAgent(proxyConfig);
  }

  try {
    const response = await cloudscraper(options);
    console.log(chalk.blue(`发送心跳请求响应: ${JSON.stringify(response.body)}`)); // 添加此行
    return response.body;
  } catch (error) {
    console.error(chalk.red(`发送心跳请求失败: ${error.message}`));
    throw error;
  }
};

// 读取输入文件（Token 和代理）
const readInputFiles = async () => {
  try {
    // 读取 Token 文件
    const tokenData = await fs.readFile(TOKEN_FILE, 'utf8');
    const tokens = tokenData
      .split('\n')
      .map((line) => line.trim())
      .filter((line) => line.length > 0);

    if (tokens.length === 0) {
      throw new Error('tokens.txt 文件中未找到有效的 Token');
    }

    // 读取代理文件
    let proxies = [];
    try {
      const proxyData = await fs.readFile(PROXY_FILE, 'utf8');
      proxies = proxyData
        .split('\n')
        .map((line) => line.trim())
        .filter((line) => line.length > 0)
        .map((proxyString) => parseProxyString(proxyString));
    } catch (error) {
      console.log(chalk.yellow('未找到 proxy.txt 文件，程序将直接连接 API'));
    }

    return { tokens, proxies };
  } catch (error) {
    throw new Error(`读取文件失败: ${error.message}`);
  }
};

// 主函数
const main = async () => {
  displayBanner();

  const spinner = ora('正在加载配置文件...').start();
  const { tokens, proxies } = await readInputFiles();
  spinner.succeed(`加载完成: ${tokens.length} 个账户, ${proxies.length} 个代理`);

  const accounts = tokens.map((token, index) => ({
    token,
    proxyConfig: proxies[index % proxies.length] || null,
    status: '初始化中',
    username: null,
    email: null,
    pointsToday: 0,
    totalPoints: 0,
    lastUpdate: null,
  }));

  while (true) {
    console.clear();
    displayBanner();
    console.log(chalk.cyan('=== 账户统计 ===\n'));
    console.log(createStatsTable(accounts).toString());
    console.log(chalk.cyan('\n=== 操作日志 ==='));

    for (let i = 0; i < accounts.length; i++) {
      const account = accounts[i];

      try {
        // 获取用户信息
        if (!account.username || !account.email) {
          const profile = await getUserProfile(account.token, account.proxyConfig);
          account.username = profile.username;
          account.email = profile.email;
        }

        // 发送心跳请求
        await ping(account.token, account.proxyConfig);
        account.status = chalk.green('已连接');

        // 获取统计数据
        const stats = await getStats(account.token, account.proxyConfig);
        account.pointsToday = stats.pointsToday;
        account.totalPoints = stats.totalPoints;
        account.lastUpdate = getTimestamp();

        console.log(
          chalk.green(`[${getTimestamp()}] 账户 ${i + 1}: 心跳请求成功`) +
            chalk.blue(` | ${account.username}`) +
            chalk.yellow(` | ${account.email}`) +
            chalk.magenta(` | 今日积分: ${stats.pointsToday?.toFixed(2)}`) +
            chalk.cyan(` | 总积分: ${stats.totalPoints?.toFixed(2)}`)
        );
      } catch (error) {
        account.status = chalk.red('错误');
        account.lastUpdate = getTimestamp();
        console.log(chalk.red(`[${getTimestamp()}] 账户 ${i + 1}: 错误 - ${error.message}`));
      }

      // 延迟 1 秒，避免请求过快
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }

    // 每 30 秒更新一次
    await new Promise((resolve) => setTimeout(resolve, 30000));
  }
};

// 启动程序
(async () => {
  try {
    await main();
  } catch (error) {
    console.error(chalk.red('程序错误:', error.message));
    process.exit(1);
  }
})();
