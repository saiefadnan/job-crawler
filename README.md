# Autonomous Job Search Pipeline & Tailored CV Engine

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![LaTeX: Tectonic](https://img.shields.io/badge/latex-tectonic-orange.svg)](https://tectonic-typesetting.github.io/)
[![CI/CD: GitHub Actions](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-2088FF.svg)](https://github.com/features/actions)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Zero Fabrication](https://img.shields.io/badge/CV-Zero%20Fabrication-success.svg)](#core-principles)

An end-to-end, zero-cost, autonomous job search and application pipeline. It ingests 550+ fresh developer postings daily from public APIs, filters and deduplicates them using rolling TTL caching, scores them against custom seniority gates (junior/entry-level/max 1 year experience), selects truthful project bullets from an immutable bank, compiles strictly **1-page ModernCV LaTeX PDFs**, logs data in real time to Google Sheets via webhooks, and routes applications to Gmail drafts or an ATS review queue.

---

## Architecture

![Pipeline Architecture](architecture/refined_architecture.png)

### The 7-Stage Pipeline

1. **Multi-Source Ingestion**: Ingests fresh postings from free, unauthenticated developer APIs (Jobicy, RemoteOK, Arbeitnow) without brittle web scraping.
2. **Deduplication Engine**: Hashes postings with SHA-256 and maintains a self-cleaning **30-day rolling TTL cache** (`data/processed_cache.json`) to prevent bloat while allowing natural re-evaluations of re-posted jobs.
3. **Match & Rank Engine**: Evaluates job descriptions with multi-tier scoring (Title, Skills, Synergy, Junior Bonus) and enforces strict **Seniority & Experience Gating** (hard-rejects senior/lead/staff roles and positions demanding $> 1$ year of experience).
4. **Tailored CV Builder**: Uses an immutable bullet bank (`data/bullet_bank.yaml`) to match and select the candidate's genuine projects and skills. **Zero LLM hallucinations or fabricated credentials.**
5. **LaTeX PDF Compiler**: Renders a clean ModernCV template and compiles it into a pixel-perfect, strict 1-page PDF using the high-performance **Tectonic** engine.
6. **Real-Time Cloud Sync**: Records all evaluations into `data/applications.csv` and dispatches live webhooks to a Google Apps Script endpoint linked to a Google Sheet.
7. **Dual Routing**:
   - **Email Applications**: Generates customized pitch drafts saved locally and synced into Gmail ready for 1-click review and send.
   - **ATS Applications**: Appends direct application URLs and matched CV paths to `output/pending_review.md` for manual submission.

---

## Project Structure

```text
job-search/
├── architecture/
│   └── refined_architecture.png     # High-contrast pipeline architecture diagram
├── data/
│   ├── profile.yaml                 # SINGLE SOURCE OF TRUTH: User profile, targets, skills, weights
│   ├── bullet_bank.yaml             # Immutable verified projects, experience, and education
│   ├── applications.csv             # Local tracking database of all processed jobs
│   └── processed_cache.json         # 30-day self-cleaning rolling TTL deduplication cache
├── src/
│   ├── sourcing/
│   │   ├── models.py                # Pydantic Job model with auto SHA-256 & email detection
│   │   ├── duplicator.py            # Deduplication manager with auto 30-day TTL pruning
│   │   └── fetchers/                # Modular API fetchers (Jobicy, RemoteOK, Arbeitnow)
│   ├── ranking/
│   │   └── matcher.py               # Multi-tier matcher with seniority & experience gates
│   ├── cv_builder/
│   │   ├── selector.py              # Relevant bullet & project selector
│   │   ├── latex_escaper.py         # Jinja2 LaTeX escaping utilities
│   │   └── renderer.py              # ModernCV Jinja2 template renderer
│   ├── compiler/
│   │   └── tectonic.py              # Automated Tectonic CLI / pdflatex compiler
│   ├── storage/
│   │   └── tracker.py               # Local CSV logging + live Google Apps Script webhook sync
│   ├── routing/
│   │   └── router.py                # Dual router: email draft creator + ATS review markdown
│   └── main.py                      # Pipeline orchestrator
├── templates/
│   └── moderncv_classic_blue.tex.j2 # Strict 1-page ModernCV template
├── scripts/
│   └── gmail_draft_sync.gs          # Google Apps Script for Sheet webhook, Drive links & Gmail drafts
├── tests/
│   └── test_flow.py                 # Full integration test suite & cache tests
├── .github/workflows/
│   └── job_pipeline.yml             # Scheduled daily GitHub Actions workflow (09:00 UTC)
├── requirements.txt
└── .env.example
```

---

## Full Setup Guide

Follow these steps to configure the pipeline for your own background and target roles.

### 1. Prerequisites

- **Python 3.10+** (Python 3.11 or 3.13 recommended)
- **Git**
- **LaTeX Compiler**: [Tectonic](https://tectonic-typesetting.github.io/) is recommended because it automatically downloads missing LaTeX packages on the fly.
  - **Windows**:
    ```powershell
    # Via winget
    winget install Tectonic.Tectonic
    # Or via cargo
    cargo install tectonic
    ```
    *Alternatively, install [MikTeX](https://miktex.org/) and ensure `pdflatex` is in your PATH.*
  - **macOS**:
    ```bash
    brew install tectonic
    ```
  - **Linux (Ubuntu/Debian)**:
    ```bash
    curl --proto '=https' --tlsv1.2 -fsSL https://drop-sh.fullyjustified.net | sh
    sudo mv tectonic /usr/local/bin/
    ```

---

### 2. Clone and Install Dependencies

```bash
git clone https://github.com/saiefadnan/job-crawler.git
cd job-crawler

# Create and activate a virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

### 3. Customize Your Profile (`data/profile.yaml`)

**This file is the single configuration hub.** You do not need to modify any Python code to adapt this system to yourself.

Open `data/profile.yaml` and update the following sections:

```yaml
candidate:
  name: "Your Full Name"
  title: "Software Engineer"
  email: "your.email@example.com"
  phone: "+1 555-0199"
  location: "Your City, Country"
  linkedin: "https://linkedin.com/in/yourprofile"
  github: "https://github.com/yourusername"
  portfolio: "https://yourportfolio.com"

# Roles to search and match
target_roles:
  - "Software Engineer"
  - "Frontend Engineer"
  - "Full Stack Engineer"
  - "Junior Developer"

# Seniority and Experience Filter
experience_filter:
  max_years: 1 # Maximum years of experience required (hard rejects anything above)
  target_seniority: # Boosts score by +15% if found
    - "junior"
    - "entry"
    - "associate"
    - "fresh graduate"
    - "intern"
  disallowed_seniority: # Hard rejects jobs containing these terms
    - "senior"
    - "sr."
    - "lead"
    - "principal"
    - "staff"
    - "architect"

# Skills and weights
skills:
  primary:
    - "react"
    - "node.js"
    - "typescript"
    - "python"
  secondary:
    - "docker"
    - "postgresql"
    - "mongodb"

weights:
  title: 0.35
  skills: 0.40
  synergy: 0.15
  junior_bonus: 0.15
  threshold: 65.0 # Minimum score (%) required to generate a tailored CV
```

---

### 4. Provide Your Authentic Experiences (`data/bullet_bank.yaml`)

Edit `data/bullet_bank.yaml` with your genuine education, work history, and portfolio projects.

Each project should include:
- `name`: Project title
- `technologies`: List of tools and languages
- `keywords`: Normalized tags (e.g. `react`, `node.js`, `websockets`, `postgresql`) used by the selector to pick the top matching projects
- `bullets`: Exact descriptions of what you built and achieved

> **Note**: The pipeline selects your best-fitting projects based on job keywords and renders them into the ModernCV template. It will **never** fabricate projects, metrics, or technologies not present in this bank.

---

### 5. Setup Google Sheets, Google Drive & Gmail Cloud Sync

The pipeline features a zero-cost cloud sync mechanism connecting Python with your personal Google Drive, Google Sheets, and Gmail using a lightweight Google Apps Script endpoint.

#### How It Works:
- **Automatic Google Drive Upload (Local or Cloud)**: When running either locally or in headless CI (GitHub Actions), Python base64-encodes each compiled 1-page CV PDF and transmits it via the webhook. The script automatically creates/finds a `Job_CVs` folder in your Google Drive, saves the PDF, sets shareable view permissions, and records the `drive_link` in your Google Sheet.
- **Automated Gmail Draft Generation**: For qualified jobs accepting email applications (`apply_method == 'email'`), the script automatically calls `GmailApp.createDraft()`. It creates a ready-to-send draft in your Gmail account with the customized cover pitch, candidate signature, and the tailored CV PDF attached.

#### Step-by-Step Setup:
1. Create a new [Google Sheet](https://sheets.new).
2. Click **Extensions > Apps Script**.
3. Delete any boilerplate code and paste the entire contents of [`scripts/gmail_draft_sync.gs`](scripts/gmail_draft_sync.gs).
4. Click **Deploy > New deployment**:
   - Select type: **Web app**
   - Description: `Job Tracker Webhook`
   - Execute as: **Me**
   - Who has access: **Anyone** *(Required so Python on your PC or GitHub Actions can post without OAuth prompt)*
5. Click **Deploy**, authorize permissions with your Google account, and copy the provided **Web App URL** (`https://script.google.com/macros/s/.../exec`).
6. Set your local `.env` file:
   ```bash
   cp .env.example .env
   ```
7. Open `.env` and paste your URL:
   ```env
   GOOGLE_SHEET_WEBHOOK_URL="https://script.google.com/macros/s/YOUR_DEPLOYMENT_ID/exec"
   ```

*(If left blank, the pipeline runs in offline mode, logging exclusively to local `data/applications.csv` and saving PDFs in `output/tailored_cvs/`.)*

---

### 6. Run the Pipeline Locally

Run the pipeline from your terminal:

```bash
python -m src.main
```

When execution completes, check the generated artifacts:
- **`output/tailored_cvs/`**: Tailored 1-page ModernCV PDF for each qualified match.
- **`output/email_drafts/`**: Personalized email pitch files for email-based applications.
- **`output/pending_review.md`**: Markdown digest with 1-click apply links for ATS systems (Greenhouse, Lever, LinkedIn).
- **`data/applications.csv`**: Local tracking log of every job evaluated, its score, reason, and status.
- **`data/processed_cache.json`**: Updated 30-day rolling deduplication cache.
- **Google Sheet & Gmail**: If configured, new rows appear instantly in your Sheet with Drive links, and email drafts appear in your Gmail Drafts folder.

---

### 7. Automated Daily Runs via GitHub Actions (Cloud Execution)

You do **not** need to keep your computer running. The repository includes a GitHub Actions workflow (`.github/workflows/job_pipeline.yml`) configured to run daily at 09:00 UTC (or manually triggered via 1-click `workflow_dispatch`).

#### How Google Drive Saves CVs When Not Running Locally:
1. **Remote PDF Compilation**: On the headless GitHub Actions runner (Ubuntu), Tectonic compiles each tailored 1-page ModernCV.
2. **Direct Cloud Transmission**: `ApplicationTracker` reads the compiled PDF bytes, encodes them in base64, and POSTs them inside the JSON payload to your Google Apps Script webhook.
3. **Google Drive Storage**: Google Apps Script receives the payload, saves the file directly into your personal Google Drive (`Job_CVs`), and generates a public view link (`drive_link`).
4. **Gmail Draft with Attachment**: If the role accepts email applications, Google Apps Script attaches the PDF directly to a draft in your Gmail inbox.
5. **Workflow Artifact Archive**: In addition, GitHub Actions archives all generated PDFs as a downloadable zip artifact (`tailored-cvs-<run_id>`) under the **Actions** tab (retained for 14 days).

#### Enabling GitHub Actions:
1. Push your repository to GitHub (public or private).
2. Navigate to **Settings > Secrets and variables > Actions**.
3. Click **New repository secret**:
   - **Name**: `GOOGLE_SHEET_WEBHOOK_URL`
   - **Value**: Your Google Apps Script Web App URL
4. Under the **Actions** tab, click **Daily Automated Job Search Pipeline** > **Run workflow** to test execution.

---

### 8. Handling Applications: Your Daily Workflow

Once the pipeline runs (either locally or on schedule in GitHub Actions):

#### Branch A: Email Applications (Gmail Drafts)
1. Open your regular Gmail (web or mobile).
2. Go to your **Drafts** folder.
3. You will see pre-populated drafts addressed to recruiter emails with:
   - Customized subject line: `Application: [Job Title] - [Your Name]`
   - Tailored pitch highlighting your matching skills and authentic projects.
   - Your compiled 1-page ModernCV PDF attached.
   - Clickable Google Drive fallback link in the body.
4. Review the draft (10 seconds), make any personal tweaks, and hit **Send**.

#### Branch B: ATS Applications (1-Click Queue)
1. Open `output/pending_review.md` (or your Google Sheet).
2. Each qualified role includes:
   - Company & Job Title
   - Direct Apply URL (Greenhouse, Lever, Workday, LinkedIn)
   - Path to your tailored 1-page CV PDF (or clickable Google Drive link)
3. Click the application link, upload your tailored CV, and submit.


---

## Running Tests

Run the full suite of integration tests (verifying seniority gates, CV compilation, routing, and cache TTL):

```bash
pytest tests/ -v
```

---

## Core Principles

- **Zero Fabrication**: No LLMs generating fake accomplishments. The CV builder only uses verified facts from `data/bullet_bank.yaml`.
- **Zero Cost**: Built entirely on free public APIs, open-source LaTeX tools, Google Apps Script, and free GitHub Actions tiers.
- **Zero ATS Auto-Submit**: Respects company application rules. Web/ATS jobs are staged in `output/pending_review.md` for 1-click human review and manual submission.
- **Seniority Protected**: Protects early-career candidates from wasting time on Senior/Staff roles while optimizing matching for Junior and Entry-level positions.

---

## License

This project is licensed under the MIT License.
