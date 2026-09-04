import { parseAgent, stringifyAgent } from './frontmatter.js'
import { slugify } from './slugify.js'
import { splitClaudeTools, claudeToolsToCopilot } from './mappings/tools.js'
import { claudeModelToCopilot } from './mappings/model.js'

// Converts one Claude Code agent file's content into a Copilot agent file.
// `stem` is the source filename without extension, used as a fallback id.
export function convertClaudeToCopilot(sourceContent, stem) {
  const { frontmatter, body } = parseAgent(sourceContent)
  const warnings = []

  const name = frontmatter.name || stem
  const out = { name, description: frontmatter.description ?? '' }

  if (frontmatter.tools) {
    const { mapped, dropped } = claudeToolsToCopilot(splitClaudeTools(frontmatter.tools))
    if (mapped.length) out.tools = mapped
    for (const tool of dropped) {
      warnings.push(`dropped tool "${tool}" (no Copilot equivalent)`)
    }
  }

  if (frontmatter.model) {
    const mappedModel = claudeModelToCopilot(frontmatter.model)
    if (mappedModel) {
      out.model = mappedModel
    } else {
      warnings.push(`dropped model "${frontmatter.model}" (no Copilot equivalent)`)
    }
  }

  if (frontmatter.memory) {
    warnings.push(`dropped memory "${frontmatter.memory}" (no Copilot equivalent)`)
  }

  return {
    filename: `${slugify(name)}.agent.md`,
    content: stringifyAgent(out, body),
    warnings,
  }
}
