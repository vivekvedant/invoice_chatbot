"use client";

import { User, Bot } from "lucide-react";

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
  isTyping?: boolean;
}

export function MessageBubble({
  role,
  content,
  isTyping = false,
}: MessageBubbleProps) {
  // At the start of the component
  if (!content && !isTyping) return null;
  
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`flex gap-3 max-w-3xl ${
          isUser ? "flex-row-reverse" : "flex-row"
        }`}
      >
        {/* Avatar */}
        <div
          className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
            isUser
              ? "bg-gradient-to-br from-blue-500 to-indigo-600"
              : "bg-gradient-to-br from-gray-600 to-gray-800"
          }`}
        >
          {isUser ? (
            <User className="w-5 h-5 text-white" />
          ) : (
            <Bot className="w-5 h-5 text-white" />
          )}
        </div>

        {/* Message */}
        <div
          className={`px-6 py-4 rounded-2xl shadow-md ${
            isUser
              ? "bg-gradient-to-br from-blue-500 to-indigo-600 text-white"
              : "bg-white text-gray-800 border border-gray-200"
          }`}
        >
          <p className="whitespace-pre-wrap break-words">
            {content}
            {isTyping && (
              <span className="inline-block w-1 h-5 bg-gray-800 ml-1 animate-pulse" />
            )}
          </p>
        </div>
      </div>
    </div>
  );
}
