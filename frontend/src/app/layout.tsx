import type { Metadata } from "next";
import "leaflet/dist/leaflet.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "TownWatch Civic Intelligence",
  description: "Conversational Municipal RAG & Zoning Line Visualizer",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      data-theme="1"
      suppressHydrationWarning
    >
      <body className="theme-1" suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
