const API_BASE = 'https://api.github.com'
const USER_AGENT = 'agent-porter'

async function githubJson(url) {
  const res = await fetch(url, {
    headers: { Accept: 'application/vnd.github+json', 'User-Agent': USER_AGENT },
  })
  if (!res.ok) {
    throw new Error(`GitHub API ${res.status} for ${url}: ${await res.text()}`)
  }
  return res.json()
}

// Lists .md files in a public repo directory via the Contents API.
export async function listRepoAgentFiles(repo, path, ref) {
  const url = `${API_BASE}/repos/${repo}/contents/${path}${ref ? `?ref=${encodeURIComponent(ref)}` : ''}`
  const items = await githubJson(url)
  if (!Array.isArray(items)) {
    throw new Error(`${path} in ${repo} is not a directory`)
  }
  return items.filter((item) => item.type === 'file' && item.name.endsWith('.md'))
}

// Fetches a single file's metadata (incl. download_url) via the Contents API.
export async function getRepoFile(repo, path, ref) {
  const url = `${API_BASE}/repos/${repo}/contents/${path}${ref ? `?ref=${encodeURIComponent(ref)}` : ''}`
  return githubJson(url)
}

export async function fetchRaw(downloadUrl) {
  const res = await fetch(downloadUrl, { headers: { 'User-Agent': USER_AGENT } })
  if (!res.ok) {
    throw new Error(`Failed to fetch ${downloadUrl}: ${res.status}`)
  }
  return res.text()
}
