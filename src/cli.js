import { parseArgs } from 'node:util'
import { resolve } from 'node:path'
import { convertFiles, listSourceFiles, defaultDir, printResults } from './index.js'
import { runInstall } from './install.js'

const USAGE = `Usage:
  agent-porter convert --src <claude|copilot> --dest <claude|copilot> [--in <dir>] [--out <dir>] [--file <path>] [--dry-run] [--force]
  agent-porter install (--agent <name> | --all) [--repo <owner>/<repo>] [--dest <claude|copilot>] [--ref <branch>] [--path <dir>] [--out <dir>] [--force] [--dry-run]
  (--repo defaults to kaushik912/my-claude-agents)`

export async function main(argv) {
  const [subcommand, ...rest] = argv

  if (subcommand === 'convert') return cmdConvert(rest)
  if (subcommand === 'install') return runInstall(rest)

  console.log(USAGE)
  if (subcommand && subcommand !== '--help' && subcommand !== '-h') {
    process.exitCode = 1
  }
}

async function cmdConvert(args) {
  const { values } = parseArgs({
    args,
    options: {
      src: { type: 'string' },
      dest: { type: 'string' },
      in: { type: 'string' },
      out: { type: 'string' },
      file: { type: 'string' },
      'dry-run': { type: 'boolean', default: false },
      force: { type: 'boolean', default: false },
    },
  })

  if (!values.src || !values.dest) {
    throw new Error('convert requires --src and --dest (each "claude" or "copilot")')
  }
  if (!['claude', 'copilot'].includes(values.src) || !['claude', 'copilot'].includes(values.dest)) {
    throw new Error('--src/--dest must be "claude" or "copilot"')
  }
  if (values.src === values.dest) {
    throw new Error('--src and --dest must differ')
  }

  const inDir = values.in ? resolve(values.in) : resolve(defaultDir(values.src))
  const outDir = values.out ? resolve(values.out) : resolve(defaultDir(values.dest))

  const files = values.file ? [resolve(values.file)] : await listSourceFiles(inDir, values.src)
  if (files.length === 0) {
    console.log(`No ${values.src} agent files found in ${inDir}`)
    return
  }

  const results = await convertFiles({
    src: values.src,
    dest: values.dest,
    files,
    outDir,
    dryRun: values['dry-run'],
    force: values.force,
  })
  printResults(results)
}
