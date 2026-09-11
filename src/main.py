from src.sourcing.fetchers.jobicy import JobicyFetcher
from src.sourcing.duplicator import Duplicator
from src.ranking.matcher import Matcher
from src.cv_builder.selector import Selector
from src.cv_builder.renderer import CVRenderer
from src.compiler.tectonic import TectonicCompiler
from src.storage.tracker import ApplicationTracker
from src.routing.router import ApplicationRouter


def run_pipeline(limit: int = 1000):
    fetcher = JobicyFetcher()
    results = fetcher.fetch_jobs(limit=limit)
    
    duplicator = Duplicator()
    new_jobs = duplicator.filter_new(results)
    duplicator.commit(new_jobs)
    
    matcher = Matcher()
    ranked_jobs = []

    print(f"Found {len(new_jobs)} new jobs.")
    print("Matching CV skills and keywords...")
    
    for job in new_jobs:
        res = matcher.score_job(job)
        print(f"\n--- {job.title} @ {job.company} ---")
        print(f"Status: {res['status']} | Score: {res['score']}%")

        if res.get("reason"):
            print(f"Reason: {res['reason']}")
        else:
            res["job_id"] = job.id
            res["title"] = job.title
            res["company"] = job.company
            res["url"] = job.url
            ranked_jobs.append(res)
            print(f"Title Score: {res['title_score']}% | Skills: {res['skills_score']}% | Synergy: {res['synergy_score']}%")
            print(f"Matched Keywords: {res['matched_keywords']}")

    # Sort jobs by match score
    ranked_jobs.sort(key=lambda x: x["score"], reverse=True)
    selector = Selector()
    renderer = CVRenderer()
    compiler = TectonicCompiler()
    tracker = ApplicationTracker()
    router = ApplicationRouter()

    # Generate tailored CV for each qualified job
    qualified_count = 0
    for job in ranked_jobs:
        if job["status"] == "QUALIFIED":
            qualified_count += 1
            print(f"\nGenerating tailored CV for {job['title']} @ {job['company']}...")
            cv_info = selector.select_for_job(job['matched_keywords'])
            safe_name = "".join(c for c in f"{job['company']}_{job['title']}" if c.isalnum() or c in ('_', '-'))[:40]
            tex_file = f"output/{safe_name}_CV.tex"
            
            tex_path = renderer.render(
                candidate=cv_info["candidate"],
                education=cv_info["education"],
                experience=cv_info["experience"],
                projects=cv_info["projects"],
                cp=cv_info["cp"],
                certifications=cv_info["certifications"],
                output_file_path=tex_file,
            )
            print(f"LaTeX rendered to: {tex_path}")

            pdf_path = compiler.compile(tex_path, output_dir="output")
            print(f"PDF compiled to: {pdf_path}")

            # Route application (Email draft or ATS queue) and log to tracker
            routing_info = router.route(job, pdf_path)
            job.update(routing_info)
            job["cv_path"] = pdf_path
            tracker.log_job(job)

    if qualified_count == 0:
        print("\nNo jobs met the QUALIFIED (>=65%) threshold in this batch.")


if __name__ == '__main__':
    run_pipeline(limit=1000)
