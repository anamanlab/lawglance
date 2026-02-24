import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "IMMCAD",
  description: "Canada-focused immigration legal information assistant"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>): JSX.Element {
  return (
    <html lang="en-CA">
      <body>{children}</body>
    </html>
  );
}
