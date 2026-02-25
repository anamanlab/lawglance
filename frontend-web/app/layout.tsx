import type { Metadata } from "next";
import Script from "next/script";
import { Lora, Poppins } from "next/font/google";
import "./globals.css";

const headingFont = Poppins({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  display: "swap",
  variable: "--font-heading",
});

const bodyFont = Lora({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
  variable: "--font-body",
});

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
    <html lang="en-CA" suppressHydrationWarning>
      <body
        className={`${headingFont.variable} ${bodyFont.variable} antialiased`}
        suppressHydrationWarning
      >
        <Script id="strip-bis-skin-checked" strategy="beforeInteractive">
          {`
            (() => {
              const strip = () => {
                document
                  .querySelectorAll('[bis_skin_checked]')
                  .forEach((node) => node.removeAttribute('bis_skin_checked'));
              };

              strip();
              const observer = new MutationObserver((mutations) => {
                for (const mutation of mutations) {
                  if (
                    mutation.type === 'attributes' &&
                    mutation.attributeName === 'bis_skin_checked' &&
                    mutation.target instanceof Element
                  ) {
                    mutation.target.removeAttribute('bis_skin_checked');
                  }
                }
                strip();
              });

              observer.observe(document.documentElement, {
                subtree: true,
                childList: true,
                attributes: true,
                attributeFilter: ['bis_skin_checked'],
              });
            })();
          `}
        </Script>
        {children}
      </body>
    </html>
  );
}
