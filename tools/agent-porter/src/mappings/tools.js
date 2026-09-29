// Best-effort tool-name mapping. Claude's tool set is small and fixed; Copilot's is a
// large, inconsistent vocabulary pulled from VS Code's tool picker (different files use
// different granularity for the same concept, e.g. "codebase" vs "search/codebase").
// Anything not covered here is dropped with a warning rather than guessed.

const CLAUDE_TO_COPILOT = {
  Read: 'read',
  Write: 'edit',
  Edit: 'edit',
  Bash: 'execute',
  Grep: 'search',
  Glob: 'search',
  WebFetch: 'web',
  WebSearch: 'web',
  Task: 'agent',
  TodoWrite: 'todo',
}

const COPILOT_TO_CLAUDE = {
  read: 'Read',
  codebase: 'Read',
  'search/codebase': 'Read',
  edit: 'Edit',
  editFiles: 'Edit',
  'edit/editFiles': 'Edit',
  execute: 'Bash',
  runCommands: 'Bash',
  'execute/runInTerminal': 'Bash',
  'execute/runCommands': 'Bash',
  'execute/runTests': 'Bash',
  'execute/getTerminalOutput': 'Bash',
  'execute/testFailure': 'Bash',
  search: 'Grep',
  usages: 'Grep',
  'search/usages': 'Grep',
  findTestFiles: 'Glob',
  web: 'WebFetch',
  fetch: 'WebFetch',
  'web/fetch': 'WebFetch',
  githubRepo: 'WebFetch',
  agent: 'Task',
  todo: 'TodoWrite',
}

// Parses Claude's comma-separated tools string into a trimmed array.
export function splitClaudeTools(toolsField) {
  return String(toolsField)
    .split(',')
    .map((t) => t.trim())
    .filter(Boolean)
}

export function claudeToolsToCopilot(claudeTools) {
  const mapped = []
  const dropped = []
  for (const tool of claudeTools) {
    if (tool.startsWith('mcp__')) {
      // No confirmed Copilot equivalent for MCP tool names — pass through as-is,
      // caller decides whether to warn.
      mapped.push(tool)
      continue
    }
    const target = CLAUDE_TO_COPILOT[tool]
    if (target) {
      if (!mapped.includes(target)) mapped.push(target)
    } else {
      dropped.push(tool)
    }
  }
  return { mapped, dropped }
}

export function copilotToolsToClaude(copilotTools) {
  const mapped = []
  const dropped = []
  for (const tool of copilotTools) {
    if (tool.startsWith('mcp__')) {
      // Round-trips an MCP tool name that a Claude->Copilot conversion passed through
      // unchanged (see claudeToolsToCopilot) — not a real Copilot vocabulary entry.
      if (!mapped.includes(tool)) mapped.push(tool)
      continue
    }
    const target = COPILOT_TO_CLAUDE[tool]
    if (target) {
      if (!mapped.includes(target)) mapped.push(target)
    } else {
      dropped.push(tool)
    }
  }
  return { mapped, dropped }
}
