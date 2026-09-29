---
name: jdb-attach
disable-model-invocation: true
description: >-
  Use when debugging a running Java/Spring Boot app, or when the user asks
  for a debugging skill/debugger, breakpoint, step-through, stack trace,
  variable inspection, or "attach jdb". Attaches the JDK's `jdb` debugger to
  a running JVM over its JDWP port, sets breakpoints, and inspects state — no
  log/println instrumentation needed.
license: MIT
compatibility: "Requires a JDK (jdb ships with every JDK, 8+) on the machine driving the debug session — does not need to match the target JVM's version exactly, but keep major versions close. Target app must be started with JDWP enabled (server=y)."
metadata:
  author: kaushik912
  version: "1.0.0"
  category: development
  tags: ["jdb", "jdwp", "debugging", "java", "spring-boot", "cli"]
---
# jdb Attach — Non-Intrusive Java/Spring Boot Debugging

## Overview

`jdb` is the DAP-equivalent debugger that ships with every JDK. It speaks
JDWP directly — no translation layer, no adapter, no MCP server needed. This
skill drives it as a persistent background session via a named pipe (FIFO),
since `jdb` is interactive and each Bash tool call is a one-shot shell.

This was chosen after `dap-mcp-server` and `claude-mcp-debugger` both turned
out not to support attaching to a running JVM's JDWP port (dap-mcp-server has
no Java adapter at all; claude-mcp-debugger's Java support is launch-only,
single-file `javac`-compiled, no attach mode). `jdb` needs none of that.

## Prerequisites

1. Confirm JDWP port is open (default assumed `5005`, ask if different):
   ```bash
   nc -z -v -w3 localhost 5005 2>/dev/null || lsof -i :5005
   ```
2. If closed, tell the user to start Spring Boot with JDWP, e.g.:
   ```bash
   ./mvnw spring-boot:run -Dspring-boot.run.jvmArguments="-agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address=*:5005"
   ```
   IntelliJ: same `-agentlib:jdwp=...` string in VM Options, then **Run** (not Debug) — Debug mode holds the port itself and `jdb` can't also attach to it.
3. `jdb` is part of the JDK — check with `command -v jdb`.

## Step 1: Start a persistent jdb session

Use a FIFO opened read-write so it never sees EOF between commands (each
Bash call is a separate shell — a plain `>` write would close and kill jdb
otherwise):

```bash
mkfifo /tmp/jdb-5005.in 2>/dev/null
jdb -attach localhost:5005 -sourcepath src/main/java \
  <> /tmp/jdb-5005.in > /tmp/jdb-5005.out 2>&1 &
disown
sleep 1
cat /tmp/jdb-5005.out
```

Confirm the output shows a successful attach (no `VMDisconnectedException`).
`-sourcepath` is only needed for `list`/source display — breakpoints and
`print`/`dump` work without it.

## Step 2: Set breakpoint(s)

Fully-qualified class name (dots, not file path), then line number:

```bash
echo "stop at com.example.demo.controller.UserController:42" > /tmp/jdb-5005.in
sleep 1
tail -n 10 /tmp/jdb-5005.out
```

If the class isn't loaded yet, jdb defers it automatically ("It will be set
after the class is loaded") — no extra step needed.

## Step 3: Trigger the endpoint

Run in the background — the request will hang once the thread hits the
breakpoint, until you `cont`:

```bash
curl -i -X POST http://localhost:8080/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Test User", "email": "invalid-email"}' &
sleep 2
tail -n 20 /tmp/jdb-5005.out
```

Look for `Breakpoint hit` in the output.

## Step 4: Inspect

```bash
echo "where" > /tmp/jdb-5005.in        # stack trace
echo "locals" > /tmp/jdb-5005.in       # local variables in current frame
echo "print userDto.getEmail()" > /tmp/jdb-5005.in
echo "dump userDto" > /tmp/jdb-5005.in # full field dump
sleep 1
tail -n 30 /tmp/jdb-5005.out
```

Repeat with more `print`/`dump` calls as needed. Each is a separate `echo`
followed by a short `sleep` + `tail` to read the response — jdb is
synchronous per command.

## Step 5: Resume, clean up, detach

```bash
echo "cont" > /tmp/jdb-5005.in                                  # let the thread finish
echo "clear com.example.demo.controller.UserController:42" > /tmp/jdb-5005.in
echo "exit" > /tmp/jdb-5005.in                                   # detach only — does NOT kill the app in attach mode
rm -f /tmp/jdb-5005.in /tmp/jdb-5005.out
```

Then formulate the fix and (per the `regression-testing` rule) offer a
regression test — write it, don't leave `println`/log statements behind.

## Safety guidelines

- **Port conflict**: never attach if an IDE debugger already holds the port
  (IntelliJ's *Debug* run mode does). Confirm the app was started with
  *Run*, not *Debug*, or from the terminal directly.
- **Timeouts**: the HTTP client will time out if the thread stays suspended
  too long. Do inspection fast; `cont` as soon as you have what you need.
- **Multiple breakpoints**: FQCN:line per `stop at` call; `clear` each
  before exiting to leave the JVM state clean.
- **Never** leave `System.out.println`/temporary logging behind — this
  workflow exists specifically to avoid that.
