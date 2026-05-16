import sys
from pathlib import Path
import json

sys.path.insert(0, "/Users/pradeep/Library/CloudStorage/OneDrive-Personal/ML/2026 ML Projects/EAG Session5 Practice/llm_gatewayV2")
try:
    from client import LLM
except ImportError as e:
    print(f"Could not import LLM Gateway V2: {e}")
    # Mock LLM for tests if gateway is missing
    class LLM:
        def chat(self, *args, **kwargs):
            return {"parsed": {"overall_agent_summary": "Test", "products": []}}

from pydantic import create_model, BaseModel
from schemas import SearchTask, AgentAnalysisResult, Product, ProductAnalysis, Stage2Recommendation, CriterionEvaluation

def evaluate_products(task: SearchTask, products: list[Product]) -> AgentAnalysisResult:
    llm = LLM()
    
    def dereference_schema(node, defs):
        if isinstance(node, dict):
            if "$ref" in node:
                ref_key = node["$ref"].split("/")[-1]
                return dereference_schema(defs[ref_key], defs)
            return {k: dereference_schema(v, defs) for k, v in node.items()}
        elif isinstance(node, list):
            return [dereference_schema(x, defs) for x in node]
        return node
        
    # --- STAGE 1: Batched Evaluations ---
    DynamicEvalModel = create_model(
        'DynamicEvalModel', 
        **{crit: (CriterionEvaluation, ...) for crit in task.priorities}
    )
    
    class ProductBatchEval(BaseModel):
        product_id: str
        evaluations: DynamicEvalModel

    class Stage1BatchEvaluation(BaseModel):
        product_evaluations: list[ProductBatchEval]
        
    raw_schema1 = Stage1BatchEvaluation.model_json_schema()
    defs1 = raw_schema1.pop("$defs", {})
    schema1 = dereference_schema(raw_schema1, defs1)
    
    batch_prompt = f"The user is looking for: \"{task.query}\"\n\n"
    batch_prompt += f"Please critically evaluate the following {len(products)} products against these EXACT criteria: {', '.join(task.priorities)}\n\n"
    
    for p in products:
        batch_prompt += f"--- PRODUCT ID: {p.id} ---\n"
        batch_prompt += f"Title: {p.title}\n"
        batch_prompt += f"Price: {p.price}\n"
        batch_prompt += f"Rating: {p.rating} ({p.reviews_count} reviews)\n"
        batch_prompt += f"Amazon AI Summary: {p.ai_review_summary}\n"
        batch_prompt += f"Top Reviews:\n{p.top_reviews}\n\n"

    batch_prompt += """
CRITICAL INSTRUCTIONS:
1. **PIPELINE CONTEXT (Conversation Loop)**: You are Step 2 of a 3-step autonomous pipeline. You are receiving output from Step 1 (Web Scraping Tool). Your scoring matrix will be the ONLY input for Step 3 (Recommendation Agent).
2. **TOOL SEPARATION**: The product data provided below is 'Tool Output'. Do not use pre-trained external knowledge about these products. Evaluate ONLY the text provided.
3. **REASONING TYPE**: For each criterion, identify if you are doing 'specs_analysis', 'sentiment_analysis', or 'price_logic'.
4. **INTERNAL SELF-CHECK**: Before submitting, verify that the ASIN and price match the input data exactly. Set 'internal_check_passed' to true only after verification.
5. **FALLBACKS**: If data for a criterion is missing or conflicting, set the score to 'uncertain' and reasoning_type to 'missing_data'.
6. **THINKING**: Do not rush. Reason step-by-step for each product's attributes.
"""
    
    stage1_results = {}
    try:
        print(f"Executing Product Analysis Agent scoring for {len(products)} products...")
        res1 = llm.chat(
            prompt=batch_prompt,
            system="""You are a Prompt Evaluation-ready Assistant. 
You must follow these strict operational rules:
- EXPLAIN YOUR THINKING: Use the 'analysis' field to show your step-by-step logic.
- SELF-VERIFY: Perform internal sanity checks on every data point.
- STRUCTURED OUTPUT: Return ONLY a valid JSON object matching the schema.
""",
            response_format={
                "type": "json_schema",
                "schema": schema1,
                "name": "Stage1BatchEvaluation",
                "strict": True,
            },
            reasoning="high"
        )
        parsed1 = res1.get("parsed") or json.loads(res1.get("text", "{}"))
        for eval_item in parsed1.get("product_evaluations", []):
            pid = eval_item.get("product_id")
            stage1_results[pid] = eval_item
    except Exception as e:
        print(f"Batched Stage 1 LLM evaluation failed: {e}")
        for p in products:
            stage1_results[p.id] = {"evaluations": {}}

    # --- STAGE 2: Final Holistic Recommendation ---
    prompt2 = f"""You are a master personal shopping assistant. You have individually evaluated {len(products)} products based on the user's priorities: {', '.join(task.priorities)}.

Here are your individual scorecards AND the raw Amazon AI summaries for the products:
"""
    for p in products:
        evals = json.dumps(stage1_results.get(p.id, {}))
        prompt2 += f"\nProduct ID: {p.id}\nTitle: {p.title}\nPrice: {p.price}\nAmazon AI Summary: {p.ai_review_summary}\nEvaluations: {evals}\n"

    prompt2 += """
CRITICAL INSTRUCTIONS FOR HOLISTIC ANALYSIS:
3. **REASONING TYPE AWARENESS**: Identify the type of reasoning used for this final decision (e.g., arithmetic, logic, lookup). For this holistic synthesis and comparison, set 'reasoning_type' to 'logic'.
4. **THINK STEP-BY-STEP**: Compare the individual scorecards across all products for each priority. Identify contradictions or clear winners.
5. **IDENTIFY TRADE-OFFS**: Weigh 'High Quality' against 'Low Price'. Use the scores provided by the Product Analysis Agent to inform this.
6. **INTERNAL SELF-CHECK**: Perform a final sanity check. Verify that your recommended product actually exists in the provided list and satisfies at least one top priority.
7. **ERROR HANDLING**: If the data is too sparse to make a recommendation, set 'fallback_applied' to true and recommend the item with the highest review count as a safety measure.
8. **VERIFICATION LOG**: Document your internal checks in the 'self_verification_log'.
"""
    
    raw_schema2 = Stage2Recommendation.model_json_schema()
    defs2 = raw_schema2.pop("$defs", {})
    schema2 = dereference_schema(raw_schema2, defs2)
    
    try:
        print("Executing Recommendation Agent final holistic analysis...")
        reply2 = llm.chat(
            prompt=prompt2,
            system="""You are a master Personal Shopping Consultant. 
Rules:
- SYNTHESIZE: Treat this as the final step in the user's buying journey.
- DATA INTEGRITY: Distinguish between raw product facts and previous analysis scores.
- FALLBACKS: If you are unsure, admit it and recommend the safest choice based on review counts.
- MULTI-TURN AWARENESS: This is the final synthesis of the preceding search and scoring phases.
""",
            response_format={
                "type": "json_schema",
                "schema": schema2,
                "name": "Stage2Recommendation",
                "strict": True,
            },
            reasoning="high"
        )
        parsed2 = reply2.get("parsed") or json.loads(reply2.get("text", "{}"))
        top_id = parsed2.get("top_recommendation_product_id")
        summary = parsed2.get("overall_agent_summary", "Evaluation complete.")
    except Exception as e:
        print(f"Stage 2 LLM evaluation failed: {e}")
        top_id = products[0].id if products else None
        summary = "Could not generate final recommendation due to an error."
        
    # --- Assemble Final Payload ---
    final_products = []
    for p in products:
        raw_evals = stage1_results.get(p.id, {}).get("evaluations", {})
        is_top = (p.id == top_id)
        
        # Ensure we have all criteria keys populated exactly as the frontend expects
        safe_evals = {}
        for crit in task.priorities:
            if crit in raw_evals:
                if isinstance(raw_evals[crit], dict):
                    safe_evals[crit] = CriterionEvaluation(**raw_evals[crit])
                else:
                    safe_evals[crit] = raw_evals[crit]
            else:
                safe_evals[crit] = CriterionEvaluation(analysis="No data generated by Agent for this criterion.", score="neutral")

        final_products.append(ProductAnalysis(
            product_id=p.id,
            is_top_recommendation=is_top,
            evaluations=safe_evals
        ))
        
    return AgentAnalysisResult(
        overall_agent_summary=summary,
        products=final_products,
        reasoning_type=parsed2.get("reasoning_type", "logic"),
        self_verification_log=parsed2.get("self_verification_log", "Standard checks performed."),
        fallback_applied=parsed2.get("fallback_applied", False)
    )
