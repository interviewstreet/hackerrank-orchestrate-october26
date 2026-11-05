import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The API routes read web/data/*.json with fs at request time. Next.js
  // cannot see those reads, so list the files explicitly; otherwise Vercel
  // deploys the functions without the data.
  outputFileTracingIncludes: {
    "/api/**": ["./data/**/*.json"],
  },
  // Don't let `next dev` write web/AGENTS.md: the repo-root AGENTS.md is the
  // single source of truth for coding agents in this repo.
  agentRules: false,
};

export default nextConfig;
