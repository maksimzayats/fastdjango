# Migration Reference

Use this file when refactoring an existing repo toward the clean architecture
style without rewriting everything at once.

## Migration Loop

Migrate one user-facing behavior at a time:

1. Identify the current entrypoint path for the behavior.
2. Characterize current behavior with focused tests if coverage is weak.
3. Create or choose the use case that owns the application flow.
4. Move reusable behavior into focused services.
5. Move framework parsing/serialization into delivery code.
6. Move external IO behind infrastructure code or a justified core-owned ABC.
7. Wire dependencies in `ioc/`.
8. Run the smallest relevant checks.
9. Repeat with the next behavior.

Do not start with a broad folder shuffle. Move code only when the behavioral path
is understood.

## Choosing the First Slice

Start with a small path that has clear inputs and outputs:

- registration;
- login/token issue;
- health check;
- command-line import;
- one background task;
- one webhook handler.

Avoid starting with the most complex workflow unless the user explicitly asks
for it.

## Preserve Behavior

Before moving logic:

- read existing tests;
- run the current relevant checks if practical;
- add a small characterization test when behavior is unclear;
- note external side effects and framework lifecycle assumptions.

Keep old and new paths side by side only when needed for a safe transition.
Remove dead code once the migrated path is active and tested.

## Refactor Order

Good order:

1. Extract command/result DTOs if the method signature is noisy.
2. Extract focused services for reusable behavior.
3. Introduce a use case around the externally meaningful action.
4. Move framework-specific parsing/serialization into delivery code.
5. Add or update `diwire` registrations for abstractions and adapters.
6. Tighten tests and architecture guardrails.

Do not add every possible abstraction before the first use case works.

## Stop Conditions

Stop a migration slice when:

- behavior is preserved;
- the new use case/service boundary is wired;
- tests cover the moved behavior;
- relevant lint/type/test checks pass or known failures are reported;
- no unrelated folders were reorganized.

Leave the repo in a state where another small slice can continue later.
