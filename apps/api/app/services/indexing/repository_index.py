# 代码索引 用于存储和检索代码模块、提交记录、案例
import json
from pathlib import Path


class RepositoryIndex:
    def __init__(self) -> None:
        data_dir = Path(__file__).resolve().parents[2] / "data"
        self.modules = self._load_json(data_dir / "sample_modules.json")
        self.commits = self._load_json(data_dir / "sample_commits.json")
        self.cases = self._load_json(data_dir / "sample_cases.json")

    def _load_json(self, path: Path) -> list[dict]:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    # 获取所有模块
    def list_modules(self) -> list[dict]:
        return self.modules
    # 获取单个模块
    def get_module(self, module_id: str) -> dict:
        for item in self.modules:
            if item["id"] == module_id:
                return item
        raise KeyError(f"Module {module_id} not found")
    # 关键词匹配打分排序模块
    def rank_modules(self, keywords: list[str]) -> list[dict]:
        ranked = []
        for module in self.modules:
            terms = " ".join(module["keywords"]).lower()
            score = sum(1 for keyword in keywords if keyword.lower() in terms)
            if score > 0:
                ranked.append(
                    {
                        "id": module["id"],
                        "name": module["name"],
                        "score": round(min(0.99, 0.45 + score * 0.12), 2),
                        "reason": f"命中关键词 {', '.join([k for k in keywords if k.lower() in terms])}",
                    }
                )

        if not ranked:
            ranked = [
                {
                    "id": self.modules[0]["id"],
                    "name": self.modules[0]["name"],
                    "score": 0.42,
                    "reason": "未命中明确关键词，按默认 runtime 场景回退。",
                }
            ]

        return sorted(ranked, key=lambda item: item["score"], reverse=True)
    # 基于模块ID召回相关文件
    def related_files(self, module_ids: list[str]) -> list[str]:
        files = []
        for module in self.modules:
            if module["id"] in module_ids:
                files.extend(module["key_files"])
        return files[:5]
    # 基于关键词召回相关提交
    def related_commits(self, keywords: list[str]) -> list[dict]:
        matched = []
        for commit in self.commits:
            haystack = f"{commit['message']} {' '.join(commit['keywords'])}".lower()
            if any(keyword.lower() in haystack for keyword in keywords):
                matched.append(commit)
        return matched[:3]
