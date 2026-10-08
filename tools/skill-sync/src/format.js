/** Rows -> aligned text (state/action columns, optional indented diff under a row). */
export function formatRows(rows) {
  if (!rows.length) return 'nothing to do';
  const label = (r) => (r.kind ? `${r.kind}/${r.name}` : r.name);
  const w = Math.max(...rows.map((r) => label(r).length));
  return rows
    .map((r) => {
      const line = `${label(r).padEnd(w)}  ${r.state.padEnd(16)}  ${r.action ?? ''}`.trimEnd();
      return r.diff ? `${line}\n${r.diff.split('\n').map((l) => `    ${l}`).join('\n')}` : line;
    })
    .join('\n');
}
