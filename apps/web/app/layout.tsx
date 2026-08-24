import type { Metadata } from "next";

import { Sidebar } from "@/components/layout/sidebar";
import { QueryProvider } from "@/lib/query-provider";

import "./globals.css";

export const metadata: Metadata = {
  title: "AgentQ - Enterprise Agent Engineering Platform",
  description: "Build, test, secure, deploy, observe, and optimize AI agents.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="h-screen overflow-hidden antialiased">
        <QueryProvider>
          <div className="flex h-full">
            <Sidebar />
            <main className="flex-1 overflow-hidden">{children}</main>
          </div>
        </QueryProvider>
      </body>
    </html>
  );
}
