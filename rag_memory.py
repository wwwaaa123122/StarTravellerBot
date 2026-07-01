import json
import os
import math
import time
from collections import Counter
from typing import List


class RAGMemory:
    """基于检索增强生成(RAG)的对话记忆系统
    使用字符 bigram TF-IDF 进行中文语义检索
    """

    def __init__(self, data_dir: str):
        self.data_dir = os.path.join(data_dir, "rag")
        os.makedirs(self.data_dir, exist_ok=True)
        self.top_k = 3
        self.min_relevance = 0.05
        self.max_tokens = 800

    def _path(self, user_id: str) -> str:
        return os.path.join(self.data_dir, f"{user_id}.json")

    def load(self, user_id: str) -> dict:
        path = self._path(user_id)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"user_id": user_id, "exchanges": []}

    def save(self, user_id: str, data: dict):
        with open(self._path(user_id), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _tokenize(self, text: str) -> List[str]:
        text = text.lower()
        return [text[i:i+2] for i in range(len(text) - 1)]

    def _calc_similarity(self, q_tokens: List[str], d_tokens: List[str],
                         idf: dict) -> float:
        q_tf = Counter(q_tokens)
        d_tf = Counter(d_tokens)
        q_vec = {t: f * idf.get(t, 1.0) for t, f in q_tf.items()}
        d_vec = {t: f * idf.get(t, 1.0) for t, f in d_tf.items()}
        all_tokens = set(q_vec) | set(d_vec)
        dot = sum(q_vec.get(t, 0) * d_vec.get(t, 0) for t in all_tokens)
        q_norm = math.sqrt(sum(v ** 2 for v in q_vec.values()))
        d_norm = math.sqrt(sum(v ** 2 for v in d_vec.values()))
        return dot / (q_norm * d_norm) if q_norm and d_norm else 0.0

    def add_exchange(self, user_id: str, question: str, answer: str):
        data = self.load(user_id)
        data["exchanges"].append({
            "q": question[:300],
            "a": answer[:500],
            "ts": time.time(),
        })
        if len(data["exchanges"]) > 200:
            data["exchanges"] = data["exchanges"][-200:]
        self.save(user_id, data)

    def get_relevant_context(self, user_id: str, query: str) -> str:
        data = self.load(user_id)
        if not data["exchanges"]:
            return ""

        exchanges = data["exchanges"]
        q_tokens = self._tokenize(query)

        all_text = " ".join(e["q"] + e["a"] for e in exchanges)
        all_tokens = self._tokenize(all_text)
        n_docs = len(exchanges)
        token_freq = Counter(all_tokens)
        idf = {t: math.log(n_docs / (1 + f)) for t, f in token_freq.items()}

        scored = []
        for i, e in enumerate(exchanges):
            doc = e["q"] + e["a"]
            d_tokens = self._tokenize(doc)
            sim = self._calc_similarity(q_tokens, d_tokens, idf)
            # 相关性 × 新鲜度权重
            recency = 1.0 + 0.15 * (i / max(1, n_docs - 1))
            scored.append((sim * recency, e))

        scored.sort(key=lambda x: -x[0])
        top = [e for s, e in scored if s > self.min_relevance][:self.top_k]

        if not top:
            return ""

        lines = ["## 📝 相关历史对话"]
        char_count = 0
        for e in top:
            entry = f"> 用户: {e['q']}\n> 你: {e['a']}"
            char_count += len(entry)
            if char_count > self.max_tokens:
                break
            lines.append(entry)

        return "\n\n".join(lines)
