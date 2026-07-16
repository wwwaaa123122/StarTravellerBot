import { defineConfig } from 'vitepress'

// https://vitepress.dev/reference/site-config
export default defineConfig({
  base: '/StarTravellerBot/',
  srcDir: "docs",

  title: "星辰旅人BOT文档",
  description: "星辰旅人QQ开放平台BOT文档",
  lastUpdated: true,

  themeConfig: {
    // https://vitepress.dev/reference/default-theme-config
    nav: [
      { text: '首页', link: '/' },
      { text: '指南', link: '/guide/getting-started' },
      { text: '插件', link: '/plugins/introduction' },
      { text: 'AI模块', link: '/ai/chat' },
    ],

    sidebar: {
      '/guide/': [
        {
          text: '指南',
          items: [
            { text: '快速开始', link: '/guide/getting-started' },
            { text: '项目结构', link: '/guide/structure' },
            { text: '消息场景', link: '/guide/scenarios' },
          ]
        }
      ],
      '/plugins/': [
        {
          text: '插件系统',
          items: [
            { text: '插件开发', link: '/plugins/introduction' },
            { text: '内置插件', link: '/plugins/builtin' },
          ]
        }
      ],
      '/ai/': [
        {
          text: 'AI 模块',
          items: [
            { text: 'AI 对话', link: '/ai/chat' },
            { text: '角色系统', link: '/ai/roleplay' },
          ]
        }
      ],
      '/tools/': [
        {
          text: '工具模块',
          items: [
            { text: '概述', link: '/tools/overview' },
          ]
        }
      ],
      '/api/': [
        {
          text: 'API 参考',
          items: [
            { text: 'API 参考', link: '/api/reference' },
          ]
        }
      ],
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/wwwaaa123122/StarTravellerBot' }
    ],

    footer: {
      message: '基于 VitePress 构建',
      copyright: 'Copyright © 2024-2025 StarTravellerBot'
    }
  }
})