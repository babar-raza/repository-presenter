# Repository Presenter

Repository Presenter is an autonomous, GitHub-native system that keeps the README files of
authorized product repositories accurate, credible, repository-specific, and current. It combines
deterministic evidence, validation, state, and safety controls with a configurable LLM for product
interpretation, editorial planning, composition, and independent review. README health is the
foundational component; other repository-presentation surfaces follow through the same core.

## Status

Run `repository-presenter status` for the current gate, work item, and the only progress metric:
current reviewable no-op-proven README candidates out of 34. `project/state.yaml` is the live
cursor; this file never restates it. The project succeeds the legacy
`babar-raza/foss-readme-optimizer` repository, whose reusable behavior migrates here only through
`migration/reuse-manifest.yaml`.

## Authority

| Subject | Document |
|---|---|
| Product outcome and standing constraints | [`plans/idea.md`](plans/idea.md) |
| Agent conduct, safety, work loop | [`AGENTS.md`](AGENTS.md) |
| Build order, gates, acceptance | [`docs/EXECUTION_STATE_MACHINE.md`](docs/EXECUTION_STATE_MACHINE.md) |
| Production runtime behavior | [`docs/STATE_MACHINE.md`](docs/STATE_MACHINE.md) |
| Candidate README shape, assembly, agentic decisions, blocking checks | [`docs/README_CONTRACT.md`](docs/README_CONTRACT.md) |
| Research record and design reasoning | [`docs/RESEARCH_AND_GUIDELINES.md`](docs/RESEARCH_AND_GUIDELINES.md) |
| Live implementation cursor | [`project/state.yaml`](project/state.yaml) |
| Legacy-code disposition | [`migration/reuse-manifest.yaml`](migration/reuse-manifest.yaml) |

Read order for a new session is defined in `AGENTS.md`.

## License

MIT. See [`LICENSE`](LICENSE).
