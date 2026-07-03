"use client";

import { useEffect, useRef } from "react";
import type { Data, Layout, Config } from "plotly.js";

interface ChartProps {
  data: Data[];
  layout?: Partial<Layout>;
  config?: Partial<Config>;
  className?: string;
}

export default function Chart({ data, layout, config, className }: ChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    let mounted = true;

    const render = async () => {
      const Plotly = await import("plotly.js-dist-min");
      if (!mounted || !containerRef.current) return;

      const isDark = document.documentElement.classList.contains("dark");
      const defaultLayout: Partial<Layout> = {
        paper_bgcolor: "transparent",
        plot_bgcolor: "transparent",
        font: { color: isDark ? "#f1f5f9" : "#0f172a", size: 11 },
        margin: { t: 40, r: 20, b: 50, l: 60 },
        ...layout,
      };

      Plotly.newPlot(
        containerRef.current,
        data,
        defaultLayout,
        { responsive: true, displayModeBar: true, ...config }
      );
    };

    render();

    const handleResize = () => {
      if (containerRef.current) {
        import("plotly.js-dist-min").then((Plotly) => {
          Plotly.Plots.resize(containerRef.current!);
        });
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      mounted = false;
      window.removeEventListener("resize", handleResize);
      if (containerRef.current) {
        import("plotly.js-dist-min").then((Plotly) => {
          Plotly.purge(containerRef.current!);
        });
      }
    };
  }, [data, layout, config]);

  return <div ref={containerRef} className={className} style={{ width: "100%", height: "100%" }} />;
}
