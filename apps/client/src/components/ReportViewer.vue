<template>
  <Teleport to="body">
    <div v-if="report" class="fixed inset-0 z-50 flex flex-col">
      <!-- Backdrop -->
      <div class="fixed inset-0 bg-black/60" @click="close"></div>

      <!-- Overlay content -->
      <div class="relative z-10 flex flex-col h-full">
        <!-- Header bar -->
        <div class="flex-shrink-0 flex items-center justify-between px-4 py-2 bg-[var(--theme-bg-primary)] border-b border-[var(--theme-border)]">
          <div class="flex items-center gap-2 min-w-0">
            <span class="text-lg">{{ report.icon }}</span>
            <span class="text-sm font-semibold text-[var(--theme-text-primary)] truncate">{{ report.name }}</span>
            <span class="text-xs text-[var(--theme-text-secondary)]">{{ report.sizeKb }} KB</span>
          </div>
          <button
            @click="close"
            class="p-1.5 rounded-lg hover:bg-[var(--theme-bg-tertiary)] transition-colors min-w-[36px] min-h-[36px] flex items-center justify-center"
            title="Close (Esc)"
          >
            <svg class="w-5 h-5 text-[var(--theme-text-secondary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- iframe -->
        <iframe
          :srcdoc="html"
          sandbox="allow-scripts allow-same-origin"
          class="flex-1 w-full border-0 bg-white"
        ></iframe>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue';
import type { ReportInfo } from '../types';

const props = defineProps<{
  report: ReportInfo | null;
  html: string;
}>();

const emit = defineEmits<{
  close: [];
}>();

const close = () => emit('close');

const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Escape' && props.report) close();
};

onMounted(() => document.addEventListener('keydown', handleKeydown));
onUnmounted(() => document.removeEventListener('keydown', handleKeydown));
</script>
