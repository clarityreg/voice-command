---
description: Analyse Claude Code transcripts for failure signals — apologies, self-corrections, context loss, tool failures
argument-hint:
---

# Transcript Failure-Signal Analysis

Mine Claude Code session transcripts for patterns that indicate context engineering failures. Inspired by Dru Knox's talk on context engineering analytics.

---

## Phase 1: DISCOVER

Count available transcripts and report to user:

```bash
echo "=== Transcript Discovery ===" ;
count_project=$(find ~/.claude/projects -name "*.jsonl" 2>/dev/null | wc -l | tr -d ' ') ;
count_backup=$(find .claude/transcripts -name "*.json" 2>/dev/null | wc -l | tr -d ' ') ;
echo "Project transcripts: $count_project" ;
echo "Backup transcripts: $count_backup" ;
echo "Total sources: $((count_project + count_backup))"
```

Report the discovery results to the user before proceeding.

---

## Phase 2: ANALYSE

Run the transcript analyser to scan for failure signals:

```bash
uv run scripts/transcript-analyser.py scan --days 30 --format json > /tmp/transcript-analysis.json 2>/tmp/transcript-analysis.log
```

If the command fails, check the log and report the error. If no transcripts are found, report that and suggest expanding the date range.

---

## Phase 3: PRESENT

Read the JSON output and present a console summary:

```
Transcript Analysis
====================

Summary
  Sessions scanned: X
  Total messages:   Y
  Failure signals:  Z
  Tool failures:    W

Signal Categories
  HIGH  Self-Corrections:  N
  HIGH  Context Loss:      N
  MED   Apologies:         N
  MED   Confusion:         N
  MED   Backtracking:      N

Top Patterns
  1. "let me try again"     — 8 occurrences
  2. "I'm sorry"            — 5 occurrences
  3. "you're absolutely right" — 3 occurrences

Tool Failures
  Read (hallucination)      — 4 occurrences
  Bash (repeated_failure)   — 2 occurrences

Recommendations
  HIGH  CLAUDE.md       Add documentation about usage patterns (6 self-correction signals)
  HIGH  Hook/Skill      Create validation for Read tool (4 hallucinations)
  MED   Command/Plan    Improve plan templates (3 backtracking signals)
```

Format the output to be readable in the terminal. Use the category labels and severity from the JSON.

---

## Phase 4: PLANE TASK (conditional)

Check if Plane is configured by reading `.claude/prp-settings.json`:

- If `plane.workspace_slug` AND `plane.project_id` are non-empty AND `PLANE_API_KEY` is set:
  - Create a Plane work item using `mcp__plane__create_work_item` with:
    - **Title**: `[Transcript Audit] {date} — {signal_count} signals, {failure_count} tool failures`
    - **Description**: Summary of top findings and recommendations (markdown formatted)
    - **Priority**: Based on highest severity found (high → urgent, medium → high, low → medium)
  - Report the created work item ID to the user
- If Plane is NOT configured:
  - Print: `Plane not configured — skipping work item creation`
  - Continue to next phase

---

## Phase 5: HTML REPORT

Generate the HTML report:

```bash
uv run scripts/transcript-analyser.py report --days 30
```

This will:
1. Save HTML to `.claude/PRPs/transcript-analysis/report.html`
2. Save JSON to `.claude/PRPs/transcript-analysis/latest.json`
3. Open the report in the default browser
4. Regenerate the reports hub (if `scripts/reports-hub.py` exists)

Report the saved file paths to the user.

---

## Phase 6: SAVE ARTIFACT

The JSON artifact is saved automatically by the report command. Confirm the path:

```
Artifacts saved:
  HTML:  .claude/PRPs/transcript-analysis/report.html
  JSON:  .claude/PRPs/transcript-analysis/latest.json
```

---

## Phase 7: DISCUSSION

Present actionable options to the user:

```
What would you like to do next?

1. Drill into a specific signal category (e.g., self-corrections, context loss)
2. Draft CLAUDE.md improvements based on recommendations
3. Create a new skill or hook to address repeated patterns
4. View the HTML report in browser
5. Re-run with different date range
6. Done
```

Wait for user input. Based on their choice:

- **Option 1**: Filter the JSON for that category, show detailed excerpts with surrounding context
- **Option 2**: Read current CLAUDE.md, propose additions targeting the recommendation areas. Show a diff preview before applying.
- **Option 3**: Scaffold a new skill or hook based on the failure patterns. For example, if file hallucinations are common, draft a context-enricher update.
- **Option 4**: Re-open the HTML report (`open .claude/PRPs/transcript-analysis/report.html`)
- **Option 5**: Ask for new `--days` or `--since` value, re-run from Phase 2
- **Option 6**: End the command
