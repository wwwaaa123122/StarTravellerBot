import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { fileURLToPath, URL } from "node:url";

// 仅在构建时把重量级依赖 external 掉，走 CDN 全局变量
// 关键：format 必须为 iife，否则 Rollup output.globals 在 ESM 格式下不生效
function cdnExternalConfig() {
  let isBuild = false;
  return {
    name: "cdn-external-config",
    config(_, { command }) {
      isBuild = command === "build";
      if (isBuild) {
        return {
          build: {
            rollupOptions: {
              external: ["vue", "element-plus", "echarts"],
              output: {
                format: "iife",
                name: "StarTravellerAdmin",
                globals: {
                  vue: "Vue",
                  "element-plus": "ElementPlus",
                  echarts: "echarts",
                },
              },
            },
          },
        };
      }
    },
    // pre: 注入 CDN 资源到 <head> 最前面
    transformIndexHtml: {
      order: "pre",
      handler(html) {
        if (!isBuild) return html;
        return [
          {
            tag: "link",
            attrs: { rel: "stylesheet", href: "https://unpkg.com/element-plus@2.9.3/dist/index.css" },
            injectTo: "head-prepend",
          },
          {
            tag: "link",
            attrs: { rel: "stylesheet", href: "https://unpkg.com/element-plus@2.9.3/theme-chalk/dark/css-vars.css" },
            injectTo: "head-prepend",
          },
          {
            tag: "script",
            attrs: { src: "https://unpkg.com/vue@3.5.13/dist/vue.global.prod.js" },
            injectTo: "head-prepend",
          },
          {
            tag: "script",
            attrs: { src: "https://unpkg.com/element-plus@2.9.3/dist/index.full.min.js" },
            injectTo: "head-prepend",
          },
          {
            tag: "script",
            attrs: { src: "https://cdn.jsdelivr.net/npm/echarts@5.6.0/dist/echarts.min.js" },
            injectTo: "head-prepend",
          },
        ];
      },
    },
  };
}

// post: 移除 type="module" crossorigin，并把 app 脚本从 <head> 移到 </body> 之前
// （IIFE 立即执行，必须等 #app 挂载点存在后才能 mount）
function cdnExternalFixScript() {
  return {
    name: "cdn-external-fix-script",
    enforce: "post",
    transformIndexHtml(html) {
      const match = html.match(
        /<script type="module" crossorigin src="(\/admin\/static\/assets\/[^"]+)"><\/script>/
      );
      if (!match) return html;
      const src = match[1];
      html = html.replace(match[0], "");
      html = html.replace("</body>", `  <script src="${src}"></script>\n</body>`);
      return html;
    },
  };
}

export default defineConfig({
  plugins: [vue(), cdnExternalConfig(), cdnExternalFixScript()],
  base: "/admin/static/",
  build: {
    outDir: "../static",
    emptyOutDir: true,
    assetsDir: "assets",
    minify: "esbuild",
  },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    proxy: {
      "/admin/api": {
        target: "http://127.0.0.1:8765",
        changeOrigin: true,
      },
    },
  },
});