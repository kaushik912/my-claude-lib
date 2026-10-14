# Bug Fixes: Failing Test First

For any bug fix (any project, any language), prove the bug with a test before
fixing it:

1. **Reproduce**: write a test that captures the bug.
2. **Red**: run it. It must fail with the bug's symptom, not a setup error
   (connection refused, wrong path, missing fixture). If it can't fail
   for the right reason, fix the test first.
3. **Fix** the code.
4. **Green**: run the test again. It must pass. Keep the test.

Skip for typos, docs-only, and config-only changes. If the bug can't be
reproduced in a test (race, environment-only), say so and ask the user.

Non-API bugs (pure logic): a failing unit test in the project's existing test
framework. No special shape.

If a test already covers the same endpoint and condition, extend it instead of
adding a duplicate.

## Java / API bugs

Before writing the test, brainstorm the exact scenario with the user in BDD
style (Given/When/Then, plain English): what a client sends, what it should
get back, what it gets today. Then write it with RestAssured, Bruno, Postman,
or equivalent. Use whatever the project already has. Defaults: Java/Spring
(pom.xml/build.gradle) → RestAssured; otherwise → Bruno.

### Bruno shape

Find or create the collection (a directory with `bruno.json`). If none exists,
confirm with the user, then scaffold `regressions/`. Check the project's real
port (server config, README, docker-compose) before defaulting to 8080:

```
regressions/
├── bruno.json          { "version": "1", "name": "regressions", "type": "collection" }
├── environments/
│   └── local.bru        vars { baseUrl: http://localhost:8080 }
└── BUG-<id-or-date>-<slug>.bru
```

Example: `regressions/BUG-JIRA-123-null-email-500.bru`. The `docs{}` block is plain
English, no jargon or code, with a `Bug:` line:

```
docs {
  Bug: <id, e.g. JIRA-123 — or a short description if no id>
  Scenario: user signs up with an email already in use.
  Expected: 409 with a clear "email taken" message. Bug: server 500'd.
}
```

Run: `bru run regressions/<file>.bru --env local` (exit code 1 = failing).

### RestAssured shape

JUnit 5 + `io.rest-assured:rest-assured`, under the project's existing test source
root (e.g. `src/test/java/**/regression/`). Method named
`given<Condition>_when<Action>_then<Outcome>`, with Given/When/Then comments
and a one-line bug note above it:

```java
// Bug: JIRA-123 — or a short description if no id
@Test
void givenEmailAlreadyInUse_whenSignUp_thenReturns409() {
    // Given
    userRepository.save(new User("taken@example.com"));

    // When / Then
    // Expected: 409 with a clear "email taken" message. Bug: server 500'd.
    given()
        .contentType(ContentType.JSON)
        .body(new SignUpRequest("taken@example.com"))
    .when()
        .post("/signup")
    .then()
        .statusCode(409)
        .body("message", containsString("email"));
}
```

Run: `mvn test -Dtest=<Class>` or `./gradlew test --tests <Class>`.
