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
    test_csv = "output/test_applications.csv"
    tracker = ApplicationTracker(csv_path=test_csv)
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

    print("\n[PASS] Routing and CSV tracking verified successfully!")


if __name__ == "__main__":
    test_full_pipeline_flow()
