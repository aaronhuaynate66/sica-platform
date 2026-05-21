import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

import { TopNav } from "@/components/site/top-nav";
import { DisclaimerBanner } from "@/components/site/disclaimer-banner";
import { ThemeProvider } from "@/components/site/theme-provider";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "SICA — Demo interna",
  description:
    "SICA · Sistema de Inteligencia Clínica Asistida. Demo interna sobre datos sintéticos.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" suppressHydrationWarning className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <body className="antialiased min-h-screen bg-background text-foreground flex flex-col">
        <ThemeProvider defaultTheme="dark">
          <TopNav />
          <main className="flex-1 flex flex-col">{children}</main>
          <DisclaimerBanner />
        </ThemeProvider>
      </body>
    </html>
  );
}
