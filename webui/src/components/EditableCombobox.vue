<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, useId } from "vue";
import { ChevronDown, Check } from "@lucide/vue";

const props = withDefaults(defineProps<{
  modelValue: string;
  label: string;
  suggestions: string[];
  labels?: Record<string, string>;
  optional?: boolean;
  placeholder?: string;
  error?: string;
  hint?: string;
  disabled?: boolean;
}>(), { optional: false, disabled: false });
const emit = defineEmits<{
  "update:modelValue": [value: string];
  select: [value: string];
}>();
const id = useId();
const input = ref<HTMLInputElement | null>(null);
const open = ref(false);
const query = ref("");
const active = ref(-1);
const position = ref<Record<string, string>>({});
const custom = computed(() => props.modelValue !== "" && !props.suggestions.includes(props.modelValue));
const items = computed(() => {
  const values = props.optional ? ["", ...props.suggestions.filter(value => value !== "")] : props.suggestions;
  const filtered = values.filter(value => !query.value || `${value} ${props.labels?.[value] ?? ""}`.toLowerCase().includes(query.value.toLowerCase()));
  if (props.modelValue && !values.includes(props.modelValue)) filtered.push(props.modelValue);
  return [...new Set(filtered)];
});
function placeList() {
  const rect = input.value?.parentElement?.getBoundingClientRect();
  if (!rect) return;
  const below = window.innerHeight - rect.bottom - 12;
  const above = rect.top - 12;
  const height = Math.min(240, Math.max(below, above));
  position.value = {
    left: `${Math.max(8, Math.min(rect.left, window.innerWidth - rect.width - 8))}px`,
    width: `${rect.width}px`, maxHeight: `${height}px`,
    ...(below < 180 && above > below ? { bottom: `${window.innerHeight - rect.top + 5}px` } : { top: `${rect.bottom + 5}px` }),
  };
}
function closeList() { open.value = false; }
function handleScroll(event: Event) {
  if (!(event.target instanceof Element && event.target.closest(".combo-suggestions"))) closeList();
}
window.addEventListener("resize", closeList);
window.addEventListener("scroll", handleScroll, true);
onBeforeUnmount(() => {
  window.removeEventListener("resize", closeList);
  window.removeEventListener("scroll", handleScroll, true);
});
function show(all = true) { query.value = all ? "" : props.modelValue; placeList(); open.value = true; active.value = -1; }
function choose(value: string) {
  emit("update:modelValue", value);
  emit("select", value);
  open.value = false;
  input.value?.focus();
}
function handleInput(event: Event) {
  const value = (event.target as HTMLInputElement).value;
  emit("update:modelValue", value);
  query.value = value;
  placeList();
  open.value = true;
  active.value = -1;
}
function handleKey(event: KeyboardEvent) {
  if (event.isComposing || event.keyCode === 229) return;
  if (event.key === "ArrowDown" || event.key === "ArrowUp") {
    event.preventDefault();
    if (!open.value) show();
    if (items.value.length) {
      active.value = active.value < 0
        ? (event.key === "ArrowDown" ? 0 : items.value.length - 1)
        : (active.value + (event.key === "ArrowDown" ? 1 : -1) + items.value.length) % items.value.length;
      nextTick(() => document.getElementById(`${id}-option-${active.value}`)?.scrollIntoView({ block: "nearest" }));
    }
  } else if (event.key === "Enter") {
    event.preventDefault();
    choose(open.value && active.value >= 0 ? items.value[active.value] : props.modelValue);
  } else if (event.key === "Escape") {
    event.preventDefault(); open.value = false;
  } else if (event.key === "Tab") open.value = false;
}
</script>

<template>
  <div class="field editable-field">
    <div class="field-heading"><label :for="`${id}-input`">{{ label }}</label><small v-if="custom" class="custom-value">自定义</small></div>
    <div class="editable-combo">
      <div class="combo-control" :class="{ invalid: error }">
        <input
          :id="`${id}-input`" ref="input" :value="modelValue" :disabled="disabled"
          :placeholder="placeholder || (optional ? '服务默认（不发送）' : '选择或直接输入')"
          role="combobox" aria-autocomplete="list" :aria-expanded="open"
          :aria-controls="`${id}-list`" :aria-activedescendant="open && active >= 0 ? `${id}-option-${active}` : undefined"
          :aria-invalid="Boolean(error)" :aria-describedby="error || hint ? `${id}-help` : undefined"
          autocomplete="off" spellcheck="false" @input="handleInput" @keydown="handleKey" @blur="open = false"
        />
        <button type="button" class="combo-toggle" :disabled="disabled" :aria-label="`展开${label}建议`" @pointerdown.prevent @click="open ? open = false : (input?.focus(), show())"><ChevronDown :size="15" aria-hidden="true" /></button>
      </div>
      <Teleport to="body"><div v-if="open && items.length" :id="`${id}-list`" class="combo-suggestions" :style="position" role="listbox" :aria-label="`${label}建议`">
        <button v-for="(value, index) in items" :id="`${id}-option-${index}`" :key="value" type="button" tabindex="-1" role="option" :aria-selected="active === index" :class="{ active: active === index, 'custom-option': value && !suggestions.includes(value) }" @pointerdown.prevent @click="choose(value)">
          <span>{{ value === '' ? '服务默认（不发送）' : !suggestions.includes(value) ? `直接使用“${value}”` : value }}</span>
          <small v-if="labels?.[value]">{{ labels[value] }}</small><Check v-if="value === modelValue" :size="13" aria-hidden="true" />
        </button>
      </div></Teleport>
    </div>
    <small v-if="error || hint" :id="`${id}-help`" :class="error ? 'field-error' : 'field-hint'">{{ error || hint }}</small>
  </div>
</template>
