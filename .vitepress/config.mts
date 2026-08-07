import { defineConfig } from 'vitepress'

// VitePress 2.0.0-alpha.18 配置文件
// 必须放在 .vitepress/ 目录下（VitePress 硬编码路径）
// 源 Markdown 文件在 docs/ 目录（由 srcDir 指定）

export default defineConfig({
  base: '/',
  srcDir: "docs",

  title: "星辰旅人BOT文档",
  description: "星辰旅人QQ开放平台BOT文档",
  lastUpdated: true,

  themeConfig: {
    nav: [
      { text: '首页', link: '/' },
      { text: '快速开始', link: '/guide/getting-started' },
    ],

    sidebar: [{
      text: '快速开始',
      items: [
        { text: '快速开始', link: '/guide/getting-started' },
        { text: '消息场景', link: '/guide/scenarios' },
        { text: '项目结构', link: '/guide/structure' },
        { text: 'AI 对话', link: '/ai/chat' },
        { text: '角色系统', link: '/ai/roleplay' },
        { text: '插件开发', link: '/plugins/introduction' },
        { text: '内置插件', link: '/plugins/builtin' },
        { text: '工具概述', link: '/tools/overview' },
        { text: 'Web 管理后台', link: '/tools/webadmin' },
        { text: 'API 参考', link: '/api/reference' },
      ]
    }],

    socialLinks: [
      { icon: 'github', link: 'https://github.com/wwwaaa123122/StarTravellerBot' }
    ],

    footer: {
      message: '基于 VitePress 构建',
      copyright: 'Copyright © 2024-2025 StarTravellerBot'
    }
  }
})
