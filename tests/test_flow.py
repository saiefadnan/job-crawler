from pathlib import Path
from src.sourcing.models import Job
from src.ranking.matcher import Matcher
from src.cv_builder.selector import Selector
from src.cv_builder.renderer import CVRenderer
from src.compiler.tectonic import TectonicCompiler


def test_full_pipeline_flow():
    # 1. Qualified Job
    job = Job(
        title="Full Stack React & Node Engineer",
        company="Stripe",
        url="https://stripe.com/jobs/1",
        description="Looking for an engineer with React, Node.js, Express, WebSockets, and PostgreSQL.",
        source="test",
        tags=["React", "Node.js", "PostgreSQL"],
    )

    # 2. Ranking
    matcher = Matcher()
    score_result = matcher.score_job(job)
    assert score_result["status"] == "QUALIFIED"
    assert score_result["score"] >= 65.0
    assert "react" in score_result["matched_keywords"]
    assert "node.js" in score_result["matched_keywords"]

    # Seniority Gate Verification
    senior_job = Job(
        title="Senior Lead Full Stack Engineer",
        company="BigCorp",
        url="https://example.com/2",
        description="React and Node.js developer.",
        source="test",
    )
    senior_res = matcher.score_job(senior_job)
    assert senior_res["status"] == "DISCARDED"
    assert "Disqualified by seniority" in senior_res["reason"]

    # Experience Gate Verification (> 1 year)
    exp_job = Job(
        title="Software Engineer",
        company="MidCorp",
        url="https://example.com/3",
        description="React and Node.js developer. Minimum 4+ years of software experience required.",
        source="test",
    )
    exp_res = matcher.score_job(exp_job)
    assert exp_res["status"] == "DISCARDED"
    assert "years of experience" in exp_res["reason"]

    # 3. CV Selection
    selector = Selector()
    cv_data = selector.select_for_job(score_result["matched_keywords"])
    assert len(cv_data["projects"]) > 0
    # Chit-Chat or MediShare should be chosen for React/Node/WebSockets
    project_names = [p["name"] for p in cv_data["projects"]]
    assert "Chit-Chat" in project_names or "MediShare" in project_names

    # 4. LaTeX Rendering
    renderer = CVRenderer()
    tex_path = renderer.render(
        candidate=cv_data["candidate"],
        education=cv_data["education"],
        experience=cv_data["experience"],
        projects=cv_data["projects"],
        cp=cv_data["cp"],
        certifications=cv_data["certifications"],
        output_file_path="output/Stripe_Test_CV.tex",
    )
    assert tex_path.endswith(".tex")

    # 5. Compilation
    compiler = TectonicCompiler()
    pdf_path = compiler.compile(tex_path, output_dir="output")
    assert pdf_path.endswith(".pdf")
    print(f"\n[PASS] End-to-end flow verified! Generated PDF at: {pdf_path}")

    # 6. Routing (ATS queue)
    from src.routing.router import ApplicationRouter
    router = ApplicationRouter(output_dir="output")
    job_dict = {
        "job_id": job.id,
        "company": job.company,
        "title": job.title,
        "score": score_result["score"],
        "status": score_result["status"],
        "url": job.url,
        "matched_keywords": score_result["matched_keywords"],
    }
    routing_info = router.route(job_dict, pdf_path)
    assert routing_info["apply_method"] == "ats"
    assert routing_info["apply_status"] == "ATS_PENDING_REVIEW"
    assert (Path("output/pending_review.md")).exists()

    # 7. Routing (Email draft)
    email_job = {
        "job_id": "email_test_123",
        "company": "TechCorp",
        "title": "Full Stack Dev",
        "score": 85.0,
        "status": "QUALIFIED",
        "url": "mailto:careers@techcorp.io",
        "matched_keywords": ["react", "node.js"],
    }
    email_route_info = router.route(email_job, pdf_path)
    assert email_route_info["apply_method"] == "email"
    assert email_route_info["apply_status"] == "EMAIL_DRAFTED"
    assert email_route_info["email_to"] == "careers@techcorp.io"
    assert "TechCorp" in email_route_info["email_body"]
    assert Path(email_route_info["draft_path"]).exists()

    # 8. Tracking (CSV logging)
    import csv
    from src.storage.tracker import ApplicationTracker
    test_csv = Path("output/test_applications.csv")
    if test_csv.exists():
        test_csv.unlink()
    tracker = ApplicationTracker(csv_path=str(test_csv), webhook_url="")
    job_dict.update(routing_info)
    job_dict["cv_path"] = pdf_path
    tracker.log_job(job_dict)

    email_job.update(email_route_info)
    email_job["cv_path"] = pdf_path
    tracker.log_job(email_job)

    with open(test_csv, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 2
        assert reader[0]["company"] == "Stripe"
        assert reader[0]["apply_method"] == "ats"
        assert reader[1]["company"] == "TechCorp"
        assert reader[1]["apply_method"] == "email"
        assert reader[1]["email_to"] == "careers@techcorp.io"
        assert "TechCorp" in reader[1]["email_body"]
        assert reader[1]["draft_path"] != ""

    # Clean up test files created by test_full_pipeline_flow
    for ext in ("aux", "log", "out", "pdf", "tex"):
        p = Path(f"output/Stripe_Test_CV.{ext}")
        if p.exists():
            p.unlink()
    if test_csv.exists():
        test_csv.unlink()
    if Path(email_route_info["draft_path"]).exists():
        Path(email_route_info["draft_path"]).unlink()

    # Reset pending_review.md to clean header
    review_path = Path("output/pending_review.md")
    if review_path.exists():
        with open(review_path, "w", encoding="utf-8") as f:
            f.write("# Pending ATS Applications Review Queue\n\n| Company | Role | Match Score | Apply Link | Tailored CV PDF |\n| :--- | :--- | :---: | :--- | :--- |\n")

    print("\n[PASS] Routing and CSV tracking verified successfully!")


def test_duplicator_cache():
    import json
    from datetime import datetime, timedelta
    from src.sourcing.duplicator import Duplicator

    cache_path = Path("output/test_cache.json")
    if cache_path.exists():
        cache_path.unlink()

    # Pre-populate cache with an active job and an expired job (35 days old)
    today_str = datetime.now().strftime("%Y-%m-%d")
    old_date = (datetime.now() - timedelta(days=35)).strftime("%Y-%m-%d")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "version": "2.0",
                "ttl_days": 30,
                "total_active": 2,
                "entries": {
                    "active_job_hash": today_str,
                    "old_job_hash": old_date,
                },
            },
            f,
        )

    duplicator = Duplicator(cache_file=str(cache_path), ttl_days=30)
    assert "active_job_hash" in duplicator.cache
    assert "old_job_hash" in duplicator.cache

    # Job list to filter
    j1 = Job(title="J1", company="C1", url="http://1", description="desc", source="test")
    j1.id = "active_job_hash"
    j2 = Job(title="J2", company="C2", url="http://2", description="desc", source="test")
    j2.id = "brand_new_job_hash"

    filtered = duplicator.filter_new([j1, j2])
    assert len(filtered) == 1
    assert filtered[0].id == "brand_new_job_hash"

    # Commit should prune old_job_hash and add brand_new_job_hash
    duplicator.commit(filtered)

    # Verify on disk
    with open(cache_path, "r", encoding="utf-8") as f:
        saved_data = json.loads(f.read())
    assert saved_data["version"] == "2.0"
    assert "brand_new_job_hash" in saved_data["entries"]
    assert "active_job_hash" in saved_data["entries"]
    assert "old_job_hash" not in saved_data["entries"]  # Pruned!
    assert saved_data["total_active"] == 2

    if cache_path.exists():
        cache_path.unlink()


