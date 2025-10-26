"use client";

import { useState } from "react";
import { Sidebar } from "@/components/sidebar";
import { MobileHeader } from "@/components/mobile-header";
import { ChatPage } from "@/components/chat/chat-page";
import { InvoicesPage } from "@/components/invoices/invoices-page";

type TabKey = "chat" | "invoices";

export default function Page() {
  const [activeTab, setActiveTab] = useState<TabKey>("chat");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [pdfCount, setPdfCount] = useState<number>(0);
  const [selectedDocumentNumber, setSelectedDocumentNumber] = useState<
    number | null
  >(null);

  return (
    <main className="h-screen flex overflow-hidden bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
      {/* Sidebar */}
      <Sidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        activeTab={activeTab}
        onSelectTab={(t) => {
          setActiveTab(t);
          setSidebarOpen(false);
        }}
        pdfCount={pdfCount}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Mobile Header */}
        <MobileHeader onOpenMenu={() => setSidebarOpen(true)} />

        {activeTab === "chat" ? (
          <ChatPage onPdfCountChange={setPdfCount} />
        ) : (
          <InvoicesPage onPdfCountChange={setPdfCount} />
        )}
      </div>

      {/* Overlay for mobile sidebar */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-20 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </main>
  );
}
