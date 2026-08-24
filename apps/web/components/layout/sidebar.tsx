"use client";

import {
  BookOpen,
  Cpu,
  Gauge,
  GitBranch,
  Layers,
  ListChecks,
  Server,
  Settings,
  Workflow,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Dashboard", icon: Gauge },
  { href: "/flows", label: "Flows", icon: Workflow },
  { href: "/runs", label: "Runs", icon: GitBranch },
  { href: "/evaluations", label: "Evaluations", icon: ListChecks },
  { href: "/knowledge", label: "Knowledge", icon: BookOpen },
  { href: "/mcp-servers", label: "MCP Servers", icon: Server },
  { href: "/models", label: "Models", icon: Cpu },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="flex h-full w-56 shrink-0 flex-col border-r border-border bg-surface">
      <div className="flex items-center gap-2 px-4 py-4">
        <div className="flex h-7 w-7 items-center justify-center rounded-md bg-accent text-accent-ink">
          <Layers size={16} />
        </div>
        <span className="text-sm font-semibold tracking-tight text-ink">AgentQ</span>
      </div>
      <nav className="flex-1 space-y-0.5 px-2">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm",
                "transition-[color,background-color,transform] duration-150 ease-out active:scale-[0.97]",
                active
                  ? "bg-accent/10 text-accent font-medium"
                  : "text-ink-muted hover:bg-accent/5 hover:text-accent"
              )}
            >
              <Icon size={15} />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-border px-4 py-3 text-[11px] text-ink-faint">
        Default Workspace · dev mode
      </div>
    </aside>
  );
}
