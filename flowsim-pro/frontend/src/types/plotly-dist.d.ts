declare module "plotly.js-dist-min" {
  import type { Data, Layout, Config } from "plotly.js";

  export function newPlot(
    root: HTMLElement,
    data: Data[],
    layout?: Partial<Layout>,
    config?: Partial<Config>
  ): Promise<void>;

  export function purge(root: HTMLElement): void;

  export namespace Plots {
    function resize(root: HTMLElement): void;
  }
}
