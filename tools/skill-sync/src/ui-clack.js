import * as p from '@clack/prompts';

const orNull = (v) => (p.isCancel(v) ? null : v);

/** Prompt adapter over @clack/prompts (cancel -> null). */
export const clackUi = {
  intro: (t) => p.intro(t),
  outro: (t) => p.outro(t),
  note: (text, title) => p.note(text, title),
  select: async (o) => orNull(await p.select(o)),
  // type-to-filter; clack has no grouped variant, so "All" (groupMultiselect) is unfiltered
  multiselect: async (o) => orNull(await p.autocompleteMultiselect({ placeholder: 'type to filter', maxItems: 12, ...o, required: false })),
  groupMultiselect: async (o) => orNull(await p.groupMultiselect({ ...o, required: false })),
  confirm: async (o) => orNull(await p.confirm(o)) === true,
};
