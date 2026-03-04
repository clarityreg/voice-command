<template>
  <div class="flex flex-col flex-1 overflow-hidden">
    <!-- Top bar: project selector + refresh -->
    <div class="flex items-center gap-2 px-3 py-2 bg-[var(--theme-bg-primary)] border-b border-[var(--theme-border)]">
      <select
        v-model="selectedProject"
        @change="selectProject(selectedProject)"
        class="text-sm px-2 py-1.5 rounded-md bg-[var(--theme-bg-tertiary)] text-[var(--theme-text-primary)] border border-[var(--theme-border)] focus:outline-none focus:ring-1 focus:ring-[var(--theme-primary)]"
      >
        <option v-for="p in projects" :key="p.name" :value="p.name">
          {{ p.name }}
        </option>
      </select>
      <button
        @click="fetchProjects"
        :disabled="isLoading"
        class="p-1.5 rounded-md hover:bg-[var(--theme-bg-tertiary)] transition-colors text-[var(--theme-text-secondary)] disabled:opacity-50"
        title="Refresh reports"
      >
        <svg class="w-4 h-4" :class="{ 'animate-spin': isLoading }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
      </button>
      <span v-if="currentReports.length" class="text-xs text-[var(--theme-text-secondary)] ml-auto">
        {{ currentReports.length }} report{{ currentReports.length !== 1 ? 's' : '' }}
      </span>
    </div>

    <!-- Error banner -->
    <div v-if="error" class="mx-3 mt-2 px-3 py-2 rounded-md bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 text-sm">
      {{ error }}
    </div>

    <!-- Loading state -->
    <div v-if="isLoading && !projects.length" class="flex-1 flex items-center justify-center text-[var(--theme-text-secondary)]">
      <span class="text-sm">Loading projects...</span>
    </div>

    <!-- No projects -->
    <div v-else-if="!projects.length" class="flex-1 flex flex-col items-center justify-center gap-2 text-[var(--theme-text-secondary)] px-4">
      <span class="text-3xl">📁</span>
      <span class="text-sm text-center">No projects configured. Create <code class="text-xs bg-[var(--theme-bg-tertiary)] px-1 py-0.5 rounded">~/.claude/prp-projects.json</code></span>
    </div>

    <!-- No reports for current project -->
    <div v-else-if="!currentReports.length" class="flex-1 flex flex-col items-center justify-center gap-2 text-[var(--theme-text-secondary)] px-4">
      <span class="text-3xl">📄</span>
      <span class="text-sm text-center">No reports found. Run <code class="text-xs bg-[var(--theme-bg-tertiary)] px-1 py-0.5 rounded">/prp-doctor</code> or <code class="text-xs bg-[var(--theme-bg-tertiary)] px-1 py-0.5 rounded">/prp-coverage</code> to generate reports.</span>
    </div>

    <!-- Report cards grid -->
    <div v-else class="flex-1 overflow-y-auto p-3">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        <button
          v-for="report in currentReports"
          :key="report.relativePath"
          @click="viewReport(report)"
          class="text-left p-4 rounded-lg border border-[var(--theme-border)] bg-[var(--theme-bg-primary)] hover:border-[var(--theme-primary)] hover:shadow-md transition-all group"
        >
          <div class="flex items-start gap-3">
            <span class="text-2xl flex-shrink-0">{{ report.icon }}</span>
            <div class="min-w-0 flex-1">
              <div class="font-medium text-sm text-[var(--theme-text-primary)] group-hover:text-[var(--theme-primary)] truncate">
                {{ report.name }}
              </div>
              <div class="flex items-center gap-2 mt-1 text-xs text-[var(--theme-text-secondary)]">
                <span>{{ report.sizeKb }} KB</span>
                <span>·</span>
                <span>{{ report.modified }}</span>
              </div>
              <span
                :class="badgeClasses(report.badgeCls)"
                class="inline-block mt-2 px-2 py-0.5 rounded-full text-xs font-medium"
              >
                {{ report.badge }}
              </span>
            </div>
          </div>
        </button>
      </div>
    </div>

    <!-- Report viewer overlay -->
    <ReportViewer
      :report="selectedReport"
      :html="reportHtml"
      @close="closeReport"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue';
import { useReports } from '../composables/useReports';
import ReportViewer from './ReportViewer.vue';

const {
  projects,
  selectedProject,
  selectedReport,
  reportHtml,
  isLoading,
  error,
  fetchProjects,
  ensureFetched,
  selectProject,
  viewReport,
  closeReport,
  setupMessageListener,
  teardownMessageListener,
} = useReports();

const currentReports = computed(() => {
  const project = projects.value.find(p => p.name === selectedProject.value);
  return project?.reports || [];
});

function badgeClasses(cls: string) {
  switch (cls) {
    case 'fresh':  return 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300';
    case 'recent': return 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300';
    case 'stale':  return 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300';
    default:       return 'bg-gray-100 dark:bg-gray-900/30 text-gray-700 dark:text-gray-300';
  }
}

onMounted(() => {
  ensureFetched();
  setupMessageListener();
});
onUnmounted(() => teardownMessageListener());
</script>
