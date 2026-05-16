from pydantic import BaseModel, Field
from typing import Literal

class Product(BaseModel):
    id: str
    url: str
    title: str
    price: str | None = None
    rating: str | None = None
    reviews_count: int | None = None
    image_url: str | None = None
    is_sponsored: bool = False
    
    # Used for LLM context
    top_reviews: str | None = None
    ai_review_summary: str | None = None

class CriterionEvaluation(BaseModel):
    analysis: str = Field(description="A critical 1-2 sentence evaluation based on the data")
    score: Literal["positive", "neutral", "negative", "uncertain"] = Field(description="The evaluation score. Use 'uncertain' if data is missing.")
    reasoning_type: Literal["specs_analysis", "sentiment_analysis", "price_logic", "missing_data"] = Field(description="The type of reasoning used for this criterion")
    internal_check_passed: bool = Field(description="True if the agent verified this against the raw data")

class Stage1Evaluation(BaseModel):
    evaluations: dict[str, CriterionEvaluation]

class Stage2Recommendation(BaseModel):
    overall_agent_summary: str = Field(description="Expert comparative recommendation summary.")
    top_recommendation_product_id: str
    reasoning_type: Literal["arithmetic", "logic", "lookup"] = Field(description="The type of reasoning used (e.g., 'logic' for synthesis).")
    self_verification_log: str = Field(description="A brief log of internal sanity checks performed.")
    fallback_applied: bool = Field(description="True if fallback logic was needed due to missing data.")

class ProductAnalysis(BaseModel):
    product_id: str
    is_top_recommendation: bool
    evaluations: dict[str, CriterionEvaluation]

class AgentAnalysisResult(BaseModel):
    overall_agent_summary: str = Field(description="Expert comparative recommendation summary.")
    products: list[ProductAnalysis]
    reasoning_type: Literal["arithmetic", "logic", "lookup"] = Field(description="The type of reasoning used.")
    self_verification_log: str = Field(description="A brief log of internal sanity checks performed.")
    fallback_applied: bool = Field(description="True if fallback logic was needed due to missing data.")

class SearchTask(BaseModel):
    query: str
    priorities: list[str]

class QueueItem(BaseModel):
    id: str
    task: SearchTask
    status: Literal["queued", "searching", "analyzing", "complete", "error"] = "queued"
    error_message: str | None = None
    products: list[Product] | None = None
    analysis: AgentAnalysisResult | None = None
