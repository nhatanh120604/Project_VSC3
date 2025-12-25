from __future__ import annotations

import csv
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from .schemas import SourceChunk
from .settings import Settings

LOGGER = logging.getLogger(__name__)

class ContentRow:
    """Represents a single row from the data.csv."""
    def __init__(self, row: Dict[str, str], source_path: Path):
        self.action = row.get("Động từ (Action)", "").strip()
        self.original_recipe = row.get("Công thức gốc (Original recipes)", "").strip()

        # Handle potential trailing space in CSV header for "Nguyên văn"
        self.full_text = row.get("Nguyên văn", "").strip()
        if not self.full_text:
            self.full_text = row.get("Nguyên văn ", "").strip()

        self.date = row.get("Ngày xuất bản", "").strip()
        self.issue = row.get("Số báo", "").strip()
        self.newspaper = row.get("Báo", "").strip()
        self.source_path = source_path

        self.citation_label = (
            f"{self.original_recipe} ({self.newspaper}, {self.date})"
            if self.original_recipe
            else "Unknown Recipe"
        )

    def to_text(self) -> str:
        return (
            f"Hành động: {self.action}\n"
            f"Công thức gốc: {self.original_recipe}\n"
            f"Nguyên văn: {self.full_text}\n"
            f"Báo: {self.newspaper}\n"
            f"Số báo: {self.issue}\n"
            f"Ngày: {self.date}"
        )

    def to_source_chunk(self) -> SourceChunk:
        text = self.full_text or self.to_text()

        # Format date to Vietnamese if present
        label = self.citation_label
        if self.date:
            dt = None
            for fmt in ("%B %d, %Y", "%b %d, %Y"):
                try:
                    dt = datetime.strptime(self.date, fmt)
                    break
                except ValueError:
                    continue

            if dt:
                formatted_date = f"{dt.day} tháng {dt.month}, {dt.year}"
                label = label.replace(self.date, formatted_date)
                text = text.replace(self.date, formatted_date)

        return SourceChunk(
            label=label,
            page_number=None,
            chapter=self.issue,
            book_title=self.newspaper,
            file_name=self.source_path.name,
            source_path=str(self.source_path),
            text=text,
            viewer_url=None,
        )

