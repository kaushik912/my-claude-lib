# Java Best Practices Handbook (2025 Edition)

> Opinionated, pragmatic guidance for production-grade Java (Java 17+ baseline).

---

## 1. Language & Style

### 1.1 Naming & Formatting
- Use **lowerCamelCase** for variables/methods, **UpperCamelCase** for classes.
- Constants are **UPPER_SNAKE_CASE**.
- 2 or 4 spaces; **no tabs**. Keep lines ≤ 120 chars.
- One class per file; keep classes focused and small.

### 1.2 Immutability by Default
- Prefer `record` for pure data carriers (Java 16+).
- Favor `private final` fields; set via constructor.
- Avoid setters; use builders for complex objects.

```java
public record Money(BigDecimal amount, Currency currency) {
    public Money add(Money other) {
        if (!currency.equals(other.currency)) throw new IllegalArgumentException("Currency mismatch");
        return new Money(amount.add(other.amount), currency);
    }
}
````

### 1.3 Explicit Visibility

* Minimize `public`; prefer `package-private` for internals.
* Keep fields `private`; expose behavior, not data.

---

## 2. Exceptions & Errors

* Use **checked exceptions** for recoverable conditions; **unchecked** for programming errors.
* Throw **specific** exceptions with actionable messages; include key identifiers, not sensitive data.
* Do not swallow exceptions. If you must catch-and-continue, **log with context**.
* Wrap third-party exceptions to maintain domain semantics.

```java
try {
    paymentGateway.charge(card, money);
} catch (GatewayTimeoutException e) {
    throw new PaymentTemporarilyUnavailable("Gateway timeout for order " + orderId, e);
}
```

* Avoid control flow via exceptions.
* Use `try-with-resources` for closables.

---

## 3. Nulls, Optionals, and Contracts

* Don’t return `null` for collections/optionals; return **empty**.
* Accept `null` only at your module boundary; validate early.
* Use `Optional` only as a **return type** (not fields/params).

```java
public Optional<User> findByEmail(String email) { ... }
// Callers:
userRepo.findByEmail(email).ifPresent(user -> ...);
```

* Document preconditions with `Objects.requireNonNull` and clear Javadoc.

---

## 4. Collections & Streams

* Choose concrete types thoughtfully:

  * `ArrayList` for random access, `LinkedList` rarely.
  * `EnumSet` / `EnumMap` for enums.
  * `ConcurrentHashMap` for concurrent access.
* Prefer `List.of(...)`, `Map.of(...)` for small immutable literals.
* Streams: keep pipelines **readable**; avoid side effects; name intermediate results.

```java
var topCustomers = customers.stream()
    .filter(c -> c.orders().size() >= 3)
    .sorted(comparingInt(c -> c.ltv()).reversed())
    .limit(10)
    .toList();
```

* Use `Collectors.groupingBy`/`mapping` judiciously; when it gets complex, refactor to loops.

---

## 5. Concurrency & Parallelism

* Favor high-level constructs: `CompletableFuture`, `ExecutorService`, structured concurrency (Project Loom when available).
* Never block on `ForkJoinPool.commonPool()` tasks.
* Size thread pools based on workload (CPU vs I/O bound).
* Make shared state **immutable**; otherwise guard with locks or use concurrent structures.
* Timeouts everywhere: HTTP, DB, message queues.

```java
var executor = Executors.newFixedThreadPool(Math.max(4, Runtime.getRuntime().availableProcessors()));
CompletableFuture
    .supplyAsync(() -> client.fetch(id), executor)
    .orTimeout(2, TimeUnit.SECONDS)
    .exceptionally(ex -> Fallbacks.empty());
