"use client";

import { Moon, Sun, Droplets } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTheme } from "@/lib/theme";
import clsx from "clsx";

const NAV = [
  { href: "/", label: "Dashboard" },
  { href: "/editor", label: "Case Editor" },
  { href: "/results", label: "Results" },
];

export default function Header() {
  const pathname = usePathname();
  const { theme, toggleTheme } = useTheme();

  return (
    <header className="h-14 border-b border-border-light dark:border-border-dark bg-panel-light dark:bg-panel-dark flex items-center px-4 gap-6">
      <Link href="/" className="flex items-center gap-2 font-semibold text-lg">
        <Droplets className="w-6 h-6 text-primary" />
        <span>FlowSim Pro</span>
      </Link>
      <nav className="flex gap-1">
        {NAV.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={clsx(
              "px-3 py-1.5 text-sm rounded-md transition",
              pathname === item.href
                ? "bg-primary text-white"
                : "hover:bg-slate-100 dark:hover:bg-slate-700"
            )}
          >
            {item.label}
          </Link>
        ))}
      </nav>
      <div className="ml-auto">
        <button onClick={toggleTheme} className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700" aria-label="Toggle theme">
          {theme === "light" ? <Moon className="w-5 h-5" /> : <Sun className="w-5 h-5" />}
        </button>
      </div>
    </header>
  );
}
