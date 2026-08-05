<script setup>
import { reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { Lock } from "@element-plus/icons-vue";
import { doLogin } from "../api";
import { login } from "../store";

const form = reactive({ password: "" });
const loading = ref(false);

async function submit() {
  if (!form.password) {
    ElMessage.warning("请输入管理密码");
    return;
  }
  loading.value = true;
  try {
    const token = await doLogin(form.password);
    login(token);
    ElMessage.success("欢迎回来");
  } catch (e) {
    ElMessage.error(e.message || "登录失败");
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="login-wrap">
    <div class="blob b1"></div>
    <div class="blob b2"></div>
    <div class="blob b3"></div>

    <div class="login-card">
      <div class="brand-row">
        <div class="logo">星</div>
        <div>
          <div class="name">StarTraveller</div>
          <div class="sub">星辰旅人 · 管理后台</div>
        </div>
      </div>

      <el-form @submit.prevent="submit">
        <el-form-item>
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入管理密码"
            size="large"
            :prefix-icon="Lock"
            show-password
            @keyup.enter="submit"
          />
        </el-form-item>
        <el-button
          class="login-btn"
          type="primary"
          size="large"
          :loading="loading"
          @click="submit"
        >进入后台</el-button>
      </el-form>

      <div class="tip">仅限管理员访问 · 会话基于 Token 认证</div>
    </div>
  </div>
</template>

<style scoped>
.login-wrap {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}
.blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.55;
  animation: float 9s ease-in-out infinite;
}
.b1 { width: 380px; height: 380px; background: rgba(99, 102, 241, 0.55); top: -120px; left: -80px; }
.b2 { width: 320px; height: 320px; background: rgba(168, 85, 247, 0.45); bottom: -100px; right: -60px; animation-delay: -3s; }
.b3 { width: 240px; height: 240px; background: rgba(34, 211, 238, 0.35); top: 40%; left: 62%; animation-delay: -6s; }
@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(24px, -28px) scale(1.06); }
}

.login-card {
  position: relative;
  z-index: 1;
  width: 380px;
  padding: 38px 36px 28px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 22px;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.35);
}
[data-theme="light"] .login-card { box-shadow: 0 24px 60px rgba(40, 50, 120, 0.18); }

.brand-row { display: flex; align-items: center; gap: 14px; margin-bottom: 26px; }
.logo {
  width: 48px; height: 48px; border-radius: 14px; flex-shrink: 0;
  background: linear-gradient(135deg, var(--accent), var(--accent-2), var(--accent-3));
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-size: 22px; font-weight: 700;
  box-shadow: 0 8px 24px rgba(99, 102, 241, 0.4);
}
.name { font-size: 20px; font-weight: 700; }
.sub { font-size: 12.5px; color: var(--text-muted); margin-top: 2px; }

.login-btn { width: 100%; margin-top: 4px; }
.tip { text-align: center; font-size: 12px; color: var(--text-muted); margin-top: 18px; }

@media (max-width: 480px) {
  .login-card { width: 92%; padding: 30px 24px 22px; }
}
</style>
