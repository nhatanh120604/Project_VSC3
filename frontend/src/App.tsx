import { useState } from "react";
import { askQuestion } from "./client";
import type { AskRequest, AskResponse } from "./types";

const DEFAULT_WEIGHT = 5;

export default function App() {
  const [view, setView] = useState<"input" | "output">("input");
  const [emotion, setEmotion] = useState("");
  const [weight, setWeight] = useState(DEFAULT_WEIGHT);
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // For output view
  const [sessionId] = useState(() => `CP-${Math.floor(Math.random() * 10000)}-X`);
  const [currentDate] = useState(() => new Date().toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }));

  const handleTransmute = async () => {
    if (!emotion.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const payload: AskRequest = {
        question: emotion,
        additional_context: `${weight} kg`,
        top_k: 1,
        pool_size: 5,
        rerank: true
      };

      const res = await askQuestion(payload);
      setResponse(res);
      setView("output");
    } catch (err) {
      console.error(err);
      setError("Failed to transmute. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleNewRecipe = () => {
    setEmotion("");
    setWeight(DEFAULT_WEIGHT);
    setResponse(null);
    setView("input");
  };

  if (view === "input") {
    return (
      <div className="min-h-screen flex flex-col font-display bg-background-light dark:bg-background-dark text-[#111418] dark:text-white overflow-x-hidden">
        <header className="flex items-center justify-between whitespace-nowrap border-b border-solid border-[#e2e8f0] dark:border-[#1e293b] px-6 lg:px-10 py-4 bg-background-light dark:bg-background-dark z-20 relative">
          <div className="flex items-center gap-4">
            <h2 className="text-[#111418] dark:text-white text-lg font-bold leading-tight tracking-[-0.015em]">Hầm cho rục, kho cho thắm</h2>
          </div>
        </header>

        <main className="relative flex-1 flex flex-col items-center justify-center p-4 lg:p-10">
            <div className="absolute inset-0 bg-grid-pattern opacity-[0.05] pointer-events-none z-0"></div>
            <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/5 rounded-full blur-[100px] pointer-events-none"></div>
            <div className="absolute bottom-1/4 right-1/4 w-64 h-64 bg-primary/10 rounded-full blur-[80px] pointer-events-none"></div>

            <div className="relative z-10 w-full max-w-[640px] flex flex-col gap-10 animate-fade-in-up">
                <div className="flex flex-col gap-2 text-center items-center">
                    <span className="text-primary text-xs font-bold uppercase tracking-wider">Thơ Ca Tập Thể</span>
                    <h1 className="text-3xl md:text-5xl font-bold leading-tight tracking-tight bg-gradient-to-br from-white to-[#bfdbfe] bg-clip-text text-transparent">
                        Chuyển hóa nỗi niềm
                    </h1>
                    <p className="text-[#64748b] dark:text-[#bfdbfe] text-base md:text-lg max-w-md mx-auto mt-2">
                        Nhập vào cảm xúc của bạn để tạo ra một công thức thơ độc đáo để giải tỏa.
                    </p>
                </div>

                <div className="bg-white/5 dark:bg-[#1e293b]/40 backdrop-blur-md border border-[#e2e8f0] dark:border-[#334155] rounded-3xl p-6 md:p-10 shadow-xl">
                    <div className="flex flex-col gap-4 mb-10">
                        <label className="flex flex-col gap-2" htmlFor="abstract-input">
                            <span className="text-[#111418] dark:text-white text-lg font-bold leading-normal flex items-center gap-2">
                                <span className="material-symbols-outlined text-primary text-xl">psychology</span>
                                Bạn muốn “chế biến” điều gì (cảm xúc, tâm trạng, một thứ khó thể gọi tên)?
                            </span>
                        </label>
                        <div className="relative group">
                            <textarea
                                className="form-input w-full resize-none overflow-hidden rounded-2xl bg-background-light dark:bg-[#020617] text-[#111418] dark:text-white placeholder:text-[#64748b] dark:placeholder:text-[#64748b] border border-[#cbd5e1] dark:border-[#334155] focus:border-primary focus:ring-1 focus:ring-primary min-h-[140px] p-5 text-lg font-medium leading-relaxed transition-all duration-300 group-hover:border-[#60a5fa]/50"
                                id="abstract-input"
                                placeholder="Ví dụ: sầu đời, cô đơn, uể oải không muốn làm gì..."
                                value={emotion}
                                onChange={(e) => setEmotion(e.target.value)}
                            ></textarea>

                        </div>
                    </div>

                    <div className="flex flex-col gap-6 mb-12">
                        <div className="flex items-center justify-between">
                            <label className="text-[#111418] dark:text-white text-lg font-bold leading-normal flex items-center gap-2" htmlFor="weight-slider">
                                <span className="material-symbols-outlined text-primary text-xl">scale</span>
                                Khối lượng của nó là bao nhiêu?
                            </label>
                            <span className="text-primary font-bold text-xl font-mono">{weight} kg</span>
                        </div>
                        <div className="relative w-full h-12 flex items-center px-2">
                            <input
                                className="w-full h-2 bg-[#e2e8f0] dark:bg-[#1e293b] rounded-lg appearance-none cursor-pointer z-10"
                                id="weight-slider"
                                type="range"
                                min="1"
                                max="10"
                                value={weight}
                                onChange={(e) => setWeight(parseInt(e.target.value))}
                            />
                            <div className="absolute bottom-0 left-0 right-0 flex justify-between px-2.5 pointer-events-none mt-2">
                                {[...Array(11)].map((_, i) => (
                                    <span key={i} className={`h-1 w-[1px] ${i % 5 === 0 ? 'bg-[#60a5fa]' : 'bg-[#60a5fa]/30'}`}></span>
                                ))}
                            </div>
                        </div>

                    </div>

                    <button
                        onClick={handleTransmute}
                        disabled={loading || !emotion.trim()}
                        className="group w-full relative flex items-center justify-center overflow-hidden rounded-full h-14 bg-primary hover:bg-[#3b82f6] text-[#0f172a] transition-all duration-300 shadow-[0_0_20px_rgba(96,165,250,0.3)] hover:shadow-[0_0_30px_rgba(96,165,250,0.5)] disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <span className="absolute inset-0 w-full h-full bg-gradient-to-r from-transparent via-white/20 to-transparent translate-x-[-100%] group-hover:animate-[shimmer_1.5s_infinite]"></span>
                        <span className="relative text-lg font-bold tracking-wide flex items-center gap-2">
                            {loading ? (
                                <>
                                    <span className="material-symbols-outlined animate-spin">progress_activity</span>
                                    Đang chế biến...
                                </>
                            ) : (
                                <>
                                    <span className="material-symbols-outlined">auto_fix_high</span>
                                    Chế biến thành Công thức
                                </>
                            )}
                        </span>
                    </button>
                    {error && <p className="text-red-500 text-center mt-4">Chế biến thất bại. Vui lòng thử lại.</p>}
                </div>

            </div>
        </main>
      </div>
    );
  }

  return (
    <div className="bg-background-light dark:bg-background-dark min-h-screen flex flex-col font-display transition-colors duration-200">
        <header className="flex items-center justify-between whitespace-nowrap border-b border-solid border-[#e2e8f0] dark:border-[#1e293b] px-6 lg:px-10 py-4 no-print relative z-10 bg-background-light dark:bg-background-dark">
            <div className="flex items-center gap-4 text-[#0f172a] dark:text-white">
                <h2 className="text-lg font-bold leading-tight tracking-[-0.015em]">Hầm cho rục, kho cho thắm</h2>
            </div>
            <button
                onClick={handleNewRecipe}
                className="flex min-w-[84px] cursor-pointer items-center justify-center overflow-hidden rounded-full h-10 px-6 bg-primary/10 hover:bg-primary/20 dark:bg-[#1e293b] dark:hover:bg-[#334155] text-[#0f172a] dark:text-primary transition-colors text-sm font-bold leading-normal tracking-[0.015em]"
            >
                <span className="material-symbols-outlined mr-2 text-lg">add</span>
                <span className="truncate">Công thức mới</span>
            </button>
        </header>

        <main className="flex-grow flex flex-col items-center justify-center p-6 sm:p-10 relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-full overflow-hidden -z-0 opacity-10 pointer-events-none no-print">
                <div className="absolute top-[-20%] right-[-10%] w-[600px] h-[600px] rounded-full bg-primary blur-[150px]"></div>
                <div className="absolute bottom-[-10%] left-[-10%] w-[400px] h-[400px] rounded-full bg-primary blur-[100px]"></div>
            </div>

            <div className="w-full max-w-[800px] flex flex-col items-center relative z-10">
                <div className="mb-8 no-print">
                    <h4 className="text-[#0f172a] dark:text-[#93c5fd] text-sm font-bold uppercase tracking-[0.15em] px-4 py-2 text-center border-b border-primary/30 pb-1">
                        Công thức giải tỏa của bạn
                    </h4>
                </div>

                <div className="w-full bg-white dark:bg-[#1e293b] rounded-lg border border-[#e2e8f0] dark:border-[#334155] shadow-xl overflow-hidden flex flex-col print-border">
                    <div className="bg-[#f8fafc] dark:bg-[#020617] px-8 py-4 border-b border-[#e2e8f0] dark:border-[#334155] flex justify-between items-center">
                        <div className="flex gap-2">
                            <div className="size-3 rounded-full bg-red-500/50"></div>
                            <div className="size-3 rounded-full bg-yellow-500/50"></div>
                            <div className="size-3 rounded-full bg-green-500/50"></div>
                        </div>
                    </div>

                    <div className="p-8 sm:p-12 flex flex-col items-center text-center">
                        {/*
                            Parsing the response to find a title if possible, otherwise generic.
                            The backend returns a full text, we might want to display it nicely.
                            For now, we display the full answer in the typewriter section.
                        */}
                        <h1 className="text-[#0f172a] dark:text-white tracking-tight text-5xl sm:text-[64px] font-extrabold leading-none mb-6">
                            CÔNG THỨC
                        </h1>

                        <div className="flex flex-wrap gap-3 justify-center mb-10 w-full">
                            <div className="flex h-8 shrink-0 items-center justify-center gap-x-2 rounded-full border border-[#e2e8f0] dark:border-[#334155] bg-transparent pl-4 pr-4">
                                <span className="material-symbols-outlined text-sm text-[#0f172a] dark:text-primary">scale</span>
                                <p className="text-[#0f172a] dark:text-white text-sm font-medium leading-normal">{weight}kg</p>
                            </div>
                            <div className="flex h-8 shrink-0 items-center justify-center gap-x-2 rounded-full border border-primary dark:border-primary/50 bg-primary/10 pl-4 pr-4">
                                <span className="material-symbols-outlined text-sm text-[#0f172a] dark:text-primary">psychology</span>
                                <p className="text-[#0f172a] dark:text-primary text-sm font-bold leading-normal uppercase truncate max-w-[200px]">
                                    {emotion}
                                </p>
                            </div>
                            <div className="flex h-8 shrink-0 items-center justify-center gap-x-2 rounded-full border border-[#e2e8f0] dark:border-[#334155] bg-transparent pl-4 pr-4">
                                <span className="material-symbols-outlined text-sm text-[#0f172a] dark:text-primary">schedule</span>
                                <p className="text-[#0f172a] dark:text-white text-sm font-medium leading-normal">{currentDate}</p>
                            </div>
                        </div>

                        <div className="w-16 h-1 bg-primary rounded-full mb-10"></div>

                        <div className="max-w-xl text-left sm:text-center">
                            <div className="text-[#334155] dark:text-[#cbd5e1] text-lg sm:text-xl font-light leading-relaxed typewriter-text whitespace-pre-wrap">
                                {response?.answer.split(/(\*\*.*?\*\*)/).map((part, i) =>
                                    part.startsWith('**') && part.endsWith('**')
                                        ? <strong key={i} className="font-bold text-[#0f172a] dark:text-white">{part.slice(2, -2)}</strong>
                                        : part
                                )}
                            </div>
                        </div>


                    </div>
                </div>

                <div className="mt-8 flex flex-col sm:flex-row gap-4 w-full justify-center items-center no-print">
                    <button
                        className="group flex min-w-[200px] cursor-pointer items-center justify-center rounded-full h-14 px-8 bg-primary hover:bg-[#3b82f6] text-[#0f172a] text-base font-bold leading-normal tracking-[0.015em] transition-all shadow-[0_0_20px_rgba(96,165,250,0.3)] hover:shadow-[0_0_30px_rgba(96,165,250,0.5)]"
                        onClick={() => window.print()}
                    >
                        <span className="material-symbols-outlined mr-2 group-hover:animate-bounce">print</span>
                        <span> In Công Thức</span>
                    </button>
                </div>
            </div>
        </main>

        <footer className="w-full py-6 text-center text-gray-400 dark:text-gray-600 text-sm no-print">
            <p>Hầm cho rục, kho cho thắm © 2025</p>
        </footer>
    </div>
  );
}
