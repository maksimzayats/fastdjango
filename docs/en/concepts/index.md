# Concepts

The template is organized around a small set of rules:

- Keep application behavior in inner modules under each `core` business package.
- Keep domain-specific delivery and SQLAlchemy adapters under that business package.
- Keep shared technical wiring in top-level `infrastructure`.
- Keep app construction and dependency wiring at the edge.
- Use Pydantic DTOs for application data and FastAPI schemas for HTTP delivery.
