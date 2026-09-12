# Refined Pipeline Architecture

This document formalizes the refined zero-cost job pipeline architecture based on the reviewed design.

![Refined Architecture](../architecture/refined_architecture.png)

---

## 1. Pipeline Flowchart (Mermaid)

```mermaid
flowchart TD
    subgraph Sourcing ["1. Sourcing Layer (Multi-Source Ingestion)"]
        Cron["GitHub Actions Cron\n(Daily @ 7:00 AM BST / 01:00 UTC)"] --> Fetchers
        Fetchers["Job Fetchers:\n- LinkedIn BD (Dhaka, Bangladesh)\n- We Work Remotely (Worldwide Remote)\n- Jobicy (Remote Tech)\n- RemoteOK (Remote Developers)\n- Arbeitnow (Remote Filtered)"]
        Fetchers --> Dedupe{"Deduplication Engine\n(SHA-256 Hash + 30-Day TTL)"}
        Dedupe -- "Already in cache" --> SkipSeen["Drop (Already Processed)"]
        Dedupe -- "New Job" --> NewJobs["Raw Normalized Job Feed"]
    end

    subgraph Ranking ["2. Matching, Strict Gating & Prioritization"]
        NewJobs --> NegativeGate{"Gate 1: Negative Keywords\n(Security clearance, US citizen only, unpaid)"}
        NegativeGate -- "Hit" --> DiscardNeg["Discard (Negative Keyword)"]
        NegativeGate -- "Pass" --> SeniorityGate{"Gate 2: Seniority Level\n(Senior, Lead, Principal, Manager, Director)"}
        
        SeniorityGate -- "Hit Senior" --> DiscardSen["Discard (Senior Role)"]
        SeniorityGate -- "Pass" --> ExpGate{"Gate 3: Experience Level\n(Demands > 1 Year Experience)"}
        
        ExpGate -- "Demands > 1 Yr" --> DiscardExp["Discard (>1 Year Required)"]
        ExpGate -- "Pass (0-1 Yr)" --> LocGate{"Gate 4: Location & Remote Gate\n(Intl Must Be Remote | Dhaka BD Allowed)"}
        
        LocGate -- "Intl On-Site" --> DiscardLoc["Discard (Intl On-Site)"]
        LocGate -- "Eligible" --> Scorer["Match Engine\n(0.35 Title + 0.50 Skills + 0.15 Synergy)\n+ Dhaka BD Local Boost (+15%)"]
        
        Scorer --> ScoreThreshold{"Score >= 65%?"}
        ScoreThreshold -- "Score < 40%" --> DiscardScore["Discard (Low Match)"]
        ScoreThreshold -- "40% <= Score < 65%" --> LogSkipped["Log to Sheet: SKIPPED_LOW_SCORE"]
        ScoreThreshold -- "Score >= 65%" --> PrioritySort["Priority Queue\n(1. Dhaka/BD Local First, 2. Highest Match Score)"]
    end

    subgraph Customization ["3. Verified CV Customization"]
        PrioritySort --> Selector["Bullet Selector & Optimizer\n(Knapsack Match from Bullet Bank)"]
        BulletBank["data/bullet_bank.yaml\n(Immutable Verified Projects & Skills)"] --> Selector
        Selector --> JinjaRenderer["LaTeX Jinja2 Renderer\n(ModernCV Classic Blue - 1 Page Strict)"]
        JinjaRenderer --> SanitizedTex["Company_Role_CV.tex"]
    end

    subgraph Compilation ["4. Zero-Cost Compilation"]
        SanitizedTex --> Tectonic["Tectonic LaTeX Engine\n(Compiled in GitHub Actions / Local Runner)"]
        Tectonic --> OutputPDF["Company_Role_CV.pdf"]
    end

    subgraph Storage ["5. Cloud Storage & Sync"]
        OutputPDF --> B64Encoder["Base64 PDF Encoder"]
        B64Encoder --> AppsScriptWebhook["Google Apps Script Webhook"]
        AppsScriptWebhook --> GDrive["Google Drive\n(Folder: Job_CVs / Shareable Link)"]
        AppsScriptWebhook --> GSheet["Google Sheet Tracker\n(Appends Row with drive_link)"]
        AppsScriptWebhook --> GmailDraft["Gmail Drafts\n(Email applications pre-attached with PDF)"]
    end

    subgraph Routing ["6. Human Review & Decision Point"]
        GSheet --> ReviewInbox{"Review Queue in Sheet / pending_review.md"}
        ReviewInbox -- "apply_method == 'email'" --> EmailQueue["Gmail Draft Ready\n(1-Click Review & Send)"]
        ReviewInbox -- "apply_method == 'ats'" --> ATSQueue["Manual ATS Queue\n(Click Apply Link + Upload Drive PDF)"]
    end

    subgraph Maintenance ["7. Unified 30-Day Rolling Maintenance"]
        DailyCron["Daily Maintenance Trigger"] --> CleanupEngine["Unified 30-Day Pruner"]
        CleanupEngine --> PruneCache["Prune processed_cache.json (TTL > 30d)"]
        CleanupEngine --> PruneLocal["Prune output/ PDFs & TeX files (TTL > 30d)"]
        CleanupEngine --> PruneCloud["Prune Google Drive files, Sheet rows & old drafts (TTL > 30d)"]
    end
```

