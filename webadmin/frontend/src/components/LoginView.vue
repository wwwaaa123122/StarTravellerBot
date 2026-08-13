<script setup>
import { reactive, ref } from "vue";
import { doLogin } from "../api";
import { login } from "../store";
import { toast } from "../ui/toast";
import UiInput from "./ui/UiInput.vue";
import UiButton from "./ui/UiButton.vue";
import Icon from "./Icon.vue";

const form = reactive({ password: "" });
const loading = ref(false);

async function submit() {
  if (!form.password) {
    toast.warning("请输入管理密码");
    return;
  }
  loading.value = true;
  try {
    const token = await doLogin(form.password);
    login(token);
    toast.success("欢迎回来，旅人");
  } catch (e) {
    toast.error(e.message || "登录失败");
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="login-wrap">
    <div class="login-bg" aria-hidden="true"></div>

    <div class="login-card">
      <div class="seal" aria-hidden="true">旅</div>
      <h1 class="title">星辰旅人</h1>
      <p class="subtitle">管理后台</p>

      <form class="login-form" @submit.prevent="submit">
        <UiInput
          v-model="form.password"
          type="password"
          size="lg"
          show-password
          prefix-icon="lock"
          placeholder="请输入管理密码"
          @enter="submit"
        />
        <UiButton class="login-btn" size="lg" full :loading="loading" @click="submit">
          进入后台
        </UiButton>
      </form>

      <p class="tip">仅限管理员访问 · 会话基于 Token 认证</p>
    </div>

    <div class="footer-note" aria-hidden="true">
      <Icon name="star" :size="12" />
      星を旅する者
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

/* 纸感 + 和纹背景（市松纹） */
.login-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    radial-gradient(34rem 34rem at 12% 8%, rgba(192, 57, 43, 0.05), transparent 60%),
    radial-gradient(36rem 36rem at 92% 88%, rgba(42, 58, 85, 0.07), transparent 62%),
    url("data:image/svg+xml,%3Csvg width='28' height='28' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M14 0h14v14H14zM0 14h14v14H0z' fill='%232a3a55' fill-opacity='0.03'/%3E%3C/svg%3E");
}

.login-card {
  position: relative;
  z-index: 1;
  width: 384px;
  max-width: 92vw;
  padding: 40px 38px 30px;
  text-align: center;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 16px;
  box-shadow: var(--shadow-pop);
}

.seal {
  width: 56px;
  height: 56px;
  margin: 0 auto 18px;
  border-radius: 50%;
  background: var(--vermilion);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-serif);
  font-size: 30px;
  font-weight: 700;
  box-shadow: 0 6px 20px rgba(192, 57, 43, 0.35);
}

.title {
  margin: 0;
  font-family: var(--font-serif);
  font-size: 25px;
  font-weight: 700;
  letter-spacing: 6px;
  text-indent: 6px;
  color: var(--ink);
}
.subtitle {
  margin: 8px 0 28px;
  font-size: 11px;
  color: var(--ink-3);
  letter-spacing: 6px;
  text-indent: 6px;
}

.login-form { display: flex; flex-direction: column; gap: 16px; }
.login-btn { letter-spacing: 4px; font-weight: 600; }

.tip {
  margin: 22px 0 0;
  font-size: 11.5px;
  color: var(--ink-3);
}

.footer-note {
  position: absolute;
  bottom: 18px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--ink-3);
  letter-spacing: 2px;
  font-family: var(--font-serif);
}

@media (prefers-reduced-motion: reduce) {
  .login-bg { animation: none; }
}
</style>
