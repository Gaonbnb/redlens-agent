# 评估服务
class DemoEvaluator:
    def summary(self) -> dict:
        return {
            "status": "placeholder",
            "supported_metrics": [
                "hit_at_3",
                "module_recall",
                "context_relevance",
                "suggestion_actionability",
            ],
            "note": "Replace with Ragas + business gold set in later stages.",
        }