---

## 2. Google Sheet State Machine & Lifecycle

The Google Sheet acts as both the **central inbox** and the **long-term tracker**:

| Status | Trigger | Meaning | Next Action Required |
|---|---|---|---|
| `SKIPPED_LOW_SCORE` | Match score $40\% - 64\%$ | Logged for auditing and visibility. | No action required. |
| `DISCARDED` | Match score $<40\%$ or negative filter hit | Ignored. | No action required. |
| `PENDING_REVIEW` | Score $\ge 65\%$ and ATS / Web portal | Ready for manual submission. | Click Job URL, upload the Drive PDF, submit form, change status to `APPLIED`. |
| `EMAIL_QUEUED` | Score $\ge 65\%$ and plain company email | Ready for email application. | Review generated email draft & CV attachment, send, change status to `APPLIED`. |
| `APPLIED` | Manually marked after applying | Application has been submitted. | Triggers the 7-day follow-up reminder clock. |
| `FOLLOW_UP_DUE` | `Date Applied + 7 days <= Today` | No response after 1 week. | Apps Script flags row in morning digest to send a polite follow-up. |
| `INTERVIEW` | Recruiter reaches out | Progressing in interview rounds. | Log interview stages and notes. |
| `REJECTED` | Rejection received | Outcome logged. | Closes loop. |
| `GHOSTED` | 30+ days without response | Archived. | Closes loop. |

---

## 3. Key Architectural Boundaries

1. **Deduplication Boundary**:
   - Computes `SHA256(source + ":" + company + ":" + title + ":" + url)`.
   - Checks against `data/processed_cache.json`.
   - Never makes unnecessary scoring or compilation calls on repeated daily runs.
2. **Immutability Boundary**:
   - `data/bullet_bank.yaml` is the single source of truth.
   - Built-in assertion checks verify that every bullet in the rendered CV exists verbatim in the verified bullet bank.
3. **ATS Protection Boundary**:
   - Zero scraping or automated form submissions against Workday, Greenhouse, Lever, or LinkedIn Easy Apply.
   - Always provides direct job links and ready-made PDFs for 1-click human submission.
4. **Free-Tier Limits Boundary**:
   - Tectonic compiles in GitHub Actions runners (0 local dependencies, 0 paid licenses).
   - Apps Script manages Drive and Sheet storage with a single daily morning digest email (conserving email quotas).

---

## 4. Ranking & Scoring Formula Summary

For detailed mathematics and a worked calculation, see [docs/ranking_formula.md](file:///e:/my_projects/job-search/docs/ranking_formula.md).

$$\text{Final Score } S = 100 \times \left( 0.35 \cdot M_{\text{title}} + 0.50 \cdot M_{\text{skills}} + 0.15 \cdot M_{\text{synergy}} \right)$$

- **Hard Gate**: If any negative keyword matches $\rightarrow \text{DISCARDED} (S = 0\%)$.
- **Thresholds**:
  - $S < 40\%$: `DISCARDED` (Dropped from pipeline).
  - $40\% \le S < 65\%$: `SKIPPED_LOW_SCORE` (Logged in Sheet, no CV built).
  - $S \ge 65\%$: `QUALIFIED` (Proceeds to Stage 3: CV Customization).

