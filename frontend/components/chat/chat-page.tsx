"use client";
import { useEffect, useState } from "react";
import { Loader2, Send, Brain, Trash2 } from "lucide-react";
import { API_BASE_URL } from "@/lib/config";
import { MessageBubble } from "./message-bubble";
import useSWR from "swr";
import { usePdfFiles } from "@/hooks/use-pdf-files";

type ChatMessage = { role: "user" | "assistant"; content: string };
type HistoryMessage = { type: "human" | "ai"; content: string; id: string };

export function ChatPage({
  onPdfCountChange,
}: {
  onPdfCountChange?: (count: number) => void;
}) {
  const { pdfs, isLoading, mutate } = usePdfFiles();

  // keep sidebar count in sync
  if (onPdfCountChange) {
    Promise.resolve().then(() => onPdfCountChange(pdfs.length));
  }

  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [userInput, setUserInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);

  // Load chat history from API on mount
  useEffect(() => {
    async function loadChatHistory() {
      try {
        const res = await fetch(`${API_BASE_URL}/chat_history`);
        if (!res.ok) throw new Error("Failed to load chat history");

        const history: HistoryMessage[] = await res.json();

        // Convert API format to chat messages
        const messages: ChatMessage[] = history.map((msg) => ({
          role: msg.type === "human" ? "user" : "assistant",
          content: msg.content,
        }));

        setChatMessages(messages);
      } catch (err) {
        console.warn("Failed to load chat history", err);
      } finally {
        setHistoryLoading(false);
      }
    }

    loadChatHistory();
  }, []);

  async function sendMessage() {
    if (!userInput.trim() || chatLoading) return;
    const text = userInput;
    setUserInput("");
    const userMessage: ChatMessage = { role: "user", content: text };

    setChatMessages((prev) => [
      ...prev,
      userMessage,
      { role: "assistant", content: "" },
    ]);
    setChatLoading(true);

    try {
      const res = await fetch(`${API_BASE_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_input: text }),
      });
      if (!res.ok) throw new Error("Failed to get response");

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) throw new Error("No reader available");

      let accumulatedContent = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        accumulatedContent += chunk;

        setChatMessages((prev) => {
          if (prev.length === 0) return prev;
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: "assistant",
            content: accumulatedContent,
          };
          return updated;
        });
      }
    } catch (err: any) {
      setChatMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Error: ${err?.message || "Unknown error"}`,
        },
      ]);
    } finally {
      setChatLoading(false);
    }
  }

  async function clearChat() {
    try {
      const res = await fetch(`${API_BASE_URL}/clear_history`, {
        method: "POST",
      });
      if (!res.ok) throw new Error("Failed to clear chat history");
      setChatMessages([]);
    } catch (err) {
      console.error("Failed to clear chat history", err);
    }
  }

  return (
    <section
      className="flex-1 flex flex-col h-full bg-white"
      aria-label="Chat and analysis"
    >
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-gradient-to-b from-blue-50/30 to-white pt-8 relative">
        {historyLoading ? (
          <div className="h-full flex items-center justify-center">
            <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
          </div>
        ) : chatMessages.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <div className="w-24 h-24 mx-auto mb-6 rounded-full bg-gradient-to-br from-blue-400 to-indigo-500 flex items-center justify-center">
                <Brain className="w-12 h-12 text-white" />
              </div>
              <p className="text-gray-600 text-xl font-medium mb-2">
                Ready to assist you
              </p>
              <p className="text-gray-500">
                Start a conversation about your invoices
              </p>
            </div>
          </div>
        ) : (
          chatMessages.map((msg, idx) => (
            <MessageBubble key={idx} role={msg.role} content={msg.content} />
          ))
        )}
        {chatLoading && (
          <MessageBubble
            role="assistant"
            content="Thinking..."
            isTyping={false}
          />
        )}
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 p-6 bg-white shadow-lg">
        <div className="max-w-4xl mx-auto flex gap-3 items-center">
          <input
            type="text"
            value={userInput}
            onChange={(e) => setUserInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
            placeholder="Ask about totals, dates, vendors..."
            className="flex-1 px-6 py-4 bg-gray-50 text-gray-800 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 border border-gray-200 text-lg"
            disabled={chatLoading}
            aria-label="Chat input"
          />
          {chatMessages.length > 0 && (
            <button
              onClick={clearChat}
              className="px-4 py-4 text-sm font-medium text-red-600 hover:text-red-700 bg-white hover:bg-red-50 rounded-xl transition-all border border-gray-200 hover:border-red-300 flex items-center gap-2"
              aria-label="Clear chat"
              title="Clear Chat"
            >
              <Trash2 className="w-4 h-4" />
              Clear Chat
            </button>
          )}
          <button
            onClick={sendMessage}
            disabled={chatLoading || !userInput.trim()}
            className="px-8 py-4 bg-gradient-to-r from-blue-500 to-indigo-600 text-white rounded-xl hover:from-blue-600 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg hover:shadow-xl flex items-center gap-2 font-semibold"
            aria-label="Send message"
          >
            <Send className="w-5 h-5" />
            Send
          </button>
        </div>
      </div>
    </section>
  );
}
