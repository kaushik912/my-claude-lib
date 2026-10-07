#!/usr/bin/env bash
# Read-only MySQL query runner. Usage: ./dbq.sh "SELECT * FROM users"
set -euo pipefail

CNF="${DBQ_CNF:-}"
LIMIT="${DBQ_LIMIT:-50}"

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 \"SQL QUERY\"" >&2
    exit 1
fi
QUERY="$1"

# guardrail: only allow read-only statements
if ! echo "$QUERY" | grep -qiE '^\s*(SELECT|SHOW|DESCRIBE|DESC|EXPLAIN)\b'; then
    echo "ERROR: only read-only queries allowed (SELECT/SHOW/DESCRIBE/EXPLAIN)" >&2
    exit 1
fi

# block chained/multi-statement queries (guardrail applies to first statement only otherwise)
if echo "$QUERY" | grep -q ';.*[^[:space:]]'; then
    echo "ERROR: multiple statements not allowed" >&2
    exit 1
fi

if [ -z "$CNF" ] || [ ! -f "$CNF" ]; then
    echo "ERROR: DBQ_CNF must point to an existing config file (got: '${CNF}'). Copy db.cnf.example anywhere, fill it in, then: export DBQ_CNF=/path/to/db.cnf" >&2
    exit 1
fi

# auto-cap unbounded SELECTs
if echo "$QUERY" | grep -qi '^\s*SELECT' && ! echo "$QUERY" | grep -qi '\bLIMIT\b'; then
    QUERY="$QUERY LIMIT $LIMIT"
fi

mysql --defaults-extra-file="$CNF" -N --batch -e "$QUERY"
