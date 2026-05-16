import sys
sys.path.insert(0, "/Users/pradeep/Library/CloudStorage/OneDrive-Personal/ML/2026 ML Projects/EAG Session5 Practice/llm_gatewayV2")
from client import LLM

from schemas import Stage1Evaluation, CriterionEvaluation

def flatten_schema(schema: dict) -> dict:
    if "$defs" not in schema: return schema
    defs = schema.pop("$defs")
    def resolve_refs(node):
        if isinstance(node, dict):
            if "$ref" in node:
                ref_key = node.pop("$ref").split("/")[-1]
                if ref_key in defs:
                    for k, v in defs[ref_key].items(): node[k] = v
            for k, v in node.items(): resolve_refs(v)
        elif isinstance(node, list):
            for item in node: resolve_refs(item)
    resolve_refs(schema)
    return schema

llm = LLM()
raw_schema1 = Stage1Evaluation.model_json_schema()
defs1 = raw_schema1.pop("$defs", {})
schema1 = flatten_schema(raw_schema1)
print("Schema:", schema1)

prompt1 = """The user wants to search for: "kids tricycle"
Please critically evaluate the following product against these EXACT criteria: Customer Sentiment, Reliability, Value for Money, Feature Completeness, Build Quality

Product ID: B0GD7TDTN1
Title: R for Rabbit Tiny Toes
Price: 100
Rating: 4.5
Top Reviews:
Great product!

IMPORTANT: You MUST return a dictionary where the keys are EXACTLY the priority strings provided above. Do not alter the casing or spelling of the keys.
"""

reply1 = llm.chat(
    prompt=prompt1,
    system="You are an expert AI Shopping Agent. Respond exactly as requested in JSON format matching the schema.",
    response_format={
        "type": "json_schema",
        "schema": schema1,
        "name": "Stage1Evaluation",
        "strict": True,
    },
    reasoning="low"
)
print("Reply:", reply1)
