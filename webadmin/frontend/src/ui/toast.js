import { reactive } from "vue";

let seed = 0;
export const toasts = reactive([]);

function push(type, message) {
  const id = ++seed;
  toasts.push({ id, type, message });
  setTimeout(() => dismiss(id), 2800);
}

export function dismiss(id) {
  const i = toasts.findIndex((t) => t.id === id);
  if (i >= 0) toasts.splice(i, 1);
}

export const toast = {
  success: (m) => push("success", m),
  error: (m) => push("error", m),
  warning: (m) => push("warning", m),
  info: (m) => push("info", m),
};
