import { reactive } from "vue";

export const store = reactive({
  token: localStorage.getItem("st_token") || "",
  authenticated: !!localStorage.getItem("st_token"),
  view: "dashboard",
});

const VIEW_TITLES = {
  dashboard: "总览",
  users: "用户管理",
  memory: "记忆库",
  plugins: "插件管理",
  permissions: "权限管理",
  schedule: "定时任务",
  "ai-settings": "AI 设置",
  prompts: "Prompt 管理",
  settings: "系统设置",
};

export function viewTitle(view = store.view) {
  return VIEW_TITLES[view] || "总览";
}

export function login(token) {
  store.token = token;
  store.authenticated = true;
  localStorage.setItem("st_token", token);
  localStorage.setItem("st_user", "admin");
}

export function logout() {
  store.token = "";
  store.authenticated = false;
  localStorage.removeItem("st_token");
  localStorage.removeItem("st_user");
}