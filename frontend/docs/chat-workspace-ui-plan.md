# Chat Workspace UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the demo platform frontend as a production-shaped React chat workspace inspired by modern AI chat products, without preserving the old `/demo` route.

**Architecture:** Keep the existing React 18 + Vite + TypeScript stack and backend API contracts. Replace the current demo-first route with `/chat`, split the UI into stable product areas, and keep streaming diagnosis behavior wired to `runChatStream`.

**Tech Stack:** React 18, TypeScript, React Router, Vite, ECharts, Vitest, Testing Library.

---

### Task 1: Route Contract

**Files:**
- Modify: `frontend/src/router.tsx`
- Test: `frontend/src/router.test.tsx`

- [ ] Write failing tests that assert `/` redirects to `/chat`, `/chat` renders the diagnosis chat workspace, and `/demo` no longer renders a compatibility route.
- [ ] Add Vitest and Testing Library config to Vite.
- [ ] Update routes to use `/chat` as the product entry point and keep `/records`, `/history`, `/admin/login`, and `/admin`.
- [ ] Run `npm test -- --run`.

### Task 2: Product Layout

**Files:**
- Modify: `frontend/src/components/AppShell.tsx`
- Modify: `frontend/src/styles.css`
- Test: `frontend/src/components/AppShell.test.tsx`

- [ ] Write failing tests for the left navigation labels and product shell landmarks.
- [ ] Replace the old demo sidebar copy with a chat-product shell: new diagnosis, conversations, records, history, admin.
- [ ] Add responsive layout CSS for desktop sidebar and mobile top navigation.
- [ ] Run `npm test -- --run`.

### Task 3: Chat Workspace

**Files:**
- Create: `frontend/src/pages/ChatPage.tsx`
- Modify: `frontend/src/router.tsx`
- Modify: `frontend/src/styles.css`
- Test: `frontend/src/pages/ChatPage.test.tsx`

- [ ] Write failing tests for welcome state, sample selection, locked invite state, and composer affordances.
- [ ] Move the useful streaming logic from `DemoPage` into `ChatPage` with a clearer three-area layout.
- [ ] Keep real API integration through `runChatStream`; do not replace it with static fake chat.
- [ ] Run `npm test -- --run`.

### Task 4: Verification

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`

- [ ] Add `test` script and required test dependencies.
- [ ] Run `npm test -- --run`.
- [ ] Run `npm run build`.
- [ ] Start the Vite dev server and inspect `/chat` in a browser for desktop and mobile layout.
