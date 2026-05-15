# Decision: Ignore Lovable Cloud / TanStack Scaffold

**Date:** 2026-05-15

## Decision
This project does NOT use Lovable Cloud, edge functions, server functions, or the TanStack Start scaffold. The only product is the Python CLI under `tools/jpg2pdf/`.

## Rationale
- `jpg2pdf` is a desktop CLI tool. No backend, no web UI, no auth, no DB.
- The TanStack scaffold (`src/`, `vite.config.ts`, `wrangler.jsonc`, `src/integrations/...`) is leftover Lovable template boilerplate.

## Implications
- Do NOT enable Lovable Cloud unless the user explicitly asks for a web companion.
- Do NOT add `createServerFn` or routes for jpg2pdf features.
- Build/typecheck the React scaffold may still run (harmless), but no feature work goes there.
