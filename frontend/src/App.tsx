import { useState } from "react";
import { askQuestion } from "./client";
import type { AskRequest, AskResponse } from "./types";
import "./styles.css";

export default function App() {
  const [emotion, setEmotion] = useState("");
  const [weight, setWeight] = useState(5); // Default weight
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleTransmute = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!emotion.trim()) return;

    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const payload: AskRequest = {
        question: emotion,
        additional_context: `${weight} kg`,
        top_k: 1,
        pool_size: 5,
        rerank: true,
      };

      const res = await askQuestion(payload);
      setResponse(res);
    } catch (err) {
      console.error(err);
      setError("Có lỗi xảy ra. Vui lòng thử lại.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Main Container */}
      <div className="container">
        {/* Title Section */}
        <div className="title-section">
          <h1 className="main-title">Hầm cho rục, kho cho thắm</h1>
          <p className="subtitle">
            Chế biến những khối vô hình trong bạn qua các công thức nấu ăn trên
            Nữ Giới Chung (1918) và Phụ nữ Tân Văn (1929).
          </p>
        </div>

        {/* Form Container */}
        <div className="form-container">
          <form
            id="poem-form"
            aria-label="Form nấu món ăn"
            onSubmit={handleTransmute}
          >
            {/* Emotion Input */}
            <div className="form-group">
              <label htmlFor="emotion">Nguyên liệu cảm xúc cần chế biến</label>
              <input
                type="text"
                id="emotion"
                name="emotion"
                placeholder="khoai lang"
                aria-label="Nhập cảm xúc"
                required
                value={emotion}
                onChange={(e) => setEmotion(e.target.value)}
              />
            </div>

            {/* Weight Input */}
            <div className="form-group">
              <label htmlFor="weight">
                Sức nặng của nguyên liệu:{" "}
                <span className="weight-value">{weight} kg</span>
              </label>
              <div className="slider-container">
                <input
                  type="range"
                  id="weight"
                  name="weight"
                  min="0"
                  max="10"
                  step="1"
                  value={weight}
                  onChange={(e) => setWeight(Number(e.target.value))}
                  className="aesthetic-slider"
                />
                <div className="slider-labels">
                  {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((num) => (
                    <span key={num} className="slider-label">
                      {num}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              className="submit-btn"
              id="submit-btn"
              disabled={loading}
            >
              {loading ? (
                <span className="btn-loader">
                  <span className="spinner"></span> Đang tạo công thức...
                </span>
              ) : (
                <span className="btn-text">Tạo công thức</span>
              )}
            </button>
          </form>

          {/* Error Message */}
          {error && (
            <div id="error-message" className="error-message">
              {error}
            </div>
          )}
        </div>

        {/* Output Section */}
        {response && (
          <div id="output-section" className="output-section">
            <div className="poem-container">
              <h2 className="output-title">Món ăn của bạn</h2>
              <div id="output" className="poem-output">
                {response.answer
                  .split(/(\*\*.*?\*\*)/g)
                  .map((part, index) =>
                    part.startsWith("**") && part.endsWith("**") ? (
                      <strong key={index}>{part.slice(2, -2)}</strong>
                    ) : (
                      <span key={index}>{part}</span>
                    )
                  )}
              </div>
              <div className="poem-separator"></div>

              {/* Explanation Section - Adapted from citations/sources */}
              <div id="explanation-section" className="explanation-section">
                <h3 className="explanation-title">Công thức gốc</h3>
                <div id="explanation-content">
                  {response.sources && response.sources.length > 0 ? (
                    response.sources.map((source, index) => (
                      <div key={index} className="keyword-item">
                        <h4>{source.label}</h4>
                        <div className="keyword-detail">
                          <strong>Nguồn:</strong> {source.book_title}
                        </div>
                        <div className="keyword-detail">
                          <strong>Số báo:</strong> {source.chapter}
                        </div>
                        <div className="keyword-citation">{source.text}</div>
                      </div>
                    ))
                  ) : (
                    <p className="text-center">Không có thông tin tham khảo.</p>
                  )}
                </div>
              </div>

              {/* Print Button */}
              <button onClick={() => window.print()} className="print-btn">
                In công thức
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <footer className="footer">
        <div className="footer-copyright">
          Triển lãm Tao Ngộ & Cộng sự | 2025
        </div>
      </footer>
    </>
  );
}
