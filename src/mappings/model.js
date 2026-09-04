// Claude's model field is a fixed enum; Copilot's is free text (e.g. "Claude Sonnet 4.5",
// "gpt-4o"). Mapping is best-effort in both directions.

const CLAUDE_TO_COPILOT_MODEL = {
  sonnet: 'Claude Sonnet 4.5',
  opus: 'Claude Opus 4.5',
  haiku: 'Claude Haiku 4.5',
  // "inherit" has no fixed Copilot equivalent — no target model name to pin.
}

export function claudeModelToCopilot(claudeModel) {
  return CLAUDE_TO_COPILOT_MODEL[claudeModel] ?? null
}

export function copilotModelToClaude(copilotModel) {
  const normalized = String(copilotModel).toLowerCase()
  if (normalized.includes('opus')) return 'opus'
  if (normalized.includes('haiku')) return 'haiku'
  if (normalized.includes('sonnet')) return 'sonnet'
  return null
}
