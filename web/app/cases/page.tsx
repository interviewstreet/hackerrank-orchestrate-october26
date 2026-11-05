import { Suspense } from "react";

import CasesTable from "./CasesTable";

export const metadata = { title: "Cases · TRACE" };

export default function CasesPage() {
  return (
    <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6 sm:py-14">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-ink sm:text-3xl">Cases</h1>
        <p className="mt-2 text-ink-2">Every deletion request, with what the shop reported and what TRACE found.</p>
      </header>
      {/* useSearchParams needs a Suspense boundary */}
      <Suspense fallback={<div className="h-96 animate-pulse rounded-xl bg-surface" />}>
        <CasesTable />
      </Suspense>
    </main>
  );
}
