---
name: task-execution
description: Execute a specific task along with its sub-tasks systematically following a TDD development workflow. Use when implementing individual tasks from a spec.
allowed-tools: Read, Edit, Bash, Glob, Grep, Write
---

# Task Execution Skill

Execute a specific task along with its sub-tasks systematically following a TDD development workflow.

## When to Use

- When implementing a specific parent task from tasks.md
- During the main execution loop of a feature spec
- When following TDD approach for feature development

## Process

### Step 1: Task Understanding

Read and analyze the given parent task and all its sub-tasks from tasks.md to gain complete understanding of what needs to be built.

**Task Analysis:**
- Parent task description
- All sub-task descriptions
- Task dependencies
- Expected outcomes

**Instructions:**
- ACTION: Read the specific parent task and all its sub-tasks
- ANALYZE: Full scope of implementation required
- UNDERSTAND: Dependencies and expected deliverables
- NOTE: Test requirements for each sub-task

### Step 2: Technical Specification Review

Search and extract relevant sections from technical-spec.md to understand the technical implementation approach for this task.

**Selective Reading:**
FIND sections in technical-spec.md related to:
- Current task functionality
- Implementation approach for this feature
- Integration requirements
- Performance criteria

**Instructions:**
- ACTION: Search technical-spec.md for task-relevant sections
- EXTRACT: Only implementation details for current task
- SKIP: Unrelated technical specifications
- FOCUS: Technical approach for this specific feature

### Step 3: Best Practices Review

Retrieve relevant sections from @.agentic-docs/standards/best-practices.md that apply to the current task's technology stack and feature type.

**Search For:**
- Task's technology stack patterns
- Feature type being implemented
- Testing approaches needed
- Code organization patterns

**Instructions:**
- ACTION: Find best practices sections
- PROCESS: Returned best practices
- APPLY: Relevant patterns to implementation

### Step 4: Code Style Review

Retrieve relevant code style rules from @.agentic-docs/standards/code-style.md for the languages and file types being used in this task.

**Search For:**
- Languages used in this task
- File types being modified
- Component patterns being implemented
- Testing style guidelines

**Instructions:**
- ACTION: Find code style rules
- PROCESS: Returned style rules
- APPLY: Relevant formatting and patterns

### Step 5: Task and Sub-task Execution

Execute the parent task and all sub-tasks in order using test-driven development (TDD) approach.

**Typical Task Structure:**
- First subtask: Write tests for [feature]
- Middle subtasks: Implementation steps
- Final subtask: Verify all tests pass

**Execution Order:**

**Subtask 1 - Tests:**
IF sub-task 1 is "Write tests for [feature]":
- Write all tests for the parent feature
- Include unit tests, integration tests, edge cases
- Run tests to ensure they fail appropriately
- Mark sub-task 1 complete

**Middle Subtasks - Implementation:**
FOR each implementation sub-task (2 through n-1):
- Implement the specific functionality
- Make relevant tests pass
- Update any adjacent/related tests if needed
- Refactor while keeping tests green
- Mark sub-task complete

**Final Subtask - Verification:**
IF final sub-task is "Verify all tests pass":
- Run entire test suite
- Fix any remaining failures
- Ensure no regressions
- Mark final sub-task complete

**Test Management:**
- New tests: Written in first sub-task, cover all aspects of parent feature, include edge cases and error handling
- Test updates: Made during implementation sub-tasks, update expectations for changed behavior, maintain backward compatibility

**Instructions:**
- ACTION: Execute sub-tasks in their defined order
- RECOGNIZE: First sub-task typically writes all tests
- IMPLEMENT: Middle sub-tasks build functionality
- VERIFY: Final sub-task ensures all tests pass
- UPDATE: Mark each sub-task complete as finished

### Step 6: Task-Specific Test Verification

Run and verify only the tests specific to this parent task (not the full test suite) to ensure the feature is working correctly.

**Focused Test Execution:**
- Run only: All new tests written for this parent task, all tests updated during this task, tests directly related to this feature
- Skip: Full test suite (done later), unrelated test files

**Final Verification:**
```
IF any test failures:
  - Debug and fix the specific issue
  - Re-run only the failed tests
ELSE:
  - Confirm all task tests passing
  - Ready to proceed
```

**Instructions:**
- ACTION: Run tests for this parent task's test files
- WAIT: For test analysis
- PROCESS: Returned failure information
- VERIFY: 100% pass rate for task-specific tests
- CONFIRM: This feature's tests are complete

### Step 7: Mark Task Complete

IMPORTANT: In the tasks.md file, mark this task and its sub-tasks complete by updating each task checkbox to [x].

**Update Format:**
- Completed: `- [x] Task description`
- Incomplete: `- [ ] Task description`
- Blocked: `- [ ] Task description` with `⚠️ Blocking issue: [DESCRIPTION]`

**Blocking Criteria:**
- Maximum 3 different approaches
- Document blocking issue with ⚠️ emoji

**Instructions:**
- ACTION: Update tasks.md after each task completion
- MARK: [x] for completed items immediately
- DOCUMENT: Blocking issues with ⚠️ emoji
- LIMIT: 3 attempts before marking as blocked

## Success Criteria

- All sub-tasks completed in order
- All task-specific tests passing
- Task marked complete in tasks.md
- Code follows project style guidelines
- TDD approach followed throughout
