<script setup lang="ts">
import { computed, ref, watch, useId } from "vue";
import { ArrowLeftRight } from "@lucide/vue";
import EditableCombobox from "./EditableCombobox.vue";
import { resolveParameters } from "../parameters";
import type { AppConfig, AppMode, ParameterDraft } from "../types/image";

const props = withDefaults(defineProps<{
  modelValue: ParameterDraft;
  config: AppConfig | null;
  mode?: AppMode;
  errors?: Record<string, string>;
}>(), { mode: "generate" });
const emit = defineEmits<{ "update:modelValue": [value: ParameterDraft] }>();
const id = useId();
const resolution = computed(() => resolveParameters(props.modelValue, props.config, props.mode));
const errors = computed(() => ({ ...resolution.value.errors, ...props.errors }));
const width = ref("");
const height = ref("");
const outputOpen = ref(Boolean(props.modelValue.background || props.modelValue.output_compression || props.modelValue.input_fidelity));
const advancedOpen = ref(Boolean(props.modelValue.style || props.modelValue.response_format || props.modelValue.timeout || props.modelValue.extra_body !== "{}"));
const maxN = computed(() => props.config?.max_n ?? 2);
const labels = { auto: "自动", low: "低", medium: "中", high: "高", transparent: "透明", opaque: "不透明", natural: "自然", vivid: "鲜明" };
watch(() => props.modelValue.size, value => {
  const match = /^(\d*)x(\d*)$/.exec(value);
  if (match) { width.value = match[1]; height.value = match[2]; }
  else { width.value = ""; height.value = ""; }
}, { immediate: true });
watch(errors, value => {
  if (["background", "output_compression", "input_fidelity", "moderation"].some(key => value[key])) outputOpen.value = true;
  if (["extra_body", "style", "response_format", "timeout"].some(key => value[key])) advancedOpen.value = true;
});
const dimensions = computed(() => {
  if (!/^[1-9]\d*x[1-9]\d*$/.test(props.modelValue.size)) return "";
  const w = Number(width.value), h = Number(height.value);
  if (!Number.isSafeInteger(w) || !Number.isSafeInteger(h)) return "";
  const gcd = (a: number, b: number): number => b ? gcd(b, a % b) : a;
  const factor = gcd(w, h);
  return `${w / factor}:${h / factor} · ${(w * h / 1e6).toFixed(2)} 百万像素`;
});
function update(key: keyof ParameterDraft, value: string) { emit("update:modelValue", { ...props.modelValue, [key]: value }); }
function updateDimension(key: "width" | "height", event: Event) {
  (key === "width" ? width : height).value = (event.target as HTMLInputElement).value;
  update("size", `${width.value}x${height.value}`);
}
function swap() { if (dimensions.value) update("size", `${height.value}x${width.value}`); }
</script>

