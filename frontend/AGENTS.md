# Frontend AGENTS

## Purpose
Guidance for agents editing React routes, pages, components, and frontend API integration.

## Runtime Entry and Structure
- Entry: `frontend/src/main.tsx`
- Router: `frontend/src/App.tsx`
- Shared layout shell: `frontend/src/layout/Layout.tsx`

## Active Routed Pages
- Public marketing: `frontend/src/pages/Landing.tsx` at `/`
- Public auth:
  - `frontend/src/pages/auth/Login.tsx`
  - `frontend/src/pages/auth/Register.tsx`
  - `frontend/src/pages/auth/ForgotPassword.tsx`
- App shell (sidebar layout) is mounted at **`/app`** (`APP_BASE` in `frontend/src/lib/appPaths.ts`):
  - `frontend/src/pages/Workspace.tsx` (index: `/app`)
  - `frontend/src/pages/Chat.tsx` (`/app/chat`)
  - `frontend/src/pages/Documents.tsx` (`/app/documents`)
  - `frontend/src/pages/Cases.tsx` (`/app/cases`)
  - `frontend/src/pages/Profile.tsx` (`/app/profile`)
  - `frontend/src/pages/auth/ChangeEmail.tsx` (`/app/settings/email`)
- Legacy paths (`/chat`, `/documents`, `/cases`, `/profile`, `/settings/email`) redirect into `/app/...`.

## Commands
- Dev: `npm run dev`
- Build/typecheck: `npm run build`
- Lint: `npm run lint`
- Preview: `npm run preview`

## Editing Rules
- Keep route definitions synchronized in `App.tsx`.
- Do not delete pages/components without first checking imports/usages.
- Prefer existing shared components/utilities over introducing duplicates.
- Keep legal-domain copy professional and consistent.

## API Integration Rules
- Keep API access patterns centralized through existing lib helpers.
- If backend payload shape changes, update parsing + error/empty state handling together.
- Validate auth-protected route behavior after auth-related changes.

## Validation Checklist
- Run `npm run build` after substantial changes.
- Run `npm run lint` when touching component/page logic.
- Manually verify navigation for changed routes/components.
