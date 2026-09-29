import matter from 'gray-matter'

export function parseAgent(content) {
  const { data, content: body } = matter(content)
  return { frontmatter: data, body: body.replace(/^\n+/, '') }
}

export function stringifyAgent(frontmatter, body) {
  return matter.stringify(`${body.trimEnd()}\n`, frontmatter)
}
