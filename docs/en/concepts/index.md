# Concepts

The template is organized around a small set of rules:

- Keep application behavior in `core`.
- Keep framework and persistence adapters in `infrastructure`.
- Keep app construction and dependency wiring at the edge.
- Use Pydantic DTOs for application data and FastAPI schemas for HTTP delivery.
