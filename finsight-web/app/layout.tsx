import type { Metadata } from "next";
import Link from "next/link";
import { Landmark } from "lucide-react";
import ServerStatus from "@/components/ServerStatus";
import ThemeToggle from "@/components/ThemeToggle";
import "./globals.css";

export const metadata: Metadata = {
  title: "FinSight — Credit Underwriting Copilot",
  description: "AI credit memos and a research copilot grounded in SEC 10-K filings.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* Apply the saved theme before first paint so there's no flash. */}
        <script
          dangerouslySetInnerHTML={{
            __html: `try{var t=localStorage.getItem("finsight:theme");if(t)document.documentElement.dataset.theme=t}catch(e){}`,
          }}
        />
      </head>
      <body className="min-h-dvh antialiased">
        <header className="no-print sticky top-0 z-30 border-b border-line bg-bg/85 backdrop-blur">
          <div className="mx-auto flex h-14 max-w-[1920px] items-center justify-between gap-3 px-4">
            <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
              <span className="grid size-7 place-items-center rounded-md bg-accent text-white">
                <Landmark size={16} aria-hidden />
              </span>
              FinSight
              <span className="hidden text-sm font-normal text-muted sm:inline">Credit Underwriting Copilot</span>
            </Link>
            <div className="flex items-center gap-2">
              <ServerStatus />
              <ThemeToggle />
            </div>
          </div>
        </header>
        {children}
      </body>
    </html>
  );
}
