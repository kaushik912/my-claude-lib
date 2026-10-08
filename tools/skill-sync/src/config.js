import path from 'node:path';

/**
 * Resolve the lib location. Precedence: flag > env > default
 * (default = the my-claude-lib this tool lives in).
 *
 * The lib repo is also the registry: my skills live in <lib>/skills,
 * vendored skills (installed by `npx skills add`, run in <lib>/registry) in <lib>/registry/.agents/skills.
 */
export function resolveConfig({ flags = {}, env = {}, toolDir }) {
  const lib = path.resolve(flags.lib ?? env.SKILL_SYNC_LIB ?? path.join(toolDir, '..', '..'));
  const registry = path.join(lib, 'registry');
  return {
    lib,
    libSkills: path.join(lib, 'skills'),
    registry,
    vendoredSkills: path.join(registry, '.agents', 'skills'),
  };
}

/** Canonical skills dir in a project (.claude/skills symlinks to it). */
export function projectSkillsDir(projectDir) {
  return path.join(projectDir, '.agents', 'skills');
}
