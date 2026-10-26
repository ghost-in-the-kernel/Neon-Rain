# Dependencies: adding, changing or removing one, or touching a config or workflow (R-029)

Read this when you add, change or remove a dependency, install a package, or touch a config or
workflow. These were CLAUDE.md's supply-chain rules that apply only then (Ghost, 2026-10-26); the
reasons are in `docs/SUPPLY-CHAIN.md`.

- Never add, change or remove a dependency without a one-line reason in the decision log and human approval.
- Install only from `requirements.lock`. Never run a package's install scripts or post-install hooks.
- No GitHub Actions workflow exists in this repository (R-003). If one appears, stop and report it.
- No module imports a broker, exchange or order client, ever (R-013).
