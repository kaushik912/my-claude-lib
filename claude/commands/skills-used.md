---
description: Show which skills were used in the last X minutes
argument-hint: [minutes]
---

Show skills whose `lastUsedAt` in `~/.claude.json` `skillUsage` falls within the last $ARGUMENTS minutes (default 60 if no argument given). Run:

```bash
python3 -c "
import json, datetime, sys
mins = float(sys.argv[1]) if len(sys.argv) > 1 else 60
d = json.load(open('/home/kaush/.claude.json'))
su = d.get('skillUsage', {})
cutoff = datetime.datetime.now() - datetime.timedelta(minutes=mins)
rows = [(k, v) for k, v in su.items() if datetime.datetime.fromtimestamp(v['lastUsedAt']/1000) >= cutoff]
rows.sort(key=lambda x: x[1]['lastUsedAt'])
if not rows:
    print(f'No skills used in the last {mins:g} min.')
for k, v in rows:
    ts = datetime.datetime.fromtimestamp(v['lastUsedAt']/1000).strftime('%Y-%m-%d %H:%M')
    print(f\"{ts}  {k}  ({v['usageCount']}x total)\")
" $ARGUMENTS
```

Report the output concisely — timestamp, skill name, total use count. Note this only reflects each skill's *most recent* use, so the count shown is lifetime total, not window-scoped.
