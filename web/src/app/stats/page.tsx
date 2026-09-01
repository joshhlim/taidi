"use client";

import { useRouter } from "next/navigation";

export default function StatsPage() {
  const router = useRouter();

  return (
    <main className="flex-1 flex items-center justify-center px-6 py-12">
      <div className="w-full max-w-sm text-center space-y-4">
        <div className="flex items-center gap-3 mb-6">
          <button
            onClick={() => router.push("/")}
            data-testid="back-btn"
            className="h-11 w-11 rounded-full border border-border flex items-center justify-center text-lg font-bold text-brand"
          >
            ←
          </button>
          <h1 className="text-lg font-extrabold text-brand">My Stats</h1>
        </div>
        <p data-testid="not-available" className="text-sm text-muted">
          Feature not available yet.
        </p>
      </div>
    </main>
  );
}
