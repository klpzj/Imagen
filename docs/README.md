# WebUI Design Documentation

Read these documents in order when implementing the Vue WebUI.

1. [WebUI module design](webui-module-design.md)
   - Overall architecture, module boundaries, directory plan, and first version
     workflow.
2. [Backend modules](backend-modules.md)
   - FastAPI module responsibilities, route ownership, config handling, service
     layer, and manifest storage.
3. [Frontend modules](frontend-modules.md)
   - Vue component split, API client, store, shared types, and styling rules.
4. [API and data contract](api-and-data-contract.md)
   - Exact request/response shapes between backend and frontend.
5. [Implementation plan](implementation-plan.md)
   - Phased build order with acceptance checks.
6. [Decision log](decision-log.md)
   - Key architectural decisions and reasons.
7. [Consistency audit](consistency-audit.md)
   - Current implementation alignment, remaining compatibility notes, and
     backlog boundaries.
8. [Three-Codex work allocation](three-codex-work-allocation.md)
   - Parallel construction split, interface alignment surface, merge order, and
     worker prompts.
9. [V1 integration verification](v1-integration-verification.md)
   - Final V1 verification commands, results, and generated output path.

Current implementation target:

- Local WebUI with text generation, image editing, preview, download, history,
  history deletion, failed task display, and refresh-safe job state.
- Keep canvas mask painting, multi-job queue management, user accounts, and
  production deployment in the backlog.
- If using parallel Codex workers, follow
  [Three-Codex work allocation](three-codex-work-allocation.md).
