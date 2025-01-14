# Depined 自动连接工具

一个 Node.js 应用程序，用于自动维护与 Depined 平台的连接并跟踪收益。


## 简介

DepinedBot 是一个基于 Node.js 和 Python 的自动化脚本，旨在帮助用户管理多个 Depined 平台账户，自动连接、获取收益信息并记录日志。通过该工具，用户能够在多个账户之间进行切换和监控，方便地追踪账户的实时收益。

## 功能

- 自动管理和连接多个 Depined 账户
- 实时获取并显示收益信息
- 自动记录账户状态、收益数据和日志
- 支持多种代理配置
- 美观的控制台输出，支持多种颜色标记日志级别
- 自动定时更新数据

## 安装要求

- **Python 版本**：Python 3.7 或更高版本

## 注册

在使用此工具之前，你需要在 Depined 平台上注册：

1. 访问 [Depined 平台](https://app.depined.org/onboarding)
2. 在注册过程中使用以下推荐码：
```
PDhuXUdms9as
```

**重要提示**：该推荐码有 5 人使用限制。如果无法使用，说明已经达到最大使用人数。

## 配置


3. 将你的 JWT Token 一行一个地添加到 `tokens.txt` 文件中：
```
your_jwt_token_1
your_jwt_token_2
```

![image](https://github.com/user-attachments/assets/f33c5809-8fe9-40a6-aa72-cf08ecbaff5a)
4.（可选）代理编辑proxy.txt
```
http://user:pass@127.0.0.1:1080
socks5://user:pass@127.0.0.1:1080
```
   
## 使用方式

克隆存储库：

```bash
git clone https://github.com/ziqing888/Depined-BOT.git
cd Depined-BOT
```
安装依赖
```bash
pip install -r requirements.txt
```
运行脚本：
```bash
python3 bot.py
```
退出程序
可以使用以下方式安全退出脚本：

Ctrl + C：手动中断程序
SIGTERM：通过发送终止信号退出程序
程序会自动清理所有挂起的任务，并记录退出日志。

免责声明
本工具仅用于教育和学习目的，使用时请遵守 Depined 的服务条款。
请确保在符合相关法律的前提下使用此脚本。
支持
如需帮助或报告问题，请访问：

Telegram 频道：https://t.me/ksqxszq


