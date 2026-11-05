import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TRACE: Ghost Data Audit",
  description: "Deletion-audit results: which deletion requests were really completed.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
