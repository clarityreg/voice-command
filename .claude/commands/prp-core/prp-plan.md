---
description: Generate a battle-tested implementation plan from requirements (PRD or description)
argument-hint: <PRD-file-path or feature-description>
---

# Implementation Plan Generator

Transform feature descriptions or PRD documents into detailed, executable implementation plans through systematic codebase analysis and strategic research.

## Core Principles

- **PLAN ONLY** - No code written, only context-rich documentation
- **CODEBASE FIRST, RESEARCH SECOND** - Solutions must fit existing patterns
- **ARCHON INTEGRATION** - Create tasks for tracking when Archon is available

---

## Phase 0: DETECT

Parse `$ARGUMENTS` to identify input type:

| Input Type | Detection | Action |
|------------|-----------|--------|
| PRD File | Path ends with `.prd.md` | Read and extract requirements |
| Markdown File | Path ends with `.md` | Read and parse as requirements |
| Free-form Text | No file path | Use text as feature description |
| Empty | No arguments | Ask user for feature description |

```bash
# If file path provided, verify it exists
if [[ -f "$ARGUMENTS" ]]; then
    INPUT_TYPE="file"
else
    INPUT_TYPE="text"
fi
```

---

## Phase 0.5: ARCHON CONTEXT

**Check for existing Archon project (if Archon MCP available):**

```python
# 1. Search for existing related project
find_projects(query="<feature-name>")

# 2. If found, get existing tasks
find_tasks(filter_by="project", filter_value="<project_id>")

# 3. Document any existing progress
```

**If existing project found:**
- Note the project ID for linking
- Review existing tasks and their statuses
- Identify what's already been planned/completed

**If no project found:**
- Continue with fresh planning
- Project will be created in Phase 6

**Fallback (Archon not available):**
- Log: "Archon not configured, using file-based tracking only"
- Continue with standard workflow

---

## Phase 1: PARSE

Extract and structure requirements:

### 1.1 If PRD File
- Read the PRD document
- Extract: Problem statement, success criteria, user stories
- Note: Technical constraints, dependencies, scope boundaries

### 1.2 If Free-form Description
- Identify the core feature request
- Formulate implicit user stories
- Ask clarifying questions if ambiguous

### Output Format
```yaml
feature_name: "{name}"
problem_statement: "{what problem does this solve}"
user_stories:
  - "As a {user}, I want {action} so that {benefit}"
success_criteria:
  - "{criterion 1}"
  - "{criterion 2}"
constraints:
  - "{constraint 1}"
scope:
  in: ["{item 1}", "{item 2}"]
  out: ["{explicitly excluded}"]
```

**CHECKPOINT**: Do not proceed if requirements are ambiguous. Ask for clarification.

---

## Phase 2: EXPLORE

**Use the Explore agent** for comprehensive codebase discovery:

```
Launch Task tool with subagent_type="Explore"

Prompt: "Analyze the codebase for implementing {feature}:
1. Find existing patterns for similar features
2. Identify integration points
3. Locate relevant utilities and helpers
4. Note testing patterns used
5. Document file naming conventions

Return actual file paths with line numbers."
```

### Discovery Targets

1. **Architecture Patterns**
   - Project structure and organization
   - Module/component patterns
   - State management approach

2. **Similar Implementations**
   - Features with comparable functionality
   - Code to use as templates

3. **Integration Points**
   - Files that will need modification
   - APIs to integrate with
   - Database schemas involved

4. **Testing Patterns**
   - Test file locations and naming
   - Testing utilities and fixtures
   - Coverage expectations

### Output: Mandatory Reading List
```yaml
mandatory_reading:
  - path: "src/features/auth/login.ts"
    reason: "Similar feature - authentication flow pattern"
    lines: "45-120"
  - path: "src/utils/validation.ts"
    reason: "Reuse existing validation utilities"
  - path: "tests/features/auth.test.ts"
    reason: "Test pattern to follow"
```

**CHECKPOINT**: Must have at least 3 real file references before proceeding.

---

## Phase 3: RESEARCH

### 3.1 Knowledge Base Search (Archon RAG)

**If Archon MCP is available:**

```python
# 1. Get available documentation sources
rag_get_available_sources()

# 2. Search for relevant patterns
rag_search_knowledge_base(
    query="<feature-related keywords>",
    match_count=5
)

# 3. Find code examples
rag_search_code_examples(
    query="<implementation pattern>",
    match_count=3
)
```

Document findings:
```yaml
rag_findings:
  documentation:
    - source: "{source_name}"
      relevant_content: "{summary}"
  code_examples:
    - pattern: "{pattern_name}"
      example: "{code_snippet}"
```

### 3.2 Web Research (if needed)

Only research AFTER exhausting codebase patterns:

1. **Technology Documentation**
   - Official docs for frameworks used
   - API references

2. **Best Practices**
   - Common patterns for this type of feature
   - Pitfalls to avoid

3. **Similar Implementations**
   - Open source examples
   - Tutorial implementations

---

## Phase 4: DESIGN

### 4.1 UX Transformation

Create ASCII diagrams showing before/after user experience:

```
BEFORE (Current State):
┌─────────────────────────────┐
│ User clicks "Submit"        │
│           ↓                 │
│ Page refreshes (slow)       │
│           ↓                 │
│ No feedback if error        │
└─────────────────────────────┘

AFTER (Target State):
┌─────────────────────────────┐
│ User clicks "Submit"        │
│           ↓                 │
│ Inline loading indicator    │
│           ↓                 │
│ Success toast OR            │
│ Inline error message        │
└─────────────────────────────┘
```

### 4.2 Data Flow

