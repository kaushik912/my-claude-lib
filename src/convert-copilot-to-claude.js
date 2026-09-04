import { parseAgent, stringifyAgent } from './frontmatter.js'
import { slugify } from './slugify.js'
import { copilotToolsToClaude } from './mappings/tools.js'
import { copilotModelToClaude } from './mappings/model.js'

// Converts one Copilot agent file's content into a Claude Code agent file.
// `stem` is the source filename with the ".agent" suffix already stripped.
export function convertCopilotToClaude(sourceContent, stem) {
  const { frontmatter, body } = parseAgent(sourceContent)
  const warnings = []

  const name = frontmatter.name ? slugify(frontmatter.name) : stem
  const out = { name, description: frontmatter.description ?? '' }

  if (Array.isArray(frontmatter.tools)) {
    const { mapped, dropped } = copilotToolsToClaude(frontmatter.tools)
    if (mapped.length) out.tools = mapped.join(', ')
    for (const tool of dropped) {
      warnings.push(`dropped tool "${tool}" (no Claude equivalent)`)
    }
  }

  if (frontmatter.model) {
    const mappedModel = copilotModelToClaude(frontmatter.model)
    if (mappedModel) {
      out.model = mappedModel
    } else {
      warnings.push(`dropped model "${frontmatter.model}" (no Claude model alias matches)`)
    }
  }

  for (const field of ['user-invocable', 'user-invokable', 'argument-hint']) {
    if (frontmatter[field] !== undefined) {
      warnings.push(`dropped ${field}="${frontmatter[field]}" (no Claude equivalent)`)
    }
  }

  return {
    filename: `${name}.md`,
    content: stringifyAgent(out, body),
    warnings,
  }
}
