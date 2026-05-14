import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "hallucin8 — Brand Hallucination Monitor",
  description:
    "SGE Semantic Dominance & Brand Hallucination Monitor — track how AI models perceive your brand.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
