---
# https://vitepress.dev/reference/default-theme-home-page
layout: home

hero:
  name: "星辰旅人 BOT"
  text: "QQ 开放平台机器人"
  tagline: 基于 botpy SDK，支持 AI 对话、角色扮演、丰富插件系统
  image:
    src: /logo.png
    alt: 星辰旅人
  actions:
    - theme: brand
      text: 快速开始
      link: /guide/getting-started
    - theme: alt
      text: GitHub
      link: https://github.com/wwwaaa123122/StarTravellerBot

features:
  - icon: 🤖
    title: 多场景覆盖
    details: 支持 QQ 单聊、群聊@机器人、频道私信、频道@机器人，全方位接入
  - icon: 🧠
    title: AI 智能对话
    details: 集成 DeepSeek / Gemini 多模型，支持上下文记忆和角色扮演
  - icon: 🔌
    title: 插件系统
    details: 动态加载插件架构，轻松扩展签到、天气、Ping 等实用功能
  - icon: 💾
    title: RAG 记忆
    details: 基于 bigram TF-IDF 的检索增强生成，让机器人记住历史对话
  - icon: 🎭
    title: 角色系统
    details: 内置傲娇/冷酷/默认角色，支持用户自定义角色创建
  - icon: ⏰
    title: 后台任务
    details: 支持插件注册后台定时任务，如定时群发早安消息
---