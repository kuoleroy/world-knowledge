import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  // @wk/types 为 TS 源码包，需 Next.js 一并转译
  transpilePackages: ["@wk/types"],
  reactCompiler: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
