# 💰 xinxin-fanli (xinxin返利)

[![AstrBot](https://img.shields.io/badge/AstrBot-v4.x-blue)](https://github.com/AstrBotDevs/AstrBot)
[![Python](https://img.shields.io/badge/Python-3.8+-yellow)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

这是一个专为 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 框架开发的电商返利插件。完美适配 **`openclaw-weixin` (个人微信官方通道)** 和常规 QQ 平台。

只需向机器人发送包含淘宝或京东的商品文案、口令或链接，机器人便会自动解析，并极速返回带有你专属推广位的优惠信息与返利链接！

## ✨ 核心特性

- 🛍️ **双端平台支持**：支持淘宝/天猫（基于折淘客API）与京东（基于折京客 + 京推推API）。
- 💬 **微信个人号专属优化**：完美兼容 `openclaw-weixin` 通道，内置事件拦截（`stop_event`）机制。一旦识别到商品链接，返回返利信息后自动截断，**防止后端的 LLM (大语言模型) 出现乱回答或幻觉**。
- ⚙️ **全可视化配置**：无需手动修改代码或 JSON 文件！采用 AstrBot V4 最新标准，直接在 WebUI 管理面板中填写 API 秘钥，保存即时生效。
- ⚡ **异步极速响应**：底层采用 `aiohttp` 异步网络请求，附带严谨的超时处理，绝不卡死主线程，保证微信回复的及时性。

## 📦 安装指南

1. 进入你的 AstrBot 插件目录：
   ```bash
   cd AstrBot/data/plugins
2. 克隆本仓库到插件目录（注意文件夹命名格式）：
Bash
git clone [https://github.com/你的GitHub用户名/xinxin_fanli.git](https://github.com/你的GitHub用户名/xinxin_fanli.git) astrbot_plugin_xinxin_fanli
3. 进入插件目录并安装依赖：
Bash
cd astrbot_plugin_xinxin_fanli
pip install -r requirements.txt
4. 重启 AstrBot 让插件生效。

🛠️ 配置说明
得益于 AstrBot 的动态可视化配置能力，你只需：

1. 登录 AstrBot 的 Web 管理控制台。

2. 点击左侧菜单的 插件管理。

3. 找到 xinxin返利，点击右侧的 ⚙️ 配置按钮。

4. 在弹出的表单中填入你的联盟与 API 参数：

淘宝侧：折淘客 AppKey、SID、淘宝联盟 PID (mm_xxx_xxx_xxx)、渠道 ID。

京东侧：折京客 AppKey、京东联盟 ID、推广位 ID。

京推推：AppID、AppKey（用于生成京东优惠口令）。

点击保存，配置立即热重载生效！

(注：如果你还没有相关 API 秘钥，请前往 折淘客、京东联盟 和 京推推 注册申请。)

💻 使用示例
场景：用户在微信中发了一段带有淘口令的种草文案

用户：这个口红绝了！快买！ 39￥ CZ3457 L9kE3b12345￥ https://www.google.com/search?q=https://m.tb.cn/h.g12345

🤖 机器人：
✨【淘宝】MAC魅可经典子弹头口红
💰券后价: ￥139.00
🔗领券地址: https://www.google.com/search?q=https://s.click.taobao.com/...
📝口令: ￥abCdE12345￥

🤝 贡献与反馈
如果你在使用过程中遇到任何 Bug，或者有添加拼多多、抖音等平台返利的需求，欢迎提交 Issue 或 Pull Request！

📄 开源协议
本项目基于 MIT License 协议开源。
