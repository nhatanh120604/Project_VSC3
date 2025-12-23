from __future__ import annotations

import csv
from datetime import datetime
import logging
from pathlib import Path
import re
from typing import Dict, Iterable, List, Optional, Sequence
from urllib.parse import quote, quote_plus

try:  # Torch is optional at runtime, fall back to CPU if unavailable
    import torch
except Exception:  # pragma: no cover - torch might be missing on smaller deployments
    torch = None  # type: ignore

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import CrossEncoder

from ..schemas import SourceChunk
from ..settings import Settings

LOGGER = logging.getLogger(__name__)


def load_documents(data_dir: Path, extensions: Sequence[str]) -> List[Document]:
    """
    Load documents from data.csv.
    Ignores extensions argument for now as we strictly look for data.csv.
    """
    csv_path = data_dir / "data.csv"
    if not csv_path.exists():
        # Fallback to searching for any csv if data.csv doesn't exist
        csv_files = list(data_dir.glob("*.csv"))
        if not csv_files:
            raise ValueError(f"No CSV files found in {data_dir}.")
        csv_path = csv_files[0]

    documents: List[Document] = []

    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Extract fields based on the CSV structure
            # Headers: Động từ (Action), Đối tượng..., Công thức gốc..., Ngày xuất bản, Số báo, Báo
            action = row.get("Động từ (Action)", "").strip()
            original_recipe = row.get("Công thức gốc (Original recipes)", "").strip()

            # Handle potential trailing space in CSV header for "Nguyên văn"
            full_text = row.get("Nguyên văn", "").strip()
            if not full_text:
                full_text = row.get("Nguyên văn ", "").strip()

            date = row.get("Ngày xuất bản", "").strip()
            issue = row.get("Số báo", "").strip()
            newspaper = row.get("Báo", "").strip()

            if not action and not original_recipe:
                continue

            # Create content for embedding/retrieval
            # We include all metadata in the text content so the LLM can easily cite it.
            text_content = (
                f"Hành động: {action}\n"
                f"Công thức gốc: {original_recipe}\n"
                f"Nguyên văn: {full_text}\n"
                f"Báo: {newspaper}\n"
                f"Số báo: {issue}\n"
                f"Ngày: {date}"
            )

            # Metadata for citation and display
            metadata = {
                "source": str(csv_path),
                "file_name": csv_path.name,
                "action": action,
                "original_recipe": original_recipe,
                "full_text": full_text,
                "date": date,
                "issue": issue,
                "newspaper": newspaper,
                "citation_label": (
                    f"{original_recipe} ({newspaper}, {date})"
                    if original_recipe
                    else "Unknown Recipe"
                ),
            }

            documents.append(Document(page_content=text_content, metadata=metadata))

    if not documents:
        raise ValueError(f"No documents were loaded from {csv_path}.")

    return documents


def unique_citations(docs: Sequence[Document]) -> List[str]:
    citations: List[str] = []
    for doc in docs:
        label = doc.metadata.get("citation_label")
        if not label:
            label = doc.metadata.get("original_recipe") or "Unknown Source"
        if label not in citations:
            citations.append(label)
    return citations


def format_docs(docs: Sequence[Document]) -> str:
    formatted: List[str] = []
    for doc in docs:
        # We just use the page_content which now contains all the info
        formatted.append(f"{doc.page_content}")
    return "\n\n".join(formatted) if formatted else "No supporting context retrieved."


def rerank_documents(
    question: str, docs: Sequence[Document], reranker: CrossEncoder, top_k: int
) -> List[Document]:
    if not docs:
        return []
    # Rerank based on the user's emotion (question) vs the action/recipe
    pairs = [[question, doc.page_content] for doc in docs]
    scores = reranker.predict(pairs)
    scored_docs = sorted(zip(scores, docs), key=lambda item: item[0], reverse=True)
    return [doc for _, doc in scored_docs[:top_k]]