<template>
  <div class="parameter-controls">
    <div class="section-heading"><h3>基本参数</h3><small>每项可选，也可直接输入</small></div>
    <div class="parameter-grid">
      <EditableCombobox class="parameter-full" :model-value="modelValue.model" label="模型" :suggestions="config?.models ?? []" optional :placeholder="`服务默认：${config?.default_model ?? '加载中'}`" :error="errors.model" @update:model-value="update('model', $event)" />
      <div class="parameter-full">
        <EditableCombobox :model-value="modelValue.size" label="尺寸" :suggestions="config?.sizes ?? []" :labels="labels" :error="errors.size" @update:model-value="update('size', $event)" />
        <div class="size-dimensions"><label :for="`${id}-width`">宽<input :id="`${id}-width`" :value="width" inputmode="numeric" :disabled="modelValue.size === 'auto'" @input="updateDimension('width', $event)" /></label><span>×</span><label :for="`${id}-height`">高<input :id="`${id}-height`" :value="height" inputmode="numeric" :disabled="modelValue.size === 'auto'" @input="updateDimension('height', $event)" /></label><button type="button" class="tool-button" :disabled="!dimensions" aria-label="交换宽高" @click="swap"><ArrowLeftRight :size="14" /></button></div>
        <small class="field-hint">{{ modelValue.size === 'auto' ? '由服务决定画幅' : dimensions || '输入宽高；真实尺寸范围由模型决定' }}</small>
        <div class="size-shortcuts"><button v-for="size in ['1024x1024', '1536x1024', '1024x1536', '1536x864']" :key="size" type="button" @click="update('size', size)">{{ size }}</button></div>
      </div>
      <EditableCombobox :model-value="modelValue.quality" label="质量" :suggestions="config?.qualities ?? []" :labels="labels" :error="errors.quality" @update:model-value="update('quality', $event)" />
      <EditableCombobox :model-value="modelValue.output_format" label="格式" :suggestions="config?.formats ?? []" :error="errors.output_format" @update:model-value="update('output_format', $event)" />
      <div class="field parameter-full"><div class="field-heading"><label :for="`${id}-count`">数量</label><small>本地上限 {{ maxN }}</small></div><input :id="`${id}-count`" :value="modelValue.n" inputmode="numeric" :aria-invalid="Boolean(errors.n)" :aria-describedby="errors.n ? `${id}-count-error` : undefined" @input="update('n', ($event.target as HTMLInputElement).value)" /><small v-if="errors.n" :id="`${id}-count-error`" class="field-error">{{ errors.n }}</small></div>
    </div>
    <details class="parameter-section" :open="outputOpen" @toggle="outputOpen = ($event.target as HTMLDetailsElement).open">
      <summary>输出与编辑设置 <small>背景、压缩、保真度、审查</small></summary>
      <div class="parameter-grid">
        <EditableCombobox class="parameter-full" :model-value="modelValue.background" label="背景" :suggestions="config?.backgrounds ?? []" :labels="labels" optional :error="errors.background" hint="透明背景需模型支持，并使用 PNG / WebP。" @update:model-value="update('background', $event)" />
        <div class="field parameter-full"><label :for="`${id}-compression`">输出压缩参数</label><input :id="`${id}-compression`" :value="modelValue.output_compression" inputmode="numeric" placeholder="服务默认（不发送）" :aria-invalid="Boolean(errors.output_compression)" @input="update('output_compression', ($event.target as HTMLInputElement).value)" /><small :class="errors.output_compression ? 'field-error' : 'field-hint'">{{ errors.output_compression || (modelValue.output_format === 'png' ? 'PNG 本次不发送此项，填写的草稿值仍保留。' : '0–100；仅 JPEG / WebP 生效。留空使用默认。') }}</small></div>
        <EditableCombobox v-if="mode === 'edit'" class="parameter-full" :model-value="modelValue.input_fidelity" label="输入图保真度" :suggestions="config?.input_fidelities ?? []" :labels="labels" optional :error="errors.input_fidelity" hint="控制输入图特征保留程度，需模型支持。" @update:model-value="update('input_fidelity', $event)" />
        <EditableCombobox class="parameter-full" :model-value="modelValue.moderation" label="审查设置" :suggestions="config?.moderations ?? []" :labels="labels" optional :error="errors.moderation" hint="服务默认表示不指定此参数，上游仍按自己的规则处理。" @update:model-value="update('moderation', $event)" />
      </div>
    </details>
    <details class="parameter-section" :open="advancedOpen" @toggle="advancedOpen = ($event.target as HTMLDetailsElement).open">
      <summary>高级与扩展 <small>按所用服务支持范围填写</small></summary>
      <div class="parameter-grid">
        <EditableCombobox v-if="mode === 'generate'" class="parameter-full" :model-value="modelValue.style" label="风格" :suggestions="config?.styles ?? []" :labels="labels" optional :error="errors.style" hint="仅在模型支持该参数时指定。" @update:model-value="update('style', $event)" />
        <EditableCombobox class="parameter-full" :model-value="modelValue.response_format" label="响应形式" :suggestions="config?.response_formats ?? []" optional :error="errors.response_format" hint="需模型支持；留空由服务决定。" @update:model-value="update('response_format', $event)" />
        <div class="field parameter-full"><label :for="`${id}-timeout`">请求超时（秒）</label><input :id="`${id}-timeout`" :value="modelValue.timeout" inputmode="decimal" placeholder="服务默认" :aria-invalid="Boolean(errors.timeout)" @input="update('timeout', ($event.target as HTMLInputElement).value)" /><small v-if="errors.timeout" class="field-error">{{ errors.timeout }}</small></div>
        <div class="field parameter-full"><label :for="`${id}-extra`">扩展参数 JSON</label><textarea :id="`${id}-extra`" :value="modelValue.extra_body" class="parameter-json" rows="5" spellcheck="false" :aria-invalid="Boolean(errors.extra_body)" @input="update('extra_body', ($event.target as HTMLTextAreaElement).value)" /><small :class="errors.extra_body ? 'field-error' : 'field-hint'">{{ errors.extra_body || '只填写服务支持的额外图像参数；已有参数在对应控件中修改。' }}</small></div>
      </div>
    </details>
    <details class="parameter-section request-preview"><summary>查看本次有效参数</summary><pre v-if="!Object.keys(resolution.errors).length">{{ JSON.stringify(resolution.options, null, 2) }}</pre><p v-else class="field-error">请先调整标出的参数。</p></details>
  </div>
</template>
