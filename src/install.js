import { mkdir, writeFile, stat } from 'node:fs/promises'
import { join, resolve } from 'node:path'
import { parseArgs } from 'node:util'
import { listRepoAgentFiles, getRepoFile, fetchRaw } from './github.js'
import { convertClaudeToCopilot } from './convert-claude-to-copilot.js'
import { defaultDir } from './index.js'

const DEFAULT_REPO = 'kaushik912/my-claude-agents'

// Source repos are always Claude format (the my-claude-agents convention) — install
// only needs to optionally convert on the way *out* to Copilot, never in.
export async function runInstall(args) {
  const { values } = parseArgs({
    args,
    options: {
      repo: { type: 'string', default: DEFAULT_REPO },
      agent: { type: 'string' },
      all: { type: 'boolean', default: false },
      dest: { type: 'string', default: 'claude' },
      ref: { type: 'string' },
      path: { type: 'string', default: '.claude/agents' },
      out: { type: 'string' },
      force: { type: 'boolean', default: false },
      'dry-run': { type: 'boolean', default: false },
    },
  })

  if (!values.agent && !values.all) throw new Error('install requires --agent <name> or --all')
  if (!['claude', 'copilot'].includes(values.dest)) {
    throw new Error('--dest must be "claude" or "copilot"')
  }

  const outDir = values.out ? resolve(values.out) : resolve(defaultDir(values.dest))
  if (!values['dry-run']) await mkdir(outDir, { recursive: true })

  const fileMetas = values.all
    ? await listRepoAgentFiles(values.repo, values.path, values.ref)
    : [await getRepoFile(values.repo, `${values.path}/${values.agent}.md`, values.ref)]

  for (const meta of fileMetas) {
    const content = await fetchRaw(meta.download_url)
    const stem = meta.name.replace(/\.md$/, '')

    let filename = meta.name
    let outContent = content
    let warnings = []
    if (values.dest === 'copilot') {
      ;({ filename, content: outContent, warnings } = convertClaudeToCopilot(content, stem))
    }

    const outPath = join(outDir, filename)
    const exists = !values['dry-run'] && (await stat(outPath).then(() => true).catch(() => false))
    if (exists && !values.force) {
      console.log(`skipped ${outPath} (exists, use --force)`)
      continue
    }

    if (!values['dry-run']) {
      await writeFile(outPath, outContent, 'utf8')
    }
    const action = values['dry-run'] ? 'would install' : 'installed'
    console.log(`${action} ${values.repo}/${values.path}/${meta.name} -> ${outPath}`)
    for (const w of warnings) console.log(`  warning: ${w}`)
  }
}
