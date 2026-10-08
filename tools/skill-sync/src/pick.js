/** Parse picker input ("1 3", "1,3", "all") into item names. Throws on bad input. */
export function parseSelection(input, items) {
  const text = input.trim().toLowerCase();
  if (text === 'all') return [...items];
  const picked = text.split(/[\s,]+/).filter(Boolean).map((t) => {
    const i = Number(t);
    if (!Number.isInteger(i) || i < 1 || i > items.length) throw new Error(`invalid choice: ${t}`);
    return items[i - 1];
  });
  return [...new Set(picked)];
}
