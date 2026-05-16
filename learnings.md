# Project Learnings: Shopping Agent v2

This document outlines the core architectural patterns and technical implementation details of the Shopping Agent v2 project, focusing on reliability, data integrity, and advanced prompt engineering.

---

## 1. LLM Gateway Integration
The **LLM Gateway** acts as the central nervous system for all AI interactions, abstracting provider complexity.

### Key Capabilities:
*   **Failover & Reliability**: Automatically reroutes requests from Gemini Flash to Flash Lite or Gemma if rate limits (429) are hit.
*   **Quota Enforcement**: Manages precise **RPM (Requests Per Minute)** and **RPD (Requests Per Day)** to stay within Free Tier limits (e.g., 20 RPD for Flash).
*   **Unified Interface**: The agent sends a single request to `:8100/v1/chat`, and the Gateway handles authentication, retries, and formatting.

---

## 2. Pydantic as the Project's "Data Spine"
We use **Pydantic (v2)** to define the strict data contracts between the Scraper, the AI agents, and the Frontend.

### A. Core Data Definitions (`schemas.py`)
We use multiple nested models to manage the complex data flow:
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

### B. Advanced JSON Operations
*   **`model_json_schema()`**: Automatically generates the "instruction manual" sent to the LLM Gateway to enforce Strict Mode.
*   **`model_validate_json()`**: Strictly parses and validates raw AI strings into Python objects, ensuring no "hallucinated" fields enter our system.
*   **`model_dump_json()`**: Standardizes the "Round Trip" from the Python backend to the Javascript Chrome extension.

---

## 3. Structured Prompting, Thinking & Reasoning
To achieve high-quality results, we implemented a "Hardened" prompting strategy that satisfies 9 key criteria for robust agentic behavior.

### The 8 Pillars of Our Prompting Strategy:
1.  **Explicit Reasoning**: Instructing the model to "THINK STEP-BY-STEP" before providing an answer.
2.  **Structured Output**: Enforcing Pydantic schemas via the API for predictable parsing.
3.  **Tool Separation**: Distinguishing between raw Scraper facts and Agent evaluations.
4.  **Conversation Loop**: Framing each step as a specific part of a multi-turn autonomous journey.
5.  **Instructional Framing**: Using explicit guidelines for trade-off analysis (e.g., Quality vs. Price).
6.  **Internal Self-Checks**: Requiring the model to verify its own output against the input data.
7.  **Reasoning Type Awareness**: Tagging logic as factual (specs) or inferred (sentiment).
8.  **Error Handling**: Defining clear fallbacks for missing or conflicting data.

### 🧪 Prompt 1: The Product Analysis Agent (Scorer)
**Goal**: Evaluate products objectively with self-verification.

*   **System Prompt**: 
    > "You are a Prompt Evaluation-ready Assistant. You must follow these strict operational rules: EXPLAIN YOUR THINKING, SELF-VERIFY all data points, and return ONLY valid JSON matching the schema."
*   **User Prompt**:
    > "Evaluate these products: {product_data} against these criteria: {priorities}. 
    > **PIPELINE CONTEXT**: You are Step 2 of a 3-step pipeline. You are receiving output from the Step 1 'Web Scraping Tool'.
    > **TOOL SEPARATION**: Treat provided data as 'Tool Output'. Do not use external knowledge.
    > **REASONING TYPE**: Identify if you are doing 'specs_analysis', 'sentiment_analysis', or 'price_logic'.
    > **INTERNAL SELF-CHECK**: Verify that the ASIN and price match input exactly.
    > **FALLBACKS**: If data is missing, mark as 'uncertain'."
*   **API Configuration**:
    ```python
    reply = llm.chat(
        system=STAGE1_SYSTEM_PROMPT,
        cache_system=True,      # Optimized for repeat tokens
        reasoning="high",       # HIGH reasoning for objective accuracy
        thinking=True,          # Explicit CoT deliberation
        temperature=0,          # Zero-variance results
        response_format=Stage1BatchEvaluation.model_json_schema()
    )
    ```

![Prompt 1 Success (ChatGPT Evaluation)](/Users/pradeep/.gemini/antigravity/brain/04f6bc5e-f281-40e7-9acc-84014e1bd072/Prompt1_Success.png)

### 🧪 Prompt 2: The Recommendation Agent (Consultant)
**Goal**: Final holistic synthesis and personal recommendation.

*   **System Prompt**: 
    > "You are a master Personal Shopping Consultant. SYNTHESIZE the buying journey, maintain DATA INTEGRITY, and admit uncertainty if it arises. Use the 'overall_agent_summary' field to speak directly to the user as their personal shopping expert."
    > "**PIPELINE CONTEXT**: Final synthesis step. Closing the conversation loop.
    > **TOOL SEPARATION**: Distinguish between 'Raw Data' (Scraper) and 'Scorecards' (Product Analysis Agent).
    > "**REASONING TYPE AWARENESS**: Identify the type of reasoning used (arithmetic, logic, lookup). Set to 'logic' for this synthesis.
    > **THINK STEP-BY-STEP**: Compare scorecards and identify clear winners.
    > **IDENTIFY TRADE-OFFS**: Weigh 'High Quality' against 'Low Price'. 
    > **INTERNAL SELF-CHECK**: Sanity check the recommendation list.
    > **VERIFICATION LOG**: Document your internal checks in 'self_verification_log'."
*   **API Configuration**:
    ```python
    reply = llm.chat(
        system=STAGE2_SYSTEM_PROMPT,
        cache_system=True,      # Preserve the consultant persona
        reasoning="high",       # COMPARATIVE DELIBERATION
        thinking=True,          # Critical trade-off analysis
        temperature=0,          # High-accuracy comparative logic
        response_format=AgentAnalysisResult.model_json_schema()
    )
    ```

![Prompt 2 Success (ChatGPT Evaluation)](/Users/pradeep/.gemini/antigravity/brain/04f6bc5e-f281-40e7-9acc-84014e1bd072/Prompt2_Success.png)
