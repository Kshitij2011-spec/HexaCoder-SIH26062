---
name: ponytail
description: Dietrich Gebert's Ponytail v4.10.0 engineering mode. Enforces minimal correct implementation, YAGNI, standard library reuse, and zero over-engineering while preserving all domain correctness requirements.
---

# Ponytail Engineering Mode (Dietrich Gebert v4.10.0)

When active, audit code and design decisions using the 7-step ladder:
1. YAGNI - does it need to exist?
2. Reuse existing codebase services.
3. Standard library first.
4. Native platform / database features first.
5. Already-installed dependencies before new ones.
6. Keep functions simple and local.
7. Minimum correct implementation.

## Review Audit Question
"Which code or abstraction can be deleted without reducing required SIH26062 operational capabilities?"