def test_storage_30_day_cleanup():
    import os
    import csv
    import time
    from datetime import datetime, timedelta
    from src.storage.tracker import ApplicationTracker

    test_csv = Path("output/test_cleanup_apps.csv")
    if test_csv.exists():
        test_csv.unlink()

    tracker = ApplicationTracker(csv_path=str(test_csv), webhook_url="")

    today_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    old_date = (datetime.now() - timedelta(days=35)).strftime("%Y-%m-%d %H:%M:%S")

    tracker.log_job({"company": "FreshCorp", "title": "Dev", "date": today_str, "status": "QUALIFIED"})
    tracker.log_job({"company": "OldCorp", "title": "Dev", "date": old_date, "status": "QUALIFIED"})

    with open(test_csv, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2

    # Prune CSV records older than 30 days
    purged_csv = tracker.prune_local_records(ttl_days=30)
    assert purged_csv == 1

    with open(test_csv, "r", encoding="utf-8") as f:
        remaining_rows = list(csv.DictReader(f))
    assert len(remaining_rows) == 1
    assert remaining_rows[0]["company"] == "FreshCorp"

    # Test file pruning
    test_dir = Path("output/test_cleanup_files")
    test_dir.mkdir(parents=True, exist_ok=True)
    fresh_file = test_dir / "fresh.pdf"
    old_file = test_dir / "old.pdf"
    fresh_file.write_text("fresh")
    old_file.write_text("old")

    # Set old_file modification time to 35 days ago
    past_time = time.time() - (35 * 86400)
    os.utime(str(old_file), (past_time, past_time))

    purged_files = tracker.prune_local_files(output_dir=str(test_dir), ttl_days=30)
    assert purged_files == 1
    assert fresh_file.exists()
    assert not old_file.exists()

    # Clean up test artifacts
    if fresh_file.exists():
        fresh_file.unlink()
    if test_dir.exists():
        test_dir.rmdir()
    if test_csv.exists():
        test_csv.unlink()


def test_location_and_remote_gate():
    matcher = Matcher()

    # 1. International On-site Job -> MUST BE DISCARDED
    onsite_intl_job = Job(
        title="Junior Software Engineer",
        company="GermanCo",
        url="https://example.com/job1",
        description="Looking for React and Node.js developer in our Karlsruhe office.",
        source="arbeitnow",
        country="Karlsruhe, Germany",
        remote_option="On-site",
        tags=["React", "Node.js"],
    )
    res_intl = matcher.score_job(onsite_intl_job)
    assert res_intl["status"] == "DISCARDED"
    assert "remote required" in res_intl["reason"].lower() or "on-site" in res_intl["reason"].lower()

    # 2. Dhaka / Bangladesh Local Job (even if On-site/Hybrid) -> ALLOWED & BOOSTED
    dhaka_job = Job(
        title="Junior Software Engineer",
        company="DhakaTech",
        url="https://example.com/job2",
        description="React and Node.js developer in Dhaka office.",
        source="linkedin_bd",
        country="Dhaka, Bangladesh",
        remote_option="On-site",
        tags=["React", "Node.js"],
    )
    res_dhaka = matcher.score_job(dhaka_job)
    assert res_dhaka["status"] == "QUALIFIED"
    assert res_dhaka["is_local"] is True
    # Local boost (+15%) applied
    assert res_dhaka["score"] > 70.0

    # 3. International Worldwide Remote Job -> ALLOWED (not discarded by location)
    remote_job = Job(
        title="Junior Software Engineer",
        company="RemoteCo",
        url="https://example.com/job3",
        description="React and Node.js developer. 100% remote anywhere in the world.",
        source="weworkremotely",
        country="Anywhere in the World",
        remote_option="Remote",
        tags=["React", "Node.js"],
    )
    res_remote = matcher.score_job(remote_job)
    assert res_remote["status"] in ("QUALIFIED", "SKIPPED_LOW_SCORE")
    assert res_remote["is_local"] is False


def test_delete_local_cv_artifacts():
    from src.storage.tracker import ApplicationTracker
    Path("output").mkdir(parents=True, exist_ok=True)
    
    # 1. Create dummy compilation files
    test_files = [
        Path("output/test_cleanup_CV.pdf"),
        Path("output/test_cleanup_CV.tex"),
        Path("output/test_cleanup_CV.aux"),
        Path("output/test_cleanup_CV.log"),
    ]
    for f in test_files:
        f.write_text("dummy test content", encoding="utf-8")
        assert f.exists()

    # 2. Trigger deletion
    ApplicationTracker.delete_local_cv_artifacts(
        cv_path="output/test_cleanup_CV.pdf",
        tex_path="output/test_cleanup_CV.tex"
    )

    # 3. Verify all artifacts deleted
    for f in test_files:
        assert not f.exists()

    # 4. Verify review link update in pending_review.md
    digest_path = Path("output/test_pending_review.md")
    digest_path.write_text("| **Acme** | Dev | 80% | [Link](url) | `output/test_cleanup_CV.pdf` |\n", encoding="utf-8")
    ApplicationTracker._update_pending_review_link(
        old_cv_path="output/test_cleanup_CV.pdf",
        drive_link="https://drive.google.com/file/d/test12345/view",
        digest_path=str(digest_path)
    )
    content = digest_path.read_text(encoding="utf-8")
    assert "[Drive PDF](https://drive.google.com/file/d/test12345/view)" in content
    assert "`output/test_cleanup_CV.pdf`" not in content

    if digest_path.exists():
        digest_path.unlink()


def test_clear_cache_utility():
    import json
    import csv
    from scripts.clear_cache import clear_cache, clear_applications_log
    test_cache = "output/test_clear_cache.json"
    test_csv = "output/test_clear_app.csv"
    
    # 1. Clear cache
    assert clear_cache(test_cache) is True
    with open(test_cache, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["entries"] == {}
        assert data["total_active"] == 0

    # 2. Clear CSV log
    assert clear_applications_log(test_csv) is True
    with open(test_csv, "r", encoding="utf-8") as f:
        rows = list(csv.reader(f))
        assert len(rows) == 1
        assert rows[0][0] == "date"
        assert rows[0][1] == "job_id"

    # Cleanup
    for path in (test_cache, test_csv):
        p = Path(path)
        if p.exists():
            p.unlink()


if __name__ == "__main__":
    test_full_pipeline_flow()
    test_duplicator_cache()
    test_storage_30_day_cleanup()
    test_location_and_remote_gate()
    test_delete_local_cv_artifacts()
    test_clear_cache_utility()
