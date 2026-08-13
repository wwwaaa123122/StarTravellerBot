<script setup>
defineProps({
  modelValue: { type: String, default: "" },
  placeholder: String,
  rows: { type: [Number, String], default: 3 },
});
const emit = defineEmits(["update:modelValue"]);
</script>

<template>
  <textarea
    class="ui-textarea"
    :rows="rows"
    :value="modelValue"
    :placeholder="placeholder"
    @input="emit('update:modelValue', $event.target.value)"
  ></textarea>
</template>

<style scoped>
.ui-textarea {
  width: 100%;
  border: 1px solid var(--line-strong);
  border-radius: 9px;
  background: var(--surface);
  color: var(--ink);
  font-family: var(--font-sans);
  font-size: 13.5px;
  line-height: 1.7;
  padding: 10px 12px;
  resize: vertical;
  outline: none;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.ui-textarea:focus {
  border-color: var(--vermilion);
  box-shadow: 0 0 0 3px rgba(192, 57, 43, 0.12);
}
.ui-textarea::placeholder { color: var(--ink-3); }
</style>
