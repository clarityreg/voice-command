import { ref, onMounted, onUnmounted } from 'vue';
import type { ReportInfo, ProjectWithReports } from '../types';
import { API_BASE_URL } from '../config';

const projects = ref<ProjectWithReports[]>([]);
const selectedProject = ref<string>('');
const selectedReport = ref<ReportInfo | null>(null);
const reportHtml = ref<string>('');
const isLoading = ref(false);
const error = ref<string | null>(null);
let hasFetched = false;

/**
 * Build a script that intercepts all <a> clicks inside the iframe.
 * Relative links are resolved against the report's directory and loaded
 * via postMessage → parent fetches the content through the API.
 * file:// and absolute links are blocked entirely.
 */
function buildLinkInterceptor(reportDir: string): string {
  return `<script>
(function() {
  var reportDir = ${JSON.stringify(reportDir)};
  document.addEventListener('click', function(e) {
    var a = e.target.closest('a');
    if (!a) return;
    var href = a.getAttribute('href');
    if (!href) return;
    // Block file:// and absolute URLs
    if (/^(file:|https?:|mailto:)/.test(href)) {
      e.preventDefault();
      return;
    }
    // Skip anchors
    if (href.startsWith('#')) return;
    // Relative link — resolve against report directory
    e.preventDefault();
    var resolved = reportDir ? reportDir + '/' + href : href;
    // Normalize path (collapse ../ and ./)
    var parts = resolved.split('/');
    var stack = [];
    for (var i = 0; i < parts.length; i++) {
      if (parts[i] === '..') { stack.pop(); }
      else if (parts[i] !== '.' && parts[i] !== '') { stack.push(parts[i]); }
    }
    window.parent.postMessage({ type: 'report-navigate', path: stack.join('/') }, '*');
  }, true);
})();
<\/script>`;
}

export function useReports() {
  /** Handle postMessage from iframe for in-report navigation */
  function onIframeMessage(e: MessageEvent) {
    if (e.data?.type !== 'report-navigate') return;
    const path = e.data.path as string;
    if (!path || !selectedProject.value) return;
    loadReportByPath(path);
  }

  async function loadReportByPath(relativePath: string) {
    isLoading.value = true;
    error.value = null;
    try {
      const encodedPath = encodeURIComponent(relativePath);
      const res = await fetch(
        `${API_BASE_URL}/api/projects/${encodeURIComponent(selectedProject.value)}/report-content?path=${encodedPath}`
      );
      if (!res.ok) throw new Error(`Report not found: ${relativePath}`);
      const data = await res.json();
      reportHtml.value = injectInterceptor(data.html, relativePath);
    } catch (e: any) {
      error.value = e.message || 'Failed to load linked report';
    } finally {
      isLoading.value = false;
    }
  }

  function injectInterceptor(html: string, relativePath: string): string {
    // Get directory of the report for resolving relative links
    const dir = relativePath.includes('/') ? relativePath.substring(0, relativePath.lastIndexOf('/')) : '';
    const script = buildLinkInterceptor(dir);
    // Inject before </body> or at end
    if (html.includes('</body>')) {
      return html.replace('</body>', script + '</body>');
    }
    return html + script;
  }

  async function fetchProjects() {
    isLoading.value = true;
    error.value = null;
    try {
      const res = await fetch(`${API_BASE_URL}/api/projects`);
      if (!res.ok) throw new Error(`Server error: ${res.status}`);
      const data = await res.json();
      projects.value = data.projects || [];
      if (!selectedProject.value && projects.value.length > 0) {
        selectedProject.value = projects.value[0].name;
      }
      hasFetched = true;
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch projects';
    } finally {
      isLoading.value = false;
    }
  }

  async function ensureFetched() {
    if (!hasFetched) await fetchProjects();
  }

  function selectProject(name: string) {
    selectedProject.value = name;
    closeReport();
  }

  async function viewReport(report: ReportInfo) {
    isLoading.value = true;
    error.value = null;
    try {
      const encodedPath = encodeURIComponent(report.relativePath);
      const res = await fetch(
        `${API_BASE_URL}/api/projects/${encodeURIComponent(selectedProject.value)}/report-content?path=${encodedPath}`
      );
      if (!res.ok) throw new Error(`Failed to load report: ${res.status}`);
      const data = await res.json();
      reportHtml.value = injectInterceptor(data.html, report.relativePath);
      selectedReport.value = report;
    } catch (e: any) {
      error.value = e.message || 'Failed to load report';
    } finally {
      isLoading.value = false;
    }
  }

  function closeReport() {
    selectedReport.value = null;
    reportHtml.value = '';
  }

  function setupMessageListener() {
    window.addEventListener('message', onIframeMessage);
  }

  function teardownMessageListener() {
    window.removeEventListener('message', onIframeMessage);
  }

  return {
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
  };
}
