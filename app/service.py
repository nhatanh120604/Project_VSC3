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
    -   **Nguyên tắc Vàng**: Chỉ thay thế **nguyên liệu chính** (thịt, cá, rau...) của công thức gốc bằng **[Cảm xúc]**.
    -   **Các nguyên liệu phụ** (nước, muối, lửa, than, gia vị...): Giữ nguyên là vật chất vật lý. **TUYỆT ĐỐI KHÔNG** biến chúng thành ẩn dụ (Ví dụ: CẤM viết "muối của niềm vui", "nước của sự quên lãng", "lửa của đam mê"). Chỉ viết "muối", "nước", "lửa".
    -   Mô tả trực tiếp hành động tác động lên "Cảm xúc" đó.
    -   **QUAN TRỌNG - ĐIỀU CẤM KỴ**:
        -   **KHÔNG dùng phép so sánh ví von** (CẤM dùng từ: "như là", "giống như", "tựa như", "như cách ta...").
        -   **KHÔNG giải thích ý nghĩa** (CẤM viết: "để quên đi gánh nặng", "để lòng nhẹ nhõm", "tượng trưng cho...").
        -   **KHÔNG thêm thắt tính từ hoa mỹ**: Nếu gốc là "rửa nước lạnh", chỉ viết "rửa nước lạnh", không viết "rửa dòng nước lạnh thanh tẩy".
        -   Chỉ tập trung vào hành động vật lý: "Rửa nỗi buồn", "Băm áp lực", "Kho nỗi đau". Đừng giải thích tại sao làm vậy.
4.  **Giọng điệu**: Thơ mộng nhưng Tả thực (Descriptive), cô đọng, mang thẩm mỹ Việt Nam xưa.
5.  **Định dạng**:
    -   **Tên món**: [Tên danh từ, KHÔNG chứa tính từ]
    -   **Nguyên liệu**: [Cảm xúc] ([Khối lượng]), [Các nguyên liệu phụ giữ nguyên từ gốc]
    -   **Cách làm**: [Khối lượng] [Cảm xúc] [Các bước chi tiết từ Nguyên văn, thay thế nguyên liệu chính bằng Cảm xúc, giữ nguyên nguyên liệu phụ]... (Viết liền mạch, không phân tích).
    -   **Cách thưởng thức**: [Cách thưởng thức món ăn cảm xúc này]
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
