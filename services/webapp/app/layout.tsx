import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Biomed Pi5",
  description: "Sistema de monitoreo biométrico",
  manifest: "/manifest.json",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es">
      <head>
        <link rel="icon" href="/favicon.ico" />
        <link rel="apple-touch-icon" href="/icon-192.png" />
        <meta name="theme-color" content="#2A9080" />
      </head>
      <body>{children}</body>
    </html>
  );
}
