<script setup lang="ts">
import { onBeforeUnmount, onMounted } from "vue";
import { X } from "@lucide/vue";

const props = defineProps<{
  message: string;
}>();

const emit = defineEmits<{
  dismiss: [];
}>();

let timeoutId: number | undefined;

onMounted(() => {
  timeoutId = window.setTimeout(() => {
    emit("dismiss");
  }, 6500);
});

onBeforeUnmount(() => {
  if (timeoutId) {
    window.clearTimeout(timeoutId);
  }
});
</script>

<template>
  <div class="error-toast" role="alert" aria-live="assertive">
    <span>{{ props.message }}</span>
    <button type="button" aria-label="关闭错误提示" @click="emit('dismiss')">
      <X :size="16" aria-hidden="true" />
    </button>
  </div>
</template>
