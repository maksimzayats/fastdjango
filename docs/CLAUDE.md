# CLAUDE.md - Documentation Guidelines

This file provides guidance for maintaining and extending the documentation in this repository.

## Documentation Framework: Diátaxis

We follow the [Diátaxis framework](https://diataxis.fr/) which organizes documentation into four distinct types:

| Type | Purpose | User Need | Writing Style |
|------|---------|-----------|---------------|
| **Tutorials** | Learning-oriented | "I want to learn" | Step-by-step, hands-on |
| **How-To Guides** | Task-oriented | "I want to do X" | Focused, practical |
| **Concepts** | Understanding-oriented | "I want to understand" | Explanatory, theoretical |
| **Reference** | Information-oriented | "I need facts" | Accurate, complete |

### Key Principle

Never mix these types. A tutorial should not explain theory (that's Concepts). A how-to should not teach fundamentals (that's Tutorials).

## Directory Structure

```
docs/
├── CLAUDE.md              # This file - documentation guidelines
├── mkdocs.yml             # MkDocs configuration and navigation
└── en/                    # English documentation
    ├── index.md           # Landing page
    ├── getting-started/   # Onboarding section
    │   ├── index.md
    │   ├── quick-start.md
    │   ├── project-structure.md
    │   └── development-environment.md
    ├── tutorial/          # Step-by-step Todo List tutorial
    │   ├── index.md
    │   ├── 01-model-and-service.md
    │   ├── 02-ioc-registration.md
    │   ├── 03-http-api.md
    │   ├── 04-celery-tasks.md
    │   ├── 05-observability.md
    │   └── 06-testing.md
    ├── concepts/          # Architectural explanations
    │   ├── index.md
    │   ├── service-layer.md
    │   ├── ioc-container.md
    │   ├── controller-pattern.md
    │   ├── factory-pattern.md
    │   └── pydantic-settings.md
    ├── how-to/            # Task-focused guides
    │   ├── index.md
    │   ├── add-new-domain.md
    │   ├── custom-exception-handling.md
    │   ├── override-ioc-in-tests.md
    │   ├── add-celery-task.md
    │   ├── secure-endpoints.md
    │   └── configure-observability.md
    └── reference/         # Technical reference
        ├── index.md
        ├── environment-variables.md
        ├── makefile.md
        └── docker-services.md
```

## Writing Conventions

### File Headers

Every documentation file should start with a clear title and brief description:

```markdown
# Page Title

Brief one-paragraph description of what this page covers and who it's for.
```

### Admonitions

Use MkDocs Material admonitions for callouts:

```markdown
!!! note "Title"
    Content here.

!!! tip "Title"
    Helpful tips.

!!! warning "Title"
    Cautions and warnings.

!!! danger "Title"
    Critical warnings.

!!! info "Title"
    Additional context.
```

### Code Blocks

Always specify the language and include file path comments for context:

```python
# src/core/todo/services.py
from core.exceptions import ApplicationError

class TodoNotFoundError(ApplicationError):
    """Raised when a todo item cannot be found."""
```

### Cross-References

Link between documentation sections using relative paths:

```markdown
> **See also:** [Service Layer concept](../concepts/service-layer.md)
```

### Tables for File Actions

In tutorials, use tables to show which files are created/modified:

```markdown
| Action | File Path |
|--------|-----------|
| Create | `src/core/todo/models.py` |
| Modify | `src/ioc/container.py` |
```

## Tutorial-Specific Guidelines

### The Todo List Feature

The tutorial uses a **Todo List** as the central example because:
- It's universally understood
- It demonstrates CRUD operations
- It naturally involves user ownership (FK to User)
- It's simple enough to not distract from architecture

### Tutorial Scope

The tutorial covers:
- HTTP API (FastAPI)
- Celery tasks
- Admin panel
- Observability (Logfire)
- Testing

The tutorial does **NOT** cover:
- Advanced authentication flows
- Production deployment

### Step Structure

Each tutorial step should follow this structure:

1. **Opening**: What you'll build and prerequisites
2. **File Action Table**: Which files to create/modify
3. **Concept Link**: Reference to relevant concept page
4. **Step-by-Step Instructions**: Numbered steps with code
5. **Verification**: How to confirm it works
6. **Summary**: What was accomplished
7. **Next Step Link**: Navigation to next tutorial step

### Service Docstring Convention

When documenting services that raise exceptions, always include a `Raises:` section:

```python
def get_todo_by_id(self, todo_id: int, user: User) -> Todo:
    """Retrieve a todo item by ID for a specific user.

    Args:
        todo_id: The unique identifier of the todo item.
        user: The user requesting the todo.

    Returns:
        The Todo instance if found and owned by the user.

    Raises:
        TodoNotFoundError: If the todo does not exist.
        TodoAccessDeniedError: If the todo belongs to another user.
    """
```

## Concepts-Specific Guidelines

### The Golden Rule

Always emphasize the architectural boundary:

```
Controller → Service → Model

✅ Controller imports Service
✅ Service imports Model
❌ Controller imports Model (NEVER)
```

### ASCII Diagrams

Use ASCII art for architecture diagrams:

```
┌─────────────────────────────────────────────────────────────┐
│                     Delivery Layer                          │
│  ┌─────────────────────────┐  ┌─────────────────────────┐  │
│  │        HTTP API         │  │      Celery Tasks       │  │
│  │      Controllers        │  │      Controllers        │  │
│  └───────────┬─────────────┘  └───────────┬─────────────┘  │
└──────────────┼────────────────────────────┼─────────────────┘
               │                            │
               ▼                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Core Layer                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    Services                          │   │
│  │   UserService  │  TodoService  │  HealthService     │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                     Models                           │   │
│  │      User      │     Todo      │    Session         │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## How-To-Specific Guidelines

### Focus on the Task

How-to guides should:
- Start with a clear goal statement
- List prerequisites
- Provide numbered steps
- End with verification

How-to guides should NOT:
- Explain underlying theory (link to Concepts instead)
- Cover every possible variation
- Include lengthy code explanations

### Checklist Format

For multi-step processes like adding a new domain, use checklists:

```markdown
## Checklist

- [ ] Create Django app in `core/<domain>/`
- [ ] Add to `installed_apps` in Pydantic settings
- [ ] Create model in `models.py`
- [ ] Create service in `services.py`
- [ ] Register service in IoC
- [ ] Create controller
- [ ] Register controller in IoC
- [ ] Update factory
- [ ] Run migrations
- [ ] Write tests
```

## Reference-Specific Guidelines

### Tables for Data

Use tables for environment variables, commands, and configuration:

```markdown
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DJANGO_SECRET_KEY` | Yes | - | Django secret key |
| `DJANGO_DEBUG` | No | `false` | Enable debug mode |
```

### Complete Coverage

Reference documentation must be:
- Complete (all options documented)
- Accurate (matches actual behavior)
- Searchable (good headings and structure)

## Adding New Documentation

### Adding a New Concept

1. Create `docs/en/concepts/<concept-name>.md`
2. Add to `nav` section in `docs/mkdocs.yml`
3. Link from `docs/en/concepts/index.md`
4. Cross-reference from relevant tutorials/how-tos

### Adding a New How-To Guide

1. Create `docs/en/how-to/<task-name>.md`
2. Add to `nav` section in `docs/mkdocs.yml`
3. Link from `docs/en/how-to/index.md`
4. Link from related concept pages

### Extending the Tutorial

If adding a new tutorial step:
1. Create `docs/en/tutorial/0X-<step-name>.md`
2. Update navigation links in adjacent steps
3. Add to `nav` section in `docs/mkdocs.yml`
4. Update `docs/en/tutorial/index.md`

## Code Examples Must Match Reality

All code examples should:
1. **Compile/run** - No syntax errors
2. **Follow project patterns** - Match existing code style
3. **Use real imports** - Not placeholder paths
4. **Include file paths** - Show where code goes

When codebase changes, documentation must be updated to match.

## Testing Documentation

```bash
# Build documentation (checks for broken links)
make docs-build

# Serve locally with live reload
make docs
```

## Navigation Structure (mkdocs.yml)

The `nav` section in `mkdocs.yml` defines the sidebar structure:

```yaml
nav:
  - Home: index.md
  - Getting Started:
    - getting-started/index.md
    - Quick Start: getting-started/quick-start.md
    # ...
  - "Tutorial: Build a Todo List":
    - tutorial/index.md
    - "Step 1: Model & Service": tutorial/01-model-and-service.md
    # ...
```

Key patterns:
- Use quoted strings for titles with special characters
- Index pages use the directory format (`section/index.md`)
- Named pages use the label format (`Label: path.md`)

## Style Guide Summary

| Element | Convention |
|---------|------------|
| Headings | Title Case for H1, Sentence case for H2+ |
| Code paths | Backticks: `src/core/todo/` |
| Commands | Code blocks with `bash` language |
| Python code | Include file path as comment |
| Lists | Use `-` for unordered, `1.` for ordered |
| Links | Relative paths: `../concepts/service-layer.md` |
| Emphasis | **Bold** for UI elements, *italic* for terms |

## Maintenance Checklist

When updating documentation:

- [ ] Does the code example match current codebase?
- [ ] Are all cross-references valid?
- [ ] Is the nav updated in `mkdocs.yml`?
- [ ] Does `make docs-build` succeed?
- [ ] Are admonitions used appropriately?
- [ ] Is the writing style consistent with section type?
