---
name: post-execution
description: Complete post-execution tasks after implementing a spec including tests, git workflow, PR creation, and documentation. Use when all spec tasks are complete.
allowed-tools: Read, Edit, Bash, Glob, Grep, Write
---

# Post-Execution Skill

Follow these steps to mark your progress updates, create a recap, and deliver the final report to the user.

## When to Use

- When all tasks in tasks.md have been implemented
- After completing feature development
- Before delivering work to the user
- As part of the final phase of spec execution

## Process

### Step 1: Run All Tests

Run ALL tests in the application's test suite to ensure no regressions and fix any failures until all tests pass.

**Instructions:**
- ACTION: Run the full test suite
- WAIT: For test analysis
- PROCESS: Fix any reported failures
- REPEAT: Until all tests pass

**Test Execution:**
1. Run entire test suite
2. Fix any failures

**Requirement:** 100% pass rate

**Failure Handling:**
- Action: troubleshoot and fix
- Priority: before proceeding

### Step 2: Git Workflow

Create git commit, push to GitHub, and create pull request for the implemented features.

**Instructions:**
- ACTION: Complete git workflow for [SPEC_NAME] feature:
  - Spec: [SPEC_FOLDER_PATH]
  - Changes: All modified files
  - Target: main branch
  - Description: [SUMMARY_OF_IMPLEMENTED_FEATURES]
- WAIT: For workflow completion
- PROCESS: Save PR URL for summary

**Commit Process:**
- Commit message: descriptive summary of changes, conventional commits format if applicable
- Push target: spec branch
- Remote: origin
- Pull request: descriptive PR title, functionality recap in description

### Step 3: Tasks Completion Verification

Read the current spec's tasks.md file and verify that all tasks have been properly marked as complete with [x] or documented with blockers.

**Instructions:**
- ACTION: Verify that all tasks have been marked with their outcome:
  - Read [SPEC_FOLDER_PATH]/tasks.md
  - Check all tasks are marked complete with [x] or (in rare cases) a documented blocking issue
- WAIT: For task verification analysis
- PROCESS: Update task status as needed

### Step 4: Roadmap Progress Update (Conditional)

Read @.agentic-docs/product/roadmap.md and mark roadmap items as complete with [x] ONLY IF the executed tasks have completed any roadmap item(s) and the spec completes that item.

**Conditional Execution:**

**Preliminary Check:**
```
EVALUATE: Did executed tasks complete any roadmap item(s)?
IF NO:
  SKIP this entire step
  PROCEED to step 5
IF YES:
  CONTINUE with roadmap check
```

**Roadmap Criteria:**
Update when:
- Spec fully implements roadmap feature
- All related tasks completed
- Tests passing

**Instructions:**
- ACTION: First evaluate if roadmap check is needed
- SKIP: If tasks clearly don't complete roadmap items
- EVALUATE: If current spec completes roadmap goals
- UPDATE: Mark roadmap items complete with [x] if applicable

### Step 5: Create Recap Document

Create a recap document in .agentic-docs/recaps/ folder that summarizes what was built for this spec.

**Instructions:**
- ACTION: Create recap document for current spec:
  - Create file: .agentic-docs/recaps/[SPEC_FOLDER_NAME].md
  - Use template format with completed features summary
  - Include context from spec-lite.md
  - Document: [SPEC_FOLDER_PATH]
- WAIT: For recap document creation
- PROCESS: Verify file is created with proper content

**Recap Template:**
```markdown
# [yyyy-mm-dd] Recap: Feature Name

This recaps what was built for the spec documented at .agentic-docs/specs/[spec-folder-name]/spec.md.

## Recap

[1 paragraph summary plus short bullet list of what was completed]

## Context

[Copy the summary found in spec-lite.md to provide concise context of what the initial goal for this spec was]
```

**File Creation:**
- Location: .agentic-docs/recaps/
- Naming: [SPEC_FOLDER_NAME].md
- Format: markdown with yaml frontmatter if needed

**Content Requirements:**
- Summary: 1 paragraph plus bullet points
- Context: from spec-lite.md summary
- Reference: link to original spec

### Step 6: Completion Summary

Create a structured summary message with emojis showing what was done, any issues, testing instructions, and PR link.

**Summary Template:**
```markdown
## ✅ What's been done

1. **[FEATURE_1]** - [ONE_SENTENCE_DESCRIPTION]
2. **[FEATURE_2]** - [ONE_SENTENCE_DESCRIPTION]

## ⚠️ Issues encountered

[ONLY_IF_APPLICABLE]
- **[ISSUE_1]** - [DESCRIPTION_AND_REASON]

## 👀 Ready to test in browser

[ONLY_IF_APPLICABLE]
1. [STEP_1_TO_TEST]
2. [STEP_2_TO_TEST]

## 📦 Pull Request

View PR: [GITHUB_PR_URL]
```

**Summary Sections:**
- Required: functionality recap, pull request info
- Conditional: issues encountered (if any), testing instructions (if testable in browser)

**Instructions:**
- ACTION: Create comprehensive summary
- INCLUDE: All required sections
- ADD: Conditional sections if applicable
- FORMAT: Use emoji headers for scannability

### Step 7: Task Completion Notification

Play a system sound to alert the user that tasks are complete.

**Notification Command:**
```bash
afplay /System/Library/Sounds/Glass.aiff
```

**Instructions:**
- ACTION: Play completion sound
- PURPOSE: Alert user that task is complete

## Success Criteria

- All tests passing (100% pass rate)
- Git commit created and pushed
- Pull request created with descriptive title and summary
- All tasks verified as complete in tasks.md
- Roadmap updated if applicable
- Recap document created
- Completion summary delivered to user
- Notification sound played
