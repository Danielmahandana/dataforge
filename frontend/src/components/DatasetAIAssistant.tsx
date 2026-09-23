import React, { useState, useEffect } from 'react';
import { apiClient } from '../services/api';
import { Sparkles, Send, Bot, FileText } from 'lucide-react';

interface DatasetAIAssistantProps {
  datasetId: string;
  datasetName: string;
}

export const DatasetAIAssistant: React.FC<DatasetAIAssistantProps> = ({ datasetId, datasetName }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [summarizing, setSummarizing] = useState(false);
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'assistant'; text: string }>>([]);
  const [status, setStatus] = useState<any>(null);
  const [summary, setSummary] = useState<string | null>(null);

  useEffect(() => {
    apiClient.getLLMStatus().then(setStatus).catch(console.error);
  }, []);

  const handleSend = async () => {
    if (!query.trim() || loading) return;

    const userText = query.trim();
    setQuery('');
    setMessages((prev) => [...prev, { role: 'user', text: userText }]);
    setLoading(true);

    try {
      const res = await apiClient.queryDatasetWithLLM(datasetId, userText);
      setMessages((prev) => [...prev, { role: 'assistant', text: res.answer }]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', text: 'Sorry, failed to get AI response: ' + (err.message || 'Error occurred') },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSummarize = async () => {
    setSummarizing(true);
    try {
      const res = await apiClient.summarizeDatasetWithLLM(datasetId);
      setSummary(res.summary);
    } catch (err: any) {
      setSummary('Failed to generate summary.');
    } finally {
      setSummarizing(false);
    }
  };

  return (
    <div className="mt-4 border-t border-zinc-800/80 pt-4">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-4 py-2 bg-zinc-900 hover:bg-zinc-800 border border-zinc-700/80 text-amber-400 rounded-xl text-xs font-semibold transition-all shadow-sm"
      >
        <Sparkles className="w-4 h-4 text-amber-400" />
        {isOpen ? 'Close AI Assistant' : 'Ask DataForge AI Assistant'}
      </button>

      {isOpen && (
        <div className="mt-4 p-5 bg-[#121215] border border-zinc-800 rounded-2xl shadow-xl">
          {/* Header & Status Badge */}
          <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-zinc-800">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-zinc-900 border border-zinc-800 flex items-center justify-center">
                <Bot className="w-4 h-4 text-emerald-400" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-zinc-100">Dataset AI Assistant</h3>
                <p className="text-xs text-zinc-400">Contextual Q&A engine for {datasetName}</p>
              </div>
            </div>

            {status && (
              <div className="flex items-center gap-2 text-xs bg-zinc-900 px-3 py-1.5 rounded-full border border-zinc-800">
                <span className={`w-2 h-2 rounded-full ${status.configured ? 'bg-emerald-400' : 'bg-amber-400'}`} />
                <span className="text-zinc-300 capitalize">{status.active_provider} ({status.active_model})</span>
              </div>
            )}
          </div>

          {/* Quick Actions */}
          <div className="py-3 flex flex-wrap gap-2">
            <button
              onClick={handleSummarize}
              disabled={summarizing}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 text-xs rounded-lg border border-zinc-800 transition"
            >
              <FileText className="w-3.5 h-3.5 text-amber-400" />
              {summarizing ? 'Generating Executive Summary...' : 'Generate Executive Summary'}
            </button>
          </div>

          {/* Summary Box */}
          {summary && (
            <div className="mb-4 p-4 bg-zinc-900/90 border border-amber-500/30 rounded-xl text-xs text-zinc-200">
              <div className="font-semibold mb-1 text-amber-400 flex items-center gap-1.5">
                <Sparkles className="w-4 h-4" /> Executive Summary
              </div>
              <p className="whitespace-pre-wrap leading-relaxed text-zinc-300">{summary}</p>
            </div>
          )}

          {/* Chat Window */}
          <div className="h-64 overflow-y-auto space-y-3 p-4 bg-[#09090b] border border-zinc-800 rounded-xl mb-4">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center text-zinc-500 text-xs">
                <Bot className="w-7 h-7 mb-2 opacity-50 text-emerald-400" />
                <p>Ask any question about this dataset (e.g. "List qualifications offered in GP", "How many NQF level 5 items exist?")</p>
              </div>
            ) : (
              messages.map((m, idx) => (
                <div key={idx} className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
                  <div
                    className={`max-w-[85%] text-xs p-3 rounded-xl leading-relaxed ${
                      m.role === 'user'
                        ? 'bg-emerald-950/40 text-emerald-100 border border-emerald-800/40 rounded-br-none'
                        : 'bg-zinc-900 text-zinc-200 border border-zinc-800 rounded-bl-none'
                    }`}
                  >
                    {m.text}
                  </div>
                </div>
              ))
            )}

            {loading && (
              <div className="flex items-center gap-2 text-xs text-amber-400/80 animate-pulse">
                <Sparkles className="w-4 h-4" /> Groq AI is analyzing dataset records...
              </div>
            )}
          </div>

          {/* Input Row */}
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Ask a question about dataset records..."
              className="flex-1 bg-[#09090b] border border-zinc-800 rounded-xl px-4 py-2 text-xs text-zinc-100 focus:outline-none focus:border-amber-400"
            />
            <button
              onClick={handleSend}
              disabled={loading || !query.trim()}
              className="p-2.5 bg-amber-400 hover:bg-amber-300 text-black font-semibold rounded-xl text-xs disabled:opacity-50 transition"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
