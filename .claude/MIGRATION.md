# Agent OS Migration to Claude Code Standards

## Migration Summary

Your Agent OS setup has been migrated from the legacy `.github/chatmodes` and `.github/instructions` format to the modern Claude Code `.claude/` directory structure.

## What Changed

### Directory Structure

**Before:**
```
.github/
├── chatmodes/
│   ├── plan-product.chatmode.md
│   ├── create-spec.chatmode.md
│   ├── create-tasks.chatmode.md
│   ├── execute-tasks.chatmode.md
│   └── analyze-product.chatmode.md
└── instructions/
    ├── plan-product.instructions.md
    ├── create-spec.instructions.md
    ├── create-tasks.instructions.md
    ├── execute-tasks.instructions.md
    ├── execute-task.instructions.md
    ├── post-execution-tasks.instructions.md
    ├── analyze-product.instructions.md
    └── meta/
        ├── pre-flight.md
        └── post-flight.md
```

**After:**
```
.claude/
├── agents/
│   ├── plan-product.md
│   ├── create-spec.md
│   ├── create-tasks.md
│   ├── execute-tasks.md
│   └── analyze-product.md
├── skills/
│   ├── task-execution/
│   │   └── SKILL.md
│   └── post-execution/
│       └── SKILL.md
├── CLAUDE.md
├── MIGRATION.md
└── settings.json
```

## Migration Details

### Agents (Previously Chatmodes)

Each `.chatmode.md` file has been converted to a modern agent format in `.claude/agents/`:

1. **plan-product.md** - Plan new products and install Agent OS
2. **create-spec.md** - Create detailed feature specifications
3. **create-tasks.md** - Break specs into executable tasks
4. **execute-tasks.md** - Execute tasks following TDD workflow
5. **analyze-product.md** - Analyze and document existing codebases

**Changes:**
- Merged chatmode description with instruction content
- Added standardized YAML frontmatter (name, description, tools, model)
- Converted XML-style process flows to markdown format
- Integrated pre-flight and post-flight checks directly
- Removed subagent references (not needed in modern format)

### Skills (Previously Instructions)

Reusable instruction sets have been converted to skills in `.claude/skills/`:

1. **task-execution** - Execute individual tasks with TDD approach
2. **post-execution** - Complete git workflow, PR creation, and documentation

**Changes:**
- Added `allowed-tools` field to restrict tool access
- Formatted as standalone skills that can be applied automatically
- Included clear "When to Use" and "Success Criteria" sections

### Project Context

**New file: `.claude/CLAUDE.md`**
- Contains project overview and product mission
- Documents technical stack
- Defines Agent OS standards and workflows
- Provides development guidelines
- Lists common commands

### Settings

**New file: `.claude/settings.json`**
- Enables agents and skills
- Configures auto-delegation
- Sets context files to always include
- Defines git branch naming conventions
- Specifies testing requirements

## How to Use the New Structure

### Invoking Agents

**Option 1: Direct invocation**
```
Use the plan-product agent to set up Agent OS in my project
```

**Option 2: Natural language (auto-delegation)**
```
I need to create a spec for a new feature
(Claude will automatically use the create-spec agent)
```

**Option 3: Via commands (if configured)**
```
/plan-product
```

### Skills Auto-Apply

Skills are automatically applied when relevant to the current task. You don't need to invoke them explicitly. Claude will:
- Use `task-execution` skill when implementing tasks
- Use `post-execution` skill when completing a spec

### Viewing Available Agents

In VS Code with Claude Code:
```
/agents
```

This will show all available agents and allow you to:
- View agent descriptions
- Create new agents
- Edit existing agents
- Delete agents

## Legacy Files

The old `.github/chatmodes` and `.github/instructions` directories have been removed as part of the migration. All functionality has been migrated to the new `.claude/` structure.

## Benefits of New Structure

1. **Standardization** - Follows official Claude Code conventions
2. **Better Tool Integration** - Works with `/agents` command and VS Code UI
3. **Auto-Delegation** - Claude can automatically select appropriate agents
4. **Cleaner Organization** - Single source of truth per agent
5. **Improved Context Management** - Settings control what's always loaded
6. **Skills Reusability** - Skills can be shared across multiple agents
7. **Plugin Support** - Can be packaged and shared as plugins

## Configuration

### Always-Included Context

The following files are always loaded into Claude's context (configured in `settings.json`):
- `.claude/CLAUDE.md` - Project overview
- `.agentic-docs/product/mission-lite.md` - Product mission
- `.agentic-docs/product/tech-stack.md` - Technical stack

### Git Workflow

- Branch names automatically strip date prefixes
- Format: `feature/{spec-name}`
- Conventional commits encouraged

## Next Steps

1. **Test the new structure** - Try invoking one of the agents
2. **Update your workflow** - Use natural language instead of manual chatmode selection
3. **Clean up legacy files** - Remove `.github/chatmodes` and `.github/instructions` after verification
4. **Customize settings** - Adjust `.claude/settings.json` to your preferences
5. **Add more agents/skills** - Extend the system as needed

## Troubleshooting

### Agent not found
- Ensure the file is in `.claude/agents/` directory
- Check that the file has `.md` extension
- Verify the YAML frontmatter is valid

### Skill not applying
- Check the `description` field accurately describes when to use the skill
- Ensure `allowed-tools` includes necessary tools
- Verify the skill file is named `SKILL.md` (uppercase)

### Settings not working
- Validate JSON syntax in `settings.json`
- Restart Claude Code / VS Code
- Check for syntax errors in settings file

## References

- Claude Code Documentation: See `/help` command
- Agent OS Original: https://github.com/buildermethods/agent-os (if applicable)
- Your project repo: https://github.com/gavargas22/Cascabel

## Questions?

If you encounter issues or have questions about the migration, refer to:
1. This migration guide
2. `.claude/CLAUDE.md` for project-specific context
3. Individual agent files for detailed workflows
4. Claude Code documentation via `/help` command