class RagService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.settings.ensure_env()

        self.device = settings.device or self._default_device()
        LOGGER.info("Using device %s for embeddings and reranker", self.device)

        self.embeddings = HuggingFaceEmbeddings(
            model_name=settings.embedding_model,
            model_kwargs={"device": self.device},
            encode_kwargs={"device": self.device},
        )
        self.reranker = CrossEncoder(settings.rerank_model, device=self.device)

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            separators=["\n\n", "\n", " ", ""],
        )
        self.llm = ChatOpenAI(
            model=settings.chat_model, temperature=0.8
        )  # Slightly higher for more creativity

        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """
Bạn là một "Đầu bếp Thơ ca" (Poetry Chef). Mục tiêu của bạn là tạo ra một "công thức nấu ăn đầy chất thơ" để chuyển hóa gánh nặng trừu tượng của người dùng thành một điều gì đó đẹp đẽ.

Đầu vào:
- Cảm xúc trừu tượng (người dùng đang mang gánh nặng gì)
- Khối lượng (nó nặng bao nhiêu)

Ngữ cảnh:
- Bạn có quyền truy cập vào cơ sở dữ liệu các công thức nấu ăn và hành động nấu nướng thời xưa của Việt Nam (được cung cấp trong context).
- Ngữ cảnh bao gồm: "Hành động" (tóm tắt) và "Nguyên văn" (chi tiết đầy đủ).

Hướng dẫn:
1.  **Phân tích Gánh nặng**: Thừa nhận cảm xúc và khối lượng của nó.
2.  **Chọn Hành động**:
    -   Ưu tiên sử dụng thông tin từ phần **"Nguyên văn"** nếu có.
    -   Hãy tận dụng **tối đa các bước** trong "Nguyên văn" để chế biến cảm xúc (ví dụ: rửa, băm, trộn, gói, nấu...). Đừng chỉ dừng lại ở bước đầu tiên.
    -   TUYỆT ĐỐI KHÔNG bịa đặt thêm các bước nấu ăn (như luộc, xào, nêm nếm) nếu chúng không có trong ngữ cảnh.
3.  **Tạo Công thức**: Kết hợp các hành động này thành một công thức thơ ca.
    -   Hãy coi "Cảm xúc" là một nguyên liệu vật lý thực sự (như thịt, cá, rau).
    -   Mô tả trực tiếp hành động tác động lên "Cảm xúc" đó.
    -   **QUAN TRỌNG - ĐIỀU CẤM KỴ**:
        -   **KHÔNG dùng phép so sánh ví von** (CẤM dùng từ: "như là", "giống như", "tựa như", "như cách ta...").
        -   **KHÔNG giải thích ý nghĩa** (CẤM viết: "để quên đi gánh nặng", "để lòng nhẹ nhõm", "tượng trưng cho...").
        -   Chỉ tập trung vào hành động vật lý: "Rửa nỗi buồn", "Băm áp lực", "Kho nỗi đau". Đừng giải thích tại sao làm vậy.
    -   Chọn hình ảnh ẩn dụ **vật lý, cụ thể** phù hợp với hành động nấu nướng (lửa, nước, dao, thớt, cối đá...).
4.  **Giọng điệu**: Thơ mộng nhưng Tả thực (Descriptive), cô đọng, mang thẩm mỹ Việt Nam xưa.
5.  **Định dạng**:
    -   **Tên món**: [Tên danh từ, KHÔNG chứa tính từ]
    -   **Nguyên liệu**: [Cảm xúc] ([Khối lượng]), [Yếu tố vật chất cụ thể trong bếp] (ví dụ: lửa, nước, gia vị...)
    -   **Cách làm**: [Khối lượng] [Cảm xúc] [Các bước chi tiết từ Nguyên văn]... (Viết liền mạch, không phân tích).
    -   **Cách thưởng thức**: [Cách thưởng thức món ăn tinh thần này]
    -   **Dựa trên**: “[Tên công thức gốc]”. [Tên báo], số [Số báo], ngày [Ngày] (Dịch ngày sang tiếng Việt, ví dụ: May 10 -> 10 tháng 5).

QUAN TRỌNG:
-   Sử dụng **càng nhiều chi tiết từ Nguyên văn càng tốt**.
-   Dịch toàn bộ ngày tháng sang tiếng Việt.
-   Ngôn ngữ: Tiếng Việt.
""".strip(),
                ),
                (
                    "user",
                    "Context:\n{context}\n\nInput Emotion: {question}\nWeight: {additional_context}",
                ),
            ]
        )

        self._vectorstore: Optional[Chroma] = None

    def _default_device(self) -> str:
        if self.settings.device:
            return self.settings.device
        if torch is not None and torch.cuda.is_available():  # type: ignore[attr-defined]
            return "cuda"
        return "cpu"

    def has_persisted_index(self) -> bool:
        directory = self.settings.resolved_persist_dir
        return directory.exists() and any(directory.iterdir())

    def load_source_documents(self) -> List[Document]:
        return load_documents(self.settings.resolved_data_dir, (".csv",))

    def build_or_load_vectorstore(self, force_rebuild: bool = False) -> Chroma:
        if self._vectorstore is not None and not force_rebuild:
            return self._vectorstore

        persist_directory = str(self.settings.resolved_persist_dir)
        if not force_rebuild and self.has_persisted_index():
            LOGGER.info("Loading existing Chroma index from %s", persist_directory)
            self._vectorstore = Chroma(
                persist_directory=persist_directory,
                embedding_function=self.embeddings,
            )
            return self._vectorstore

        LOGGER.info("Building new Chroma index at %s", persist_directory)
        documents = self.load_source_documents()
        # For CSV rows which are short, we might not need to split, but it doesn't hurt.
        chunks = self.splitter.split_documents(documents)
        self._vectorstore = Chroma.from_documents(
            chunks,
            embedding=self.embeddings,
            persist_directory=persist_directory,
        )
        LOGGER.info(
            "Indexed %s chunks from %s source passages",
            len(chunks),
            len(documents),
        )
        return self._vectorstore

    def ensure_vectorstore(self, force_rebuild: bool = False) -> Chroma:
        return self.build_or_load_vectorstore(force_rebuild=force_rebuild)

    def ingest(self, force_rebuild: bool = False) -> None:
        self.ensure_vectorstore(force_rebuild=force_rebuild)

    def _build_source_payload(self, doc: Document) -> SourceChunk:
        label = doc.metadata.get("citation_label")
        if not label:
            label = doc.metadata.get("original_recipe") or "Unknown Source"

        # Format date to Vietnamese if present
        date_str = doc.metadata.get("date", "")
        if date_str:
            try:
                dt = datetime.strptime(date_str, "%B %d, %Y")
                formatted_date = f"{dt.day} tháng {dt.month}, {dt.year}"

                if date_str in label:
                    label = label.replace(date_str, formatted_date)
            except ValueError:
                pass

        # Also replace in text content for display
        # Use full_text from metadata if available, otherwise fall back to page_content
        text = doc.metadata.get("full_text") or doc.page_content

        if date_str:
            try:
                dt = datetime.strptime(date_str, "%B %d, %Y")
                formatted_date = f"{dt.day} tháng {dt.month}, {dt.year}"
                if date_str in text:
                    text = text.replace(date_str, formatted_date)
            except ValueError:
                pass

        return SourceChunk(
            label=label,
            page_number=None,  # Not applicable for CSV usually
            chapter=doc.metadata.get(
                "issue"
            ),  # Map issue to chapter? Or just leave blank
            book_title=doc.metadata.get("newspaper"),
            file_name=doc.metadata.get("file_name"),
            source_path=doc.metadata.get("source"),
            text=text,
            viewer_url=None,  # No viewer for CSV rows yet
        )

    def ask(
        self,
        *,
        question: str,
        additional_context: Optional[str] = None,
        top_k: Optional[int] = None,
        pool_size: Optional[int] = None,
        temperature: Optional[float] = None,
        rerank: bool = True,
    ) -> Dict[str, object]:
        vectorstore = self.ensure_vectorstore()
        k = pool_size or self.settings.retriever_k
        chosen_top_k = top_k or self.settings.rerank_top_k
        retriever = vectorstore.as_retriever(search_kwargs={"k": k})
        candidate_docs = retriever.invoke(question)
        if rerank:
            docs = rerank_documents(
                question, candidate_docs, self.reranker, chosen_top_k
            )
        else:
            docs = list(candidate_docs[:chosen_top_k])

        context_text = format_docs(docs)

        # We pass additional_context (Weight) as a separate variable to the prompt
        # The prompt template expects 'additional_context' key if we used it that way,
        # but here we are formatting it into the prompt variables.

        previous_temperature = self.llm.temperature
        if temperature is not None:
            self.llm.temperature = temperature
        try:
            # Note: The prompt template defined above uses {question} and {additional_context}
            response = self.llm.invoke(
                self.prompt.format_messages(
                    context=context_text,
                    question=question,
                    additional_context=additional_context or "Unknown Weight",
                )
            )
        finally:
            if temperature is not None:
                self.llm.temperature = previous_temperature

        answer = response.content.strip()
        citations = unique_citations(docs)
        sources = [self._build_source_payload(doc) for doc in docs]
        return {
            "answer": answer,
            "citations": citations,
            "sources": sources,
        }
