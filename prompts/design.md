# Master prompt: automated job search pipeline (zero-cost)

Use this as a standalone prompt for Claude, Claude Code, or any capable assistant to design and implement the full system. Paste it as-is, or hand off one section at a time.

---

## Objective

Design and build a fully automated, zero-cost job search pipeline that:
1. Sources job postings from free channels on a schedule
2. Ranks each posting against my CV/skill profile
3. Customizes my LaTeX CV per job using only pre-approved, verified content
4. Compiles a tailored PDF
5. Stores the result and logs it in a tracker
6. Routes each application to either an auto-apply path (email-only) or a manual review queue — never auto-submits to ATS platforms

Every component must run on free tiers only: GitHub Actions, Google Sheets/Docs/Drive/Apps Script, free-tier job APIs, and open-source libraries.

## Hard constraints (non-negotiable)

- **No fabricated CV content.** The customization step may only select, reorder, or omit bullets from a pre-written, human-approved "bullet bank." It must never generate new claims, metrics, or experience.
- **No auto-submission to ATS platforms** (LinkedIn Easy Apply, Workday, Greenhouse, Lever, etc.) — this violates their ToS and risks account bans. Auto-apply is permitted only when a plain company email address is the stated application channel.
- **No paid APIs or subscriptions** at any stage. Free tiers only (state the specific free tier/limit used at each step).
- **Every generated CV variant must be traceable** — log which bullets were selected and why (matched keywords) so I can audit output.
- **Ask before finalizing anything that touches factual CV content** — if a step would require inventing or inferring unverified details, stop and flag it instead of proceeding.

## Architecture to design

### 1. Sourcing
- Pull listings from free sources: RSS feeds from job boards, Google Alerts, free-tier APIs (e.g. Adzuna, RemoteOK, Arbeitnow, USAJobs).
- Run on a schedule via GitHub Actions (free minutes on public repos).
- Normalize all postings into a common schema: `title, company, description, url, source, date_posted, apply_method (email/ats/unknown)`.

### 2. Matching and ranking
- Maintain a structured skill/keyword profile representing my CV (skills, technologies, project domains).
- Score each posting against that profile (keyword overlap / TF-IDF / cosine similarity — no paid LLM required, but note where an optional LLM call could improve scoring if I later choose to add one).
- Define and justify a threshold below which jobs are logged but not processed further.
- Output: ranked list with per-job match score and matched-keyword breakdown.

### 3. CV customization
- Design a "bullet bank" format (YAML/JSON) containing every verified bullet point, tagged with the keywords/skills it demonstrates, per project (e.g. Chit-Chat, PDF Explainer AI, MediShare, Vehicle Expresso, Neighborly).
- Design a selection algorithm: given a job's matched keywords, choose the best-fitting subset of bullets per section within defined length limits.
- Design a LaTeX templating approach (e.g. Jinja2 rendering into a moderncv-based `.tex` file) that injects the selected bullets into my existing CV structure/theme.
- Explicitly flag: this step must never alter dates, titles, company names, or metrics — only bullet selection/ordering.

### 4. Compilation
- Design a free LaTeX-to-PDF compilation step using an open-source engine (e.g. tectonic or a LaTeX Docker image) inside GitHub Actions — no local LaTeX install required.
- Output: one PDF per job, named predictably (e.g. `Company_Role_CV.pdf`).

### 5. Storage and logging
- Design the upload of each generated PDF (and cover letter, if included) to a Google Drive folder via a free-tier method (service account or Apps Script).
- Design the Google Sheet schema for logging: `company, role, match_score, matched_keywords, cv_variant_link, cover_letter_link, apply_method, status, date_generated, date_applied, follow_up_date`.

### 6. Apply-or-review routing
- If `apply_method == email`: design an automated (but reviewable-before-send, or send-with-delay-and-cancel-window) email dispatch.
- Otherwise: route to a "pending review" status in the Sheet, and design a lightweight notification (e.g. daily digest email via Apps Script) summarizing what's waiting for me to review and manually submit.
- Design the feedback loop: once I mark an application's outcome (rejected, interview, ghosted), the tracker should support follow-up reminders.

## Deliverables expected from the implementation

1. A component diagram or written architecture summary
2. Data schemas for every handoff point (sourcing → ranking → customization → storage)
3. The bullet bank file format and one worked example
4. The matching/scoring algorithm with a concrete example calculation
5. The GitHub Actions workflow file(s)
6. The LaTeX templating script
7. The Apps Script for Drive/Sheet logging and notifications
8. A clear statement of every free-tier limit relied upon and what happens if it's exceeded

## My current context (fill in before running this prompt)

- CV built in LaTeX using moderncv, classic style, blue theme
- Key projects to draw bullets from: [list your verified projects]
- Target roles: [full-stack, backend/distributed systems, AI agents, game dev — adjust as needed]
- Preferred sourcing regions/remote status: [fill in]

---

Build this incrementally — propose the architecture and schemas first, get my sign-off, then implement one component at a time.