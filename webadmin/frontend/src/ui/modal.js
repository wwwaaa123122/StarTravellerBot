import { reactive } from "vue";

export const confirmState = reactive({
  visible: false,
  title: "确认",
  message: "",
  confirmText: "确定",
  cancelText: "取消",
  danger: false,
  _resolve: null,
});

export function confirm(opts = {}) {
  return new Promise((resolve) => {
    Object.assign(confirmState, {
      visible: true,
      title: opts.title ?? "确认",
      message: opts.message ?? "",
      confirmText: opts.confirmText ?? "确定",
      cancelText: opts.cancelText ?? "取消",
      danger: !!opts.danger,
      _resolve: resolve,
    });
  });
}

export function settleConfirm(result) {
  const r = confirmState._resolve;
  confirmState.visible = false;
  confirmState._resolve = null;
  if (r) r(result);
}
