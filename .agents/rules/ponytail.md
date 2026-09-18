# Ponytail Engineering Mode (Dietrich Gebert v4.10.0) — Antigravity Integration

## Core Thesis
"Understand the problem first. The best code is the code you never wrote."

## The Seven-Step Decision Ladder
Before writing any code or introducing an abstraction, ask:
1. **YAGNI**: Does the feature or abstraction actually need to exist right now?
2. **Reuse Existing**: Does the codebase already have this logic or service?
3. **Standard Library**: Does the standard library (Python `sys`, `collections`, `itertools`, `datetime`, `uuid`, etc.) provide it?
4. **Native Platform**: Does the database (PostgreSQL indexes, constraints, recursive CTEs) or OS provide it natively?
5. **Installed Dependency**: Does an already installed dependency (SQLAlchemy, Pydantic, FastAPI) solve it cleanly?
6. **One-Liner / Simple Function**: Can it be a clean, simple, local deterministic function?
7. **Minimum Correct Implementation**: Only then, write the minimum new code required to solve the problem correctly.

## Project Override: MINIMAL != INCOMPLETE
In the SIH26062 Polar Logistics Monolith:
- **Do NOT** strip out required architectural invariants:
  - Event correlation chains (`correlation_id`)
  - Semantic dependency types (`REQUIRES`, `SUPPORTS`, `ASSIGNED_TO`, etc.)
  - Transactional consistency (state mutation + operational event + audit log)
  - Explicit human approval boundaries
  - Bounded graph traversal and cycle safety
  - Explicit multi-state constraint outcomes (`SATISFIED`, `VIOLATED`, `NOT_EVALUABLE`)
  - Explicit readiness states (`READY`, `AT_RISK`, `BLOCKED`) with blockers and unknowns
- **Do NOT** build:
  - Strategy-pattern forests
  - Speculative plugin architectures
  - Generic rule interpreters / code-eval engines
  - Unnecessary microservices or external message brokers (Kafka/Redis/Celery)
