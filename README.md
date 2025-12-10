AT-Spider丨Telegram 资源自动抓取与转存脚本
🎯 项目简介
这是一个非常强大且专业的 Telegram 资源自动抓取与转存脚本，专为搭建个人影视库（NAS 或 TVBox）而设计，实现"全自动追剧"功能。此容器使用的是TG群AList Tvbox里两位大神开发的py脚本生成。

感谢两位大神:我就问这瓜保熟不、tcxp 提供的py脚本

🔧 核心功能
📥 自动抓取
​监控指定 Telegram 频道：实时监听目标频道的最新消息
​智能识别云盘链接：自动抓取天翼、百度、UC、123 等主流云盘链接
​资源标题清洗：自动清理和规范化资源标题，去除无用字符
🗂️ 智能处理
​自动去重：智能识别重复资源，避免重复转存
​资源分类：根据关键词自动分类（如电影、电视剧、动漫等）
​元数据提取：从标题中提取集数、分辨率、编码格式等信息
🔄 自动转存
​推送到 Alist-TVBox 服务器：将清洗后的资源链接自动推送到您的 Alist 服务器
​多平台支持：支持主流网盘，适配 TVBox 等播放器
​实时通知：发送转存成功/失败通知
🏗️ 技术架构
核心技术栈
​编程语言：Python
​依赖框架：Telethon（Telegram API 客户端）
​容器化：Docker
​异步处理：异步 I/O 提高效率
部署方式 compose.yaml
version: '3.8'
services:
  bot:
    image: xudahua520/at-spider:latest
    container_name: at-spider
    restart: unless-stopped
    ports:
      - "8877:8877"
    volumes:
      - ./data:/app/data
    environment:
      - TZ=Asia/Shanghai
