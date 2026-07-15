"""
文档加载与分块模块

负责加载 knowledge_base/ 目录下的所有 Markdown 知识文档，
并按指定大小和重叠量进行文本分块（chunking），
为后续的向量化和语义检索做准备。
"""

import os
import re
from typing import List, Dict


class DocumentLoader:
    """
    文档加载器

    加载 knowledge_base/ 目录下的 .md 文件，
    将每个文档按段落分块，并提取文档标题作为元数据。
    """

    def __init__(self, knowledge_base_dir: str = None):
        """
        初始化文档加载器

        Args:
            knowledge_base_dir: 知识库文档目录路径，默认为 backend/knowledge_base/
        """
        if knowledge_base_dir is None:
            # 相对于当前文件所在目录的路径：app/rag/ -> ../../knowledge_base/
            knowledge_base_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..", "..", "knowledge_base"
            )
        self.knowledge_base_dir = os.path.abspath(knowledge_base_dir)

    def load_documents(self) -> List[Dict[str, str]]:
        """
        加载 knowledge_base/ 目录下所有 .md 文件

        遍历知识库目录，读取每个 .md 文件的完整内容，
        并提取文档标题（第一个 # 开头的行）作为元数据。

        Returns:
            List[Dict]: 文档列表，每个文档包含 content（文本内容）和 metadata（元数据）字段
                格式：[{"content": "文档内容...", "metadata": {"title": "文档标题", "source": "文件名"}}, ...]
        """
        documents = []

        if not os.path.isdir(self.knowledge_base_dir):
            print(f"知识库目录不存在: {self.knowledge_base_dir}")
            return documents

        for filename in sorted(os.listdir(self.knowledge_base_dir)):
            if not filename.endswith(".md"):
                continue

            filepath = os.path.join(self.knowledge_base_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                print(f"读取文档失败 {filename}: {e}")
                continue

            if not content.strip():
                continue

            # 提取文档标题：第一个 # 开头的行
            title = filename.replace(".md", "")
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith("# ") and not line.startswith("## "):
                    title = line[2:].strip()
                    break

            documents.append({
                "content": content,
                "metadata": {
                    "title": title,
                    "source": filename,
                }
            })

        return documents

    def split_documents(
        self,
        documents: List[Dict[str, str]],
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> List[Dict[str, str]]:
        """
        按指定大小和重叠量对文档进行分块

        分块策略：
        1. 先按段落（双换行）进行初步分割
        2. 再将段落按句子（中文句号、换行等）进一步切分
        3. 合并短句直到达到 chunk_size，同时保留 chunk_overlap 长度的重叠

        Args:
            documents: load_documents() 返回的文档列表
            chunk_size: 每个文本块的最大字符数，默认 500
            chunk_overlap: 相邻文本块之间的重叠字符数，默认 50

        Returns:
            List[Dict]: 分块后的文档片段列表
                格式：[{"content": "片段文本...", "metadata": {"title": "...", "source": "...", "chunk_index": 0}}, ...]
        """
        chunks = []

        for doc in documents:
            content = doc["content"]
            metadata = doc["metadata"]

            # 第一步：按段落分割（双换行或 ## 标题）
            paragraphs = re.split(r"\n\n|\n## ", content)
            paragraphs = [p.strip() for p in paragraphs if p.strip()]

            # 第二步：按句子进一步分割（中文句号、问号、感叹号、换行）
            sentences = []
            for para in paragraphs:
                # 按中文标点符号和换行分割
                parts = re.split(r"(?<=[。！？\n])", para)
                for part in parts:
                    part = part.strip()
                    if part:
                        sentences.append(part)

            # 第三步：合并句子成块，确保每个块不超过 chunk_size
            chunk_index = 0
            current_chunk = ""
            current_length = 0

            for sentence in sentences:
                sentence_len = len(sentence)

                # 如果当前块加上新句子会超过 chunk_size，先保存当前块
                if current_length + sentence_len > chunk_size and current_chunk:
                    chunks.append({
                        "content": current_chunk.strip(),
                        "metadata": {
                            **metadata,
                            "chunk_index": chunk_index,
                        }
                    })
                    chunk_index += 1

                    # 重叠处理：保留最后 chunk_overlap 个字符作为新块的起始
                    if chunk_overlap > 0 and len(current_chunk) > chunk_overlap:
                        current_chunk = current_chunk[-chunk_overlap:]
                        current_length = len(current_chunk)
                    else:
                        current_chunk = ""
                        current_length = 0

                current_chunk += sentence
                current_length += sentence_len

            # 保存最后一个块
            if current_chunk.strip():
                chunks.append({
                    "content": current_chunk.strip(),
                    "metadata": {
                        **metadata,
                        "chunk_index": chunk_index,
                    }
                })

        return chunks