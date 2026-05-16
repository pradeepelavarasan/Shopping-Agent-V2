# Shopping Agent v2: Autonomous Product Researcher

> ✨ **Your AI Shopping Consultant = Multi-Agent Reasoning + Stealth Scraping.**

📹 **Demo Video:** [https://youtu.be/v-O43Ika84I](https://youtu.be/v-O43Ika84I)

---

## 📖 "The What"
Shopping Agent v2 is a fully autonomous research agent. It takes a search query, navigates the web using stealth scraping, extracts high-fidelity data, and runs a multi-stage reasoning pipeline to deliver an expert recommendation.

---

## 🤔 "The Why"
Shopping research is cognitively exhausting. Context-switching between tabs and deciphering thousands of reviews kills comprehension. v2 collapses this loop into a single, instant view, acting as your **Personal Shopping Consultant**.

---

## 📖 "The Learnings"

This section outlines the core architectural patterns and technical implementation details of the project.

### 1. LLM Gateway Integration
The **LLM Gateway** acts as the central hub for all AI interactions, abstracting provider complexity.
*   **Failover & Reliability**: Automatically reroutes requests from Gemini Flash to Flash Lite or Gemma if rate limits (429) are hit.
*   **Quota Enforcement**: Manages precise **RPM (Requests Per Minute)** and **RPD (Requests Per Day)** to stay within Free Tier limits.
*   **Unified Interface**: A single local endpoint handles authentication, retries, and formatting.

### 2. Pydantic as the Project's "Data Spine"
We use **Pydantic (v2)** to define strict data contracts:
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

### 3. Structured Prompting, Thinking & Reasoning
To achieve high-quality results, we implemented a "Hardened" prompting strategy that satisfies 9 key criteria for robust agentic behavior.

#### The 8 Pillars of Our Prompting Strategy:
1.  **Explicit Reasoning**: Instructing the model to "THINK STEP-BY-STEP".
2.  **Structured Output**: Enforcing Pydantic schemas via the API.
3.  **Tool Separation**: Distinguishing between raw Scraper facts and Agent evaluations.
4.  **Conversation Loop**: Framing each step as a specific part of an autonomous journey.
5.  **Instructional Framing**: Using explicit guidelines for trade-off analysis.
6.  **Internal Self-Checks**: Requiring the model to verify its own output.
7.  **Reasoning Type Awareness**: Tagging logic (arithmetic, logic, lookup).
8.  **Error Handling**: Defining clear fallbacks for missing data.

#### 🧪 Agent 1: The Product Analysis Agent (Scorer)
*   **System Prompt**: 
    > "You are a Prompt Evaluation-ready Assistant. Rules: EXPLAIN YOUR THINKING, SELF-VERIFY all data points, and return ONLY valid JSON matching the schema."
*   **User Prompt**:
    > "Evaluate these products: {product_data} against these criteria: {priorities}. 
    > **PIPELINE CONTEXT**: Step 2 of 3. You are receiving output from the Step 1 'Web Scraping Tool'.
    > **TOOL SEPARATION**: Treat provided data as 'Tool Output'. Do not use external knowledge.
    > **REASONING TYPE**: Identify logic (specs_analysis, sentiment_analysis, or price_logic).
    > **INTERNAL SELF-CHECK**: Verify ASIN and price match input exactly."
*   **API Configuration**:
    ```python
    reply = llm.chat(
        system=STAGE1_SYSTEM_PROMPT,
        cache_system=True, reasoning="high", thinking=True, temperature=0,
        response_format=Stage1BatchEvaluation.model_json_schema()
    )
    ```

![Prompt 1 Success](https://raw.githubusercontent.com/pradeepelavarasan/Shopping-Agent-V2/main/assets/prompt1_success.png)

#### 🧪 Agent 2: The Recommendation Agent (Consultant)
*   **System Prompt**: 
    > "You are a master Personal Shopping Consultant. SYNTHESIZE the buying journey, maintain DATA INTEGRITY, and admit uncertainty if it arises."
*   **User Prompt**:
    > "**PIPELINE CONTEXT**: Final synthesis step. Closing the conversation loop.
    > **TOOL SEPARATION**: Distinguish between 'Raw Data' (Scraper) and 'Scorecards' (Product Analysis Agent).
    > **REASONING TYPE AWARENESS**: Identify the type (arithmetic, logic, lookup). Set to 'logic'.
    > **THINK STEP-BY-STEP**: Compare scorecards and identify clear winners."
*   **API Configuration**:
    ```python
    reply = llm.chat(
        system=STAGE2_SYSTEM_PROMPT,
        cache_system=True, reasoning="high", thinking=True, temperature=0,
        response_format=AgentAnalysisResult.model_json_schema()
    )
    ```

![Prompt 2 Success](https://raw.githubusercontent.com/pradeepelavarasan/Shopping-Agent-V2/main/assets/prompt2_success.png)

---

## 🛠️ "The How" — Technical Architecture

![Architecture Diagram](https://raw.githubusercontent.com/pradeepelavarasan/Shopping-Agent-V2/main/assets/architecture_diagram.png)

```text
┌─────────────────────────────────────────────────────┐
│              User Interface (Chrome Extension)      │
└───────────────┬─────────────────────────────────────┘
                ▼
┌─────────────────────────────────────────────────────┐
│          FastAPI Backend (Orchestration Layer)      │
│  1. Stealth Scraper (Playwright)                    │
│  2. Product Analysis Agent (Scorer)                 │
│  3. Recommendation Agent (Consultant)               │
└───────────────┬─────────────────────────────────────┘
                ▼
┌─────────────────────────────────────────────────────┐
│              LLM Gateway (Central Nervous System)   │
└─────────────────────────────────────────────────────┘
```

---

*Built by [Pradeep Elavarasan](https://www.linkedin.com/in/pradeepelavarasan/) · Co-created with Google Agent*
