import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactCompiler: true,
  devIndicators: false,
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
