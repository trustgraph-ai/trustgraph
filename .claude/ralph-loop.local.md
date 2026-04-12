---
active: true
iteration: 1
session_id: 
max_iterations: 10
completion_promise: "ALL_CLEAR"
started_at: "2026-04-10T22:12:33Z"
---

Run a full QA pass on the TrustGraph Workbench at localhost:5173. Launch 6 parallel QA agents using the Agent tool with mcp__claude-in-chrome__* browser tools. Agent assignments: Agent 1: /chat + /library. Agent 2: /graph + /prompts. Agent 3: /token-cost + /knowledge-cores. Agent 4: /flows + /settings. Agent 5: sidebar, root-layout, skip-link, loading bar, disconnection banner (viewport 1440x900, test both dark+light mode). Agent 6: responsive at 768x600 across all 8 pages + keyboard navigation (Tab/Shift+Tab/Enter/Escape) on dialogs (/library upload, /flows start/stop). Each agent checks: (a) visual - page loads fully, icons visible, no overflow/clipping; (b) a11y - aria-labels, htmlFor/id label pairs, heading hierarchy, color contrast (no raw amber/yellow on dark bg), focus indicators; (c) functional - buttons respond, toggles work, dialogs open/close/trap focus, loading states display; (d) responsive - content wraps, no horizontal scrollbar, tables scroll. Each agent outputs: AGENT N REPORT - PAGE: /path - ISSUES FOUND: count - then per issue: [SEVERITY:critical|major|minor] [CATEGORY:visual|a11y|functional|responsive] file_path:line description. After all agents complete, aggregate. If total issues == 0, output <promise>ALL_CLEAR</promise>. If issues > 0, fix them by editing source files in ts/packages/workbench/src/, run 'cd /home/elpresidank/YeeBois/dev/trustgraph/ts && pnpm build' to verify, then exit so the loop re-runs.