class PoetryChefService:
    """
    Service that provides 'poetry chef' responses by picking random historical
    Vietnamese cooking context.
    """
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.settings.ensure_env()

        self.llm = ChatOpenAI(
            model=settings.chat_model,
            temperature=0.8
        )

        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """
Bạn là một "Đầu bếp Thơ ca" (Poetry Chef). Mục tiêu duy nhất của bạn là chuyển hóa gánh nặng của người dùng bằng cách đặt chúng vào một công thức nấu ăn cổ xưa của Việt Nam.

Hướng dẫn quan trọng nhất:
1.  **Sao chép Nguyên văn**: Bạn phải sử dụng phần **"Nguyên văn"** trong ngữ cảnh để làm nội dung cho phần "Cách làm".
2.  **Sát sao từng từ (Word-for-word)**: Hãy giữ nguyên gần như toàn bộ câu chữ, cấu trúc câu, và phong cách ngôn ngữ cổ của "Nguyên văn". KHÔNG được tóm tắt, KHÔNG được viết lại bằng ngôn ngữ hiện đại, KHÔNG được bỏ bớt chi tiết.
3.  **Thay thế Nguyên liệu Chính**: Tìm danh từ chỉ nguyên liệu chính trong công thức (ví dụ: Cua biển, Cá lóc, Tôm, Thịt heo...) và thay thế ĐÚNG từ đó bằng **[Cảm xúc]** của người dùng.
    -   Ví dụ: Nếu gốc là "Cua biển lựa con nào cho thiệt chắc sẽ mua", hãy viết "[Cảm xúc] lựa con nào cho thiệt chắc sẽ mua".
    -   Giữ nguyên mọi nguyên liệu phụ (muối, mắm, nước, nấm, gia vị...), hành động (rửa, băm, hầm, kho...) và các từ nối (sẽ, đoạn, rồi, thiệt...).
4.  **Nguyên liệu Thi vị (Spontaneity)**: Để tạo sự bất ngờ và tăng tính thẩm mỹ, hãy chọn ngẫu nhiên **MỘT** "nguyên liệu thi vị giàu tính biểu tượng" (ví dụ: nước mưa, nước mắt, gió mùa đông, ánh trăng, tiếng thở dài, sương sớm, lời thề, kỷ niệm...) và khéo léo "trộn" nó vào một bước bất kỳ trong "Cách làm" mà không làm thay đổi cấu trúc câu gốc quá nhiều.
5.  **CẤM KỴ TUYỆT ĐỐI**:
    -   KHÔNG giải thích ý nghĩa tâm lý hay gán ghép ẩn dụ cho hành động nấu ăn.
    -   KHÔNG dùng phép so sánh (CẤM dùng: "như là", "giống như", "tựa như").
    -   Chỉ tập trung vào mô tả hành động vật lý tác động lên [Cảm xúc] y hệt như tác động lên thực phẩm trong bản gốc.

Định dạng đầu ra:
-   **Tên món**: [Giữ nguyên tên gốc, nhưng thay nguyên liệu tương ứng bằng Cảm xúc]
-   **Nguyên liệu**: [Cảm xúc] ([Khối lượng]), [Nguyên liệu thi vị], [Các nguyên liệu phụ liệt kê y hệt bản gốc]
-   **Cách làm**: [Chép lại toàn bộ "Nguyên văn", thay thế nguyên liệu chính bằng Cảm xúc và lồng ghép khéo léo Nguyên liệu bất ngờ vào].
-   **Cách thưởng thức**: [Viết 1 câu ngắn gọn nhưng đầy tính thi vị và cảm xúc về cách dùng món ăn này].
-   **Dựa trên**: “[Tên công thức gốc]”. [Tên báo], số [Số báo], ngày [Ngày] (Dịch sang tiếng Việt, ví dụ: May 10 -> 10 tháng 5).
""".strip(),
                ),
                (
                    "user",
                    "Context:\n{context}\n\nInput Emotion: {question}\nWeight: {additional_context}",
                ),
            ]
        )
        self._cache_data: List[ContentRow] = []

    def _load_data(self) -> List[ContentRow]:
        if self._cache_data:
            return self._cache_data

        csv_path = self.settings.resolved_data_dir / "data.csv"
        if not csv_path.exists():
            LOGGER.error(f"Data file not found at {csv_path}")
            return []

        rows: List[ContentRow] = []
        try:
            with open(csv_path, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not row.get("Động từ (Action)") and not row.get("Công thức gốc (Original recipes)"):
                        continue
                    rows.append(ContentRow(row, csv_path))
        except Exception as e:
            LOGGER.error(f"Error loading CSV data: {e}")

        self._cache_data = rows
        return rows

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
        """
        Picks a random context and generates a response.
        Args:
            question: The user's emotion/gánh nặng.
            additional_context: The weight of the emotion.
            temperature: LLM temperature.
            top_k, pool_size, rerank: Ignored in this simplified version.
        """
        data = self._load_data()
        if not data:
            return {
                "answer": "Xin lỗi, hiện tại tôi không có dữ liệu công thức để chế biến cảm xúc này.",
                "citations": [],
                "sources": []
            }

        # Pick one random row
        selected_row = random.choice(data)
        context_text = selected_row.to_text()

        # Update temperature if requested
        previous_temperature = self.llm.temperature
        if temperature is not None:
            self.llm.temperature = temperature

        try:
            response = self.llm.invoke(
                self.prompt.format_messages(
                    context=context_text,
                    question=question,
                    additional_context=additional_context or "không xác định",
                )
            )
        finally:
            self.llm.temperature = previous_temperature

        return {
            "answer": response.content.strip(),
            "citations": [selected_row.citation_label],
            "sources": [selected_row.to_source_chunk()],
        }

    def ensure_vectorstore(self, force_rebuild: bool = False) -> None:
        """Compatibility method for startup logic."""
        self._load_data()
