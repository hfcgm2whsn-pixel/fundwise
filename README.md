# 💰 FundWise - 基金学习助手

一个 AI 原生的基金学习助手，让零基础用户通过自然对话学习基金知识、跟踪市场动态、获取个性化建议。

## ✨ 功能特色

| 功能 | 说明 |
|------|------|
| 💬 **智能问答** | 用大白话回答任何基金问题，举例子帮助理解 |
| 📈 **查涨跌** | 输入基金代码，实时查看净值和涨跌幅，AI 通俗解读 |
| 🔗 **视频总结** | 粘贴小红书/抖音/B站/微信链接，AI 自动总结核心要点 |
| 📚 **学习计划** | 根据你的水平定制个性化基金学习路线 |
| 📊 **走势分析** | 查看基金历史走势图，AI 分析趋势和波动特征 |

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/your-username/FundWise.git
cd FundWise
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 API Key

复制环境变量模板并填入你的 DeepSeek API Key：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

> 💡 **如何获取 DeepSeek API Key？**
> 1. 访问 [DeepSeek 开放平台](https://platform.deepseek.com/)
> 2. 注册/登录账号
> 3. 进入「API Keys」页面
> 4. 点击「创建 API Key」
> 5. 复制生成的 Key 填入 `.env` 文件
>
> 新用户通常有免费额度，足够日常使用。

### 4. 启动应用

```bash
streamlit run app.py
```

浏览器会自动打开 `http://localhost:8501`

## 📁 项目结构

```
FundWise/
├── app.py              # Streamlit 主界面
├── fund_api.py         # 基金数据模块（天天基金 API）
├── ai_service.py       # AI 服务模块（DeepSeek API）
├── video_parser.py     # 视频/图文链接解析模块
├── requirements.txt    # Python 依赖
├── .env.example        # 环境变量模板
└── README.md           # 项目说明
```

## 🔧 技术栈

- **前端**：[Streamlit](https://streamlit.io/) - Python 快速 Web 框架
- **AI 模型**：[DeepSeek](https://platform.deepseek.com/) - 大语言模型 API
- **基金数据**：天天基金（eastmoney.com）公开 API
- **视频解析**：BeautifulSoup4 - 网页内容提取

## 📖 使用指南

### 智能问答
直接在对话框中输入任何基金相关问题，例如：
- "什么是基金净值？"
- "ETF 和普通基金有什么区别？"
- "定投亏了要不要停？"

### 查涨跌
输入 6 位基金代码（如 `110022`），即可查看最新净值和涨跌幅，并获得 AI 通俗解读。

也可以输入关键词（如"沪深300"）搜索相关基金。

### 视频总结
粘贴小红书、抖音、B站、微信公众号的链接，AI 会自动提取内容并生成结构化总结。

### 学习计划
选择你的基金学习水平（零基础/入门/进阶），AI 会为你量身定制学习路线。

### 走势分析
输入基金代码，查看近 30 天净值走势图，AI 会分析趋势和波动特征。

## ⚠️ 免责声明

- 本项目仅供学习和研究使用，**不构成任何投资建议**
- AI 生成的内容可能存在错误，请以官方信息为准
- 基金投资有风险，投资需谨慎
- 数据来源于公开 API，可能存在延迟

## 📄 开源协议

[MIT License](LICENSE)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 发起 Pull Request
