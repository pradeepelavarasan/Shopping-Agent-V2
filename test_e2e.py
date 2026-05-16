import httpx
import time
import json
import sys

API_URL = "http://127.0.0.1:8000"

def test_shopping_agent(query):
    print(f"--- Starting End-to-End Test for: '{query}' ---")
    
    # 1. Create Task
    payload = {
        "query": query,
        "priorities": ["Customer Sentiment", "Reliability", "Value for Money", "Feature Completeness", "Build Quality"]
    }
    
    try:
        response = httpx.post(f"{API_URL}/tasks", json=payload, timeout=30)
        response.raise_for_status()
        task = response.json()
        task_id = task["id"]
        print(f"Task Created. ID: {task_id}")
    except Exception as e:
        print(f"Failed to create task: {e}")
        return

    # 2. Poll for Completion
    print("Polling for task completion (this may take 30-60 seconds)...")
    while True:
        try:
            status_res = httpx.get(f"{API_URL}/tasks/{task_id}", timeout=30)
            status_res.raise_for_status()
            data = status_res.json()
            status = data["status"]
            
            if status == "complete":
                print("\n✅ Task Complete!")
                print("\n--- RESULTS ---")
                print(f"Overall Summary: {data['analysis']['overall_agent_summary']}")
                print("\nProduct Evaluations:")
                for p_analysis in data["analysis"]["products"]:
                    p_id = p_analysis["product_id"]
                    print(f"\n[Product: {p_id}]")
                    for crit, eval_data in p_analysis["evaluations"].items():
                        score = eval_data["score"]
                        status_icon = "🟢" if score == "positive" else "🔴" if score == "negative" else "🟡"
                        print(f"  {status_icon} {crit}: {eval_data['analysis']}")
                break
            elif status == "error":
                print(f"\n❌ Task failed with error: {data['error_message']}")
                break
            else:
                sys.stdout.write(f"  Current Status: {status}...   \r")
                sys.stdout.flush()
                time.sleep(3)
        except Exception as e:
            print(f"\nError polling status: {e}")
            break

if __name__ == "__main__":
    test_query = sys.argv[1] if len(sys.argv) > 1 else "badminton racquet"
    test_shopping_agent(test_query)
