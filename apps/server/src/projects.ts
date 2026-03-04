import { resolve, join } from 'path';
import { statSync, readdirSync, existsSync } from 'fs';

// ── Types ───────────────────────────────────────────────────────────────────

export interface ProjectConfig {
  name: string;
  path: string;
}

export interface ReportInfo {
  name: string;
  icon: string;
  relativePath: string;
  sizeKb: number;
  modified: string;
  badge: string;
  badgeCls: 'fresh' | 'recent' | 'stale';
}

export interface ProjectWithReports {
  name: string;
  path: string;
  reports: ReportInfo[];
}

// ── Known report locations (ported from scripts/reports-hub.py) ─────────────

const KNOWN_REPORTS = [
  { name: 'Reports Hub',           icon: '🏠', path: '.claude/PRPs/reports-hub.html' },
  { name: 'Doctor Report',         icon: '🏥', path: '.claude/PRPs/doctor/doctor-report.html' },
  { name: 'Branch Visualization',  icon: '🌿', path: '.claude/PRPs/branches/branch-viz.html' },
  { name: 'Transcript Analysis',   icon: '📊', path: '.claude/PRPs/transcript-analysis/report.html' },
  { name: 'Coverage Report',       icon: '📈', path: 'htmlcov/index.html' },
  { name: 'QA Report',             icon: '🧪', path: '.claude/PRPs/qa/reports/qa-report.html' },
];

const QA_REPORT_DIR = '.claude/PRPs/qa/reports';

const CONFIG_PATH = join(process.env.HOME || '~', '.claude', 'prp-projects.json');

// ── Helpers ─────────────────────────────────────────────────────────────────

function freshnessBadge(mtimeMs: number): { label: string; cls: 'fresh' | 'recent' | 'stale' } {
  const ageHours = (Date.now() - mtimeMs) / (1000 * 3600);
  if (ageHours < 24) return { label: 'Fresh', cls: 'fresh' };
  if (ageHours < 168) return { label: `${Math.floor(ageHours / 24)}d ago`, cls: 'recent' };
  return { label: `${Math.floor(ageHours / 24)}d ago`, cls: 'stale' };
}

function autoDetectProjects(): ProjectConfig[] {
  const projects: ProjectConfig[] = [];
  const devDir = join(process.env.HOME || '~', 'Development');

  try {
    const entries = readdirSync(devDir, { withFileTypes: true });
    for (const entry of entries) {
      if (!entry.isDirectory()) continue;
      const projectPath = join(devDir, entry.name);
      if (existsSync(join(projectPath, '.claude'))) {
        projects.push({ name: entry.name, path: projectPath });
      }
    }
  } catch {
    // ~/Development doesn't exist — fall back to walking up from server dir
    let current = resolve(import.meta.dir);
    while (current !== resolve(current, '..')) {
      if (existsSync(join(current, '.claude'))) {
        const name = current.split('/').pop() || 'project';
        projects.push({ name, path: current });
        break;
      }
      current = resolve(current, '..');
    }
  }

  return projects;
}

// ── Public API ──────────────────────────────────────────────────────────────

export function loadProjectsConfig(): ProjectConfig[] {
  const seen = new Set<string>();
  const projects: ProjectConfig[] = [];

  // 1. Read explicit config entries first (they take priority)
  try {
    if (existsSync(CONFIG_PATH)) {
      const text = require('fs').readFileSync(CONFIG_PATH, 'utf-8');
      const data = JSON.parse(text);
      if (Array.isArray(data.projects)) {
        for (const p of data.projects) {
          if (p.name && p.path && !seen.has(p.path)) {
            projects.push(p);
            seen.add(p.path);
          }
        }
      }
    }
  } catch {
    // Config missing or invalid — continue to auto-detect
  }

  // 2. Merge in auto-detected projects (any not already in config)
  for (const p of autoDetectProjects()) {
    if (!seen.has(p.path)) {
      projects.push(p);
      seen.add(p.path);
    }
  }

  return projects;
}

export function discoverReports(projectPath: string): ReportInfo[] {
  const reports: ReportInfo[] = [];
  const root = resolve(projectPath);

  // Check known report locations
  for (const known of KNOWN_REPORTS) {
    const fullPath = join(root, known.path);
    try {
      const stat = statSync(fullPath);
      const badge = freshnessBadge(stat.mtimeMs);
      reports.push({
        name: known.name,
        icon: known.icon,
        relativePath: known.path,
        sizeKb: Math.round(stat.size / 1024 * 10) / 10,
        modified: new Date(stat.mtimeMs).toISOString().slice(0, 16).replace('T', ' '),
        badge: badge.label,
        badgeCls: badge.cls,
      });
    } catch {
      // File doesn't exist, skip
    }
  }

  // Scan QA reports directory for additional reports
  const qaDir = join(root, QA_REPORT_DIR);
  try {
    const files = readdirSync(qaDir)
      .filter(f => f.endsWith('.html'))
      .map(f => {
        const stat = statSync(join(qaDir, f));
        return { name: f, mtimeMs: stat.mtimeMs, size: stat.size };
      })
      .sort((a, b) => b.mtimeMs - a.mtimeMs);

    for (const file of files) {
      const relPath = `${QA_REPORT_DIR}/${file.name}`;
      // Skip the main QA report — already in KNOWN_REPORTS
      if (relPath === 'claude/PRPs/qa/reports/qa-report.html') continue;
      // Skip if already covered by KNOWN_REPORTS
      if (reports.some(r => r.relativePath === relPath)) continue;

      const badge = freshnessBadge(file.mtimeMs);
      reports.push({
        name: `QA: ${file.name.replace('.html', '')}`,
        icon: '🧪',
        relativePath: relPath,
        sizeKb: Math.round(file.size / 1024 * 10) / 10,
        modified: new Date(file.mtimeMs).toISOString().slice(0, 16).replace('T', ' '),
        badge: badge.label,
        badgeCls: badge.cls,
      });
    }
  } catch {
    // QA directory doesn't exist
  }

  return reports;
}

export function getReportContent(projectPath: string, relativePath: string): string | null {
  const root = resolve(projectPath);
  const reportPath = resolve(root, relativePath);

  // Path traversal prevention
  if (!reportPath.startsWith(root)) {
    return null;
  }

  try {
    return require('fs').readFileSync(reportPath, 'utf-8');
  } catch {
    return null;
  }
}

export function getProjectsWithReports(): ProjectWithReports[] {
  const projects = loadProjectsConfig();
  return projects
    .map(p => ({
      name: p.name,
      path: p.path,
      reports: discoverReports(p.path),
    }))
    .filter(p => p.reports.length > 0);
}
