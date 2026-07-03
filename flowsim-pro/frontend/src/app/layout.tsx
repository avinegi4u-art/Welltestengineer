import type { Metadata } from "next";
import { ThemeProvider } from "@/lib/theme";
import Header from "@/components/Header";
import "./globals.css";

export const metadata: Metadata = {
  title: "FlowSim Pro — Multiphase Flow Simulator",
  description: "Steady-state multiphase flow simulation for wells, flowlines, and production networks",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen">
        <ThemeProvider>
          <Header />
          <main>{children}</main>
        </ThemeProvider>
      </body>
    </html>
  );
}
