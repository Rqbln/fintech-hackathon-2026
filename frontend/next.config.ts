import type { NextConfig } from "next";

const backendApiBase = process.env.BACKEND_API_BASE || "http://localhost:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendApiBase}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
