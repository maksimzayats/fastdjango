# modern-python-template

modern-python-template is a project starter for creating new application repositories with a clean FastAPI and Django foundation.

## Language

**Prompt Template**:
An editable natural-language instruction that a project creator gives to an LLM agent to create a generated project from the template repository. The prompt template is expected to be changed by removing unwanted capabilities before use.
_Avoid_: Setup wizard, setup config, answer file

**Project Creator**:
The person using the prompt template to create a new application repository.
_Avoid_: User, template user

**Generated Project**:
The application repository produced from the template repository after a project creator gives the prompt template to an LLM agent.
_Avoid_: Scaffold, clone

**Template Repository**:
The source repository that the prompt template tells an LLM agent to use as the starting point for a generated project.
_Avoid_: Boilerplate, starter clone

**Capability**:
A named product or development feature that may be present in the prompt template and therefore present in the generated project. A capability omitted from the prompt template should be absent from the generated project, not left dormant.
_Avoid_: Option, module, plugin

**modern-python-template Base**:
The mandatory identity of every generated project: FastAPI delivery, Django ORM and admin, dependency injection, architecture guardrails, tests, linting, and typing. The modern-python-template Base is not removable through the prompt template.
_Avoid_: Core options, default capabilities

**Removable Capability**:
A capability that the project creator may remove from the prompt template, causing the LLM agent to delete it from the generated project. Removable capabilities include Celery, authentication endpoints, throttling, storage backends, observability, documentation site publishing, extra Docker services, GitHub workflows, and example domains.
_Avoid_: Optional setting, disabled feature

## Example Dialogue

Project creator: "I want a generated project from the template repository, but I do not need Celery or remote S3."

Domain expert: "Remove those removable capabilities from the prompt template before giving it to the LLM agent. Keep the modern-python-template Base intact, because that is the template identity."