```
User Input
    ↓
┌─────────────┐
│ Validation  │ ← Reuse: src/utils/validation.ts
└─────────────┘
    ↓
┌─────────────┐
│ API Call    │ ← Pattern: src/api/client.ts
└─────────────┘
    ↓
┌─────────────┐
│ State Update│ ← Pattern: src/store/slices/
└─────────────┘
    ↓
UI Update
```

---

## Phase 5: ARCHITECT

### 5.1 Design Fit Analysis

| Aspect | Current Pattern | Proposed Approach | Fit |
|--------|-----------------|-------------------|-----|
| State | Redux Toolkit | Use existing slice pattern | High |
| API | React Query | Add new query hook | High |
| UI | Tailwind + shadcn | Compose existing components | High |

### 5.2 Failure Mode Analysis

| Scenario | Impact | Mitigation |
|----------|--------|------------|
| API timeout | User stuck | Loading states + timeout handling |
| Validation error | Poor UX | Inline field-level errors |
| Race condition | Data corruption | Request deduplication |

### 5.3 Performance Implications

- Bundle size impact: {estimate}
- Runtime performance: {considerations}
- Database impact: {if applicable}

---

## Phase 6: GENERATE

### 6.1 Create Plan Document

Write to `.claude/PRPs/plans/{kebab-case-name}.plan.md`:

```markdown
# Implementation Plan: {Feature Name}

**Created**: {date}
**Status**: Ready for Implementation
**Archon Project ID**: {project_id or "Not created"}

---

## Overview

{2-3 sentence summary of what will be built}

## User Stories

- As a {user}, I want {action} so that {benefit}

## Success Criteria

- [ ] {criterion 1}
- [ ] {criterion 2}

---

## Mandatory Reading

Before implementation, read these files to understand patterns:

| File | Purpose | Key Lines |
|------|---------|-----------|
| {path} | {why to read} | {lines} |

## Patterns to Follow

### Naming
- Components: `{pattern}`
- Files: `{pattern}`
- Tests: `{pattern}`

### Code Style
- {pattern from codebase}

### Error Handling
- {pattern from codebase}

### Testing
- {pattern from codebase}

---

## Implementation Tasks

### Phase 1: Foundation

#### Task 1.1: {Task Name}
**Status**: todo
**Archon Task ID**: {task_id or TBD}

**Description**: {What needs to be done}

**Files**:
- Create: `{path}`
- Modify: `{path}:{lines}`

**Validation**:
```bash
{command to verify task completion}
```

**Acceptance Criteria**:
- [ ] {criterion}

---

#### Task 1.2: {Task Name}
...

### Phase 2: Core Implementation
...

### Phase 3: Integration & Testing
...

---

## Edge Cases

| Case | Expected Behavior | Test Coverage |
|------|-------------------|---------------|
| {case} | {behavior} | {test file} |

---

## Validation Approach

### Level 1: Static Analysis
```bash
npm run typecheck
npm run lint
```

### Level 2: Unit Tests
```bash
npm test -- --coverage
```

### Level 3: Integration Tests
```bash
npm run test:integration
```

### Level 4: Build Verification
```bash
npm run build
```

### Level 5: E2E Tests (if applicable)
```bash
npm run test:e2e
```

### Level 6: Manual Testing
- [ ] {manual test scenario 1}
- [ ] {manual test scenario 2}

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| {risk} | {H/M/L} | {H/M/L} | {plan} |

---

## Research Findings

### From Codebase
{Key patterns and references discovered}

### From Archon RAG
{Relevant documentation and examples found}

### From Web Research
{External resources and best practices}

---

*Ready for implementation with `/prp-implement`*
```

### 6.2 Create Archon Project and Tasks

**If Archon MCP is available:**

```python
# 1. Create project
project_result = manage_project(
    "create",
    title="<plan-title>",
    description="<summary from plan>"
)
project_id = project_result["project_id"]

# 2. Create tasks for each implementation task
task_order = 100  # Start high, decrement for priority

for task in plan_tasks:
    manage_task(
        "create",
        project_id=project_id,
        title=task["name"],
        description=task["description"],
        status="todo",
        task_order=task_order
    )
    task_order -= 10

# 3. Update plan document with project_id and task_ids
```

**Store in plan frontmatter:**
```yaml
archon_project_id: "proj-abc123"
archon_tasks:
  - task_id: "task-001"
    name: "Task 1.1"
  - task_id: "task-002"
    name: "Task 1.2"
```

---

## Phase 7: OUTPUT

Report to user:

```
Implementation Plan Created

File: .claude/PRPs/plans/{name}.plan.md

Summary:
- Tasks: {total_count}
- Phases: {phase_count}
- Mandatory Reading: {file_count} files

Archon Integration:
- Project ID: {project_id or "Not available"}
- Tasks Created: {task_count or "None - Archon not configured"}

Validation Levels: 6

Next Steps:
1. Review the plan document
2. Read the mandatory reading files
3. When ready: /prp-implement .claude/PRPs/plans/{name}.plan.md
```

---

## Quality Checklist

Before finalizing:

- [ ] All tasks are atomic and actionable
- [ ] Each task has validation commands
- [ ] Mandatory reading includes real file paths
- [ ] Patterns reference actual codebase code
- [ ] Edge cases are documented
- [ ] Risk assessment is complete
- [ ] Archon project created (if available)

---

## Fallback Behavior

If Archon MCP is not available:

1. Log warning: "Archon not configured, using file-based tracking"
2. Skip Phase 0.5 Archon context check
3. Skip Phase 3.1 RAG search (use web research only)
4. Skip Phase 6.2 Archon project creation
5. Continue with all other phases normally
6. Plan document remains fully functional without Archon
