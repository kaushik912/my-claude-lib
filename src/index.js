import { readdir, readFile, writeFile, mkdir, stat } from 'node:fs/promises'
import { join, basename } from 'node:path'
import { convertClaudeToCopilot } from './convert-claude-to-copilot.js'
import { convertCopilotToClaude } from './convert-copilot-to-claude.js'

const DEFAULT_DIRS = {
  claude: '.claude/agents',
  copilot: '.github/agents',
}

export function defaultDir(format) {
  return DEFAULT_DIRS[format]
}

function stemFor(format, filename) {
  return format === 'claude' ? basename(filename, '.md') : basename(filename, '.agent.md')
}

function matchesFormat(format, filename) {
  if (format === 'claude') return filename.endsWith('.md') && !filename.endsWith('.agent.md')
  return filename.endsWith('.agent.md')
}

function converterFor(src, dest) {
  if (src === 'claude' && dest === 'copilot') return convertClaudeToCopilot
  if (src === 'copilot' && dest === 'claude') return convertCopilotToClaude
  throw new Error(`Unsupported conversion: ${src} -> ${dest}`)
}

export async function listSourceFiles(inDir, format) {
  const entries = await readdir(inDir, { withFileTypes: true })
  return entries
    .filter((e) => e.isFile() && matchesFormat(format, e.name))
    .map((e) => join(inDir, e.name))
}

export async function convertFiles({ src, dest, files, outDir, dryRun, force }) {
  const convert = converterFor(src, dest)
  if (!dryRun) await mkdir(outDir, { recursive: true })

  const results = []
  for (const filePath of files) {
    const content = await readFile(filePath, 'utf8')
    const stem = stemFor(src, basename(filePath))
    const { filename, content: outContent, warnings } = convert(content, stem)
    const outPath = join(outDir, filename)

    const exists = !dryRun && (await stat(outPath).then(() => true).catch(() => false))
    const skipped = exists && !force

    if (!dryRun && !skipped) {
      await writeFile(outPath, outContent, 'utf8')
    }

    results.push({ inPath: filePath, outPath, warnings, skipped, dryRun })
  }
  return results
}

export function printResults(results) {
  for (const r of results) {
    const action = r.dryRun ? 'would write' : r.skipped ? 'skipped (exists, use --force)' : 'wrote'
    console.log(`${r.inPath} -> ${r.outPath} (${action})`)
    for (const w of r.warnings) console.log(`  warning: ${w}`)
  }
}
