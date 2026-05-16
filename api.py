import asyncio
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from schemas import QueueItem, SearchTask, AgentAnalysisResult, Product
from scraper import scrape_amazon_top_3
from agent import evaluate_products

app = FastAPI(title="Shopping Agent v2 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

tasks_db: dict[str, QueueItem] = {}
queue = asyncio.Queue()

@app.post("/tasks", response_model=QueueItem)
async def create_task(task: SearchTask):
    task_id = str(uuid.uuid4())
    item = QueueItem(id=task_id, task=task, status="queued")
    tasks_db[task_id] = item
    await queue.put(task_id)
    return item

@app.get("/tasks/{task_id}", response_model=QueueItem)
async def get_task(task_id: str):
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks_db[task_id]

async def process_queue():
    while True:
        task_id = await queue.get()
        item = tasks_db[task_id]
        try:
            item.status = "searching"
            print(f"Processing task {task_id}: {item.task.query}")
            
            # Step 1: Scrape
            products, all_candidates, filtered_items = await scrape_amazon_top_3(item.task.query)
            item.products = products
            
            if not products:
                item.status = "error"
                item.error_message = "No organic products found."
                continue
                
            item.status = "analyzing"
            
            # Step 2: Evaluate via LLM (sync call pushed to thread)
            analysis = await asyncio.to_thread(evaluate_products, item.task, products)
            item.analysis = analysis
            item.status = "complete"
            
            # Step 3: Write Agent Trace File
            import os
            os.makedirs("traces", exist_ok=True)
            trace_path = f"traces/trace_{task_id}.md"
            with open(trace_path, "w") as f:
                f.write(f"# Agent Trace: {item.task.query}\n\n")
                f.write(f"**Task ID:** `{task_id}`  \n")
                f.write(f"**Status:** Complete\n\n")
                
                f.write("## 1. Top 10 Organic Candidates Found\n")
                f.write("| Rank | ASIN | Reviews | Rating | Title |\n")
                f.write("| :--- | :--- | :--- | :--- | :--- |\n")
                # all_candidates are already sorted by scraper
                for i, p in enumerate(all_candidates[:10], 1):
                    f.write(f"| {i} | `{p.id}` | {p.reviews_count} | {p.rating} | {p.title[:60]}... |\n")
                
                if filtered_items:
                    f.write("\n## 2. Filtered Products (Sponsored/AD)\n")
                    f.write("| ASIN | Reviews | Reason | Title |\n")
                    f.write("| :--- | :--- | :--- | :--- |\n")
                    for p in filtered_items:
                        f.write(f"| `{p['id']}` | {p['reviews']} | {p['reason']} | {p['title'][:60]}... |\n")

                f.write("\n## 3. Top 3 Candidates Selected for Deep Analysis\n")
                for p in products:
                    f.write(f"- **{p.title[:60]}...** (`{p.id}`): {p.reviews_count} reviews, {p.rating} stars\n")
                
                f.write("\n## 4. Agentic Intelligence & Self-Checks\n")
                f.write(f"**Primary Reasoning Type:** `{analysis.reasoning_type.upper()}`\n")
                f.write(f"**Self-Verification Log:**\n> {analysis.self_verification_log}\n\n")
                f.write(f"**Fallback Strategy Applied:** `{'Yes' if analysis.fallback_applied else 'No'}`\n\n")

                f.write("## 5. Detailed Product Analysis Scorecards\n")
                for ap in analysis.products:
                    p_meta = next((p for p in products if p.id == ap.product_id), None)
                    name = p_meta.title[:60] if p_meta else ap.product_id
                    f.write(f"### {'🏆 ' if ap.is_top_recommendation else ''}{name}\n")
                    f.write("| Criterion | Score | Reasoning Type | Analysis |\n")
                    f.write("| :--- | :--- | :--- | :--- |\n")
                    for crit, eval in ap.evaluations.items():
                        check = "✅" if eval.internal_check_passed else "❌"
                        f.write(f"| {crit} | **{eval.score.upper()}** | `{eval.reasoning_type}` | {eval.analysis} (Check: {check}) |\n")
                    f.write("\n")

                f.write("\n## 6. Final Recommendation Summary\n")
                f.write(f"{analysis.overall_agent_summary}\n")
            
            print(f"Completed task {task_id}. Trace saved to {trace_path}")
            
        except Exception as e:
            item.status = "error"
            item.error_message = str(e)
            print(f"Error on task {task_id}: {e}")
        finally:
            queue.task_done()

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(process_queue())