```

---

## 6. I/O, HTTP, and Persistence

* Use connection pooling; close resources with try-with-resources.
* For HTTP: set read/connect **timeouts** and **retries with backoff**; avoid infinite retries.
* SQL: prefer parameterized queries; never string-concatenate user input.
* Use **migrations** (Flyway/Liquibase); no ad-hoc schema changes.
* Keep transactions **short**; avoid long-running business logic inside them.

---

## 7. APIs & DTOs

* Separate **domain** from **transport** (DTOs). Don’t leak entity internals.
* Validate **inputs** (Bean Validation) at the boundary; return precise 4xx/5xx.
* Version APIs; maintain backward compatibility.
* Be **idempotent** where possible (e.g., retries with request IDs).

```java
@POST @Path("/payments")
public Response create(@Valid CreatePaymentDto dto, @HeaderParam("Idempotency-Key") String key) { ... }
```

---

## 8. Spring Boot (if applicable)

* Keep configuration in `application.yml`; override via env for prod.
* Use **constructor injection**; avoid field injection.

```java
@Service
public class BillingService {
    private final PaymentGateway gateway;
    public BillingService(PaymentGateway gateway) { this.gateway = gateway; }
}
```

* Slice tests (`@WebMvcTest`, `@DataJpaTest`) for speed; use Testcontainers for integration tests.
* Fail fast on startup: missing configs, invalid profiles.

---

## 9. Logging, Observability, Resilience

* Use **SLF4J** with parameterized logs; avoid string concatenation.
* Log **once** at the appropriate layer; include correlation/request IDs.
* Metrics: latency, error rate, throughput, resource usage. Expose Prometheus/OTel.
* Tracing: add spans for external calls and DB operations.
* Resilience: circuit breakers, bulkheads, rate limits, timeouts, retries (jittered).

```java
log.info("Charge initiated orderId={} amount={} currency={}", orderId, amount, currency);
// No PII or secrets in logs.
```

---

## 10. Security

* Never log secrets/PII; mask sensitive fields.
* Use `char[]` for passwords in memory where practical; clear after use.
* Validate all inputs; encode outputs; prefer allow-lists.
* Keep dependencies patched; watch CVEs.
* Use **prepared statements**; parameterize ORM queries.
* Implement CSRF protection for state-changing web endpoints.
* Enforce TLS; verify hostnames; pin certs where warranted.
* Principle of least privilege for DB/users/services.

---

## 11. Performance & Memory

* Measure, don’t guess: JMH for microbenchmarks; production metrics for real behavior.
* Avoid premature optimization; choose clear code first.
* Prefer immutable objects and minimal allocations in hot paths.
* Cache carefully with clear TTL/invalidations (Caffeine recommended).
* Beware boxing/unboxing in tight loops; prefer primitives.

---

## 12. Testing Strategy

* Pyramid: many unit tests, fewer integration, minimal E2E but meaningful.
* Fast, deterministic, isolated unit tests.
* Use **Testcontainers** for DB/queue integration tests.
* Contract tests for inter-service APIs.
* Given-When-Then naming; assert behavior, not implementation details.

```java
@Test
void calculatesTotalWithTaxes() {
    var cart = new Cart(List.of(new Item("book", 1000)));
    assertThat(cart.totalWithTax(Tax.of(0.07))).isEqualTo(1070);
}
```

---

## 13. Build, Dependencies, Packaging

* Prefer **Gradle** or **Maven** with dependency locking.
* Keep dependency graph small; remove unused libs.
* Use semantic version ranges cautiously; pin critical libs.
* Produce **fat JAR** or container image; set explicit JVM flags for memory.

---

## 14. Deployment & Runtime

* Externalize config via env/secret stores; no secrets in repo.
* Health endpoints: liveness/readiness.
* Graceful shutdown: handle SIGTERM; set `server.shutdown.grace-period`.
* GC: use G1GC/ZGC defaults unless profiling suggests otherwise.
* Observability baked in: logs to stdout, metrics + traces exported.

---

## 15. Documentation & Reviews

* Javadoc public APIs; README for modules with run/debug steps.
* Architecture decision records (ADRs) for significant choices.
* Code reviews: correctness, clarity, tests, security considerations.
* Small PRs (< 400 LOC) encouraged; CI must be green.

---

## 16. Quick Checklists

**PR Checklist**

* [ ] Tests added/updated
* [ ] Logging at appropriate levels, no secrets
* [ ] Errors mapped to domain exceptions
* [ ] Timeouts/retries configured
* [ ] Docs updated (README/ADR)

**Service Readiness**

* [ ] Liveness/readiness probes
* [ ] Metrics & traces
* [ ] Rate limits/circuit breakers
* [ ] Config via env; secrets sealed
* [ ] Idempotency on external calls

---

## 17. Anti-Patterns to Avoid

* God classes; cyclic dependencies
* Overuse of `@Transactional` at controller layer
* Catch-all `Exception` without action
* Using `Optional` for fields/params
* Excessive static state / singletons
* Business logic in DTOs or controllers
* Logging stack traces at INFO
* Returning `null` collections

---

*(End of Handbook)*