# Shopping Agent v2: Advanced Agentic Product Researcher

Shopping Agent v2 is a high-performance browser extension and backend system designed to automate the deep research required for online shopping. It uses a multi-agent orchestration pipeline to scrape, evaluate, and recommend products based on user-defined priorities.

---

## 🏗️ Architecture Flow
The project follows a decoupled architecture where the extension handles the UI, while a Python/FastAPI backend manages the heavy lifting of scraping and LLM orchestration.

![Architecture Diagram](assets/architecture_diagram.png)

### The 3-Step Pipeline:
1.  **Step 1: Stealth Scraper (Playwright)**: Bypasses anti-bot mechanisms to extract organic product listings, technical specs, and AI review summaries from Amazon.
2.  **Step 2: Product Analysis Agent (Scorer)**: A high-reasoning LLM agent that evaluates each product objectively against user priorities.
3.  **Step 3: Recommendation Agent (Consultant)**: A master synthesis agent that weighs trade-offs and delivers a final comparative recommendation.

---

## 🛠️ Project Learnings & Technical Deep Dive

### 1. LLM Gateway Integration
The **LLM Gateway** acts as the central nervous system for all AI interactions, abstracting provider complexity.
*   **Failover & Reliability**: Automatically reroutes requests from Gemini Flash to Flash Lite or Gemma if rate limits (429) are hit.
*   **Quota Enforcement**: Manages precise **RPM (Requests Per Minute)** and **RPD (Requests Per Day)** to stay within Free Tier limits.
*   **Unified Interface**: The agent sends a single request to `:8100/v1/chat`, and the Gateway handles authentication and formatting.

### 2. Pydantic as the Project's "Data Spine"
We use **Pydantic (v2)** to define the strict data contracts between the system components.
```python
# Product Analysis Agent (The "Scorecard")
class CriterionEvaluation(BaseModel):
    analysis: str
    score: Literal["positive", "neutral", "negative", "uncertain"]
    reasoning_type: Literal["specs_analysis", "sentiment_analysis", "price_logic", "missing_data"]
    internal_check_passed: bool

# Recommendation Agent (Final Comparison)
class AgentAnalysisResult(BaseModel):
    overall_agent_summary: str
    products: list[ProductAnalysis]
    reasoning_type: Literal["arithmetic", "logic", "lookup"]
    self_verification_log: str # Log of internal sanity checks
    fallback_applied: bool     # Error handling flag
```
*   **Validation**: Strictly parses raw AI strings into Python objects using `model_validate_json()`.
*   **Schema Enforcement**: Generates the "instruction manual" for the LLM via `model_json_schema()`.

### 3. Structured Prompting, Thinking & Reasoning
To meet rigorous academic standards, we implemented a "Hardened" prompting strategy based on 8 pillars:
*   **Explicit Reasoning**: "THINK STEP-BY-STEP" instructions.
*   **Tool Separation**: Distinguishing between 'Raw Tool Output' and 'Agent Analysis'.
*   **Conversation Loop**: Framing agents as specific steps in an autonomous journey.
*   **Internal Self-Checks**: Explicit verification of data points before outputting.

#### 🧪 Agent 1: The Product Analysis Agent (Scorer)
*   **System Prompt**: "You are a Prompt Evaluation-ready Assistant. Rules: EXPLAIN YOUR THINKING, SELF-VERIFY all data points."
*   **Config**: `reasoning="high"`, `thinking=True`, `cache_system=True`.

![Prompt 1 Success](assets/Prompt1 Success.png)

#### 🧪 Agent 2: The Recommendation Agent (Consultant)
*   **System Prompt**: "You are a master Personal Shopping Consultant. SYNTHESIZE the buying journey and maintain DATA INTEGRITY."
*   **Config**: `reasoning="high"`, `thinking=True`, `cache_system=True`.

![Prompt 2 Success](assets/Prompt2 Success.png)

---

## 🚀 Getting Started
1. Start the LLM Gateway.
2. Run the FastAPI server: `uvicorn api:app --reload`.
3. Load the Extension in Chrome and start searching!
