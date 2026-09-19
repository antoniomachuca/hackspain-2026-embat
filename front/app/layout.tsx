import type { Metadata } from "next";
import "./globals.css";
import { Shell } from "@/components/shell";

export const metadata: Metadata = {
  title: "X Ray · Salud financiera",
  description: "Score de salud financiera con trayectoria, explicación y simulación. Reto de Embat, HackSpain 2026.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <head>
        <link rel="preconnect" href="https://api.fontshare.com" />
        <link href="https://api.fontshare.com/v2/css?f[]=general-sans@400,500&display=swap" rel="stylesheet" />
      </head>
      {/* Las extensiones del navegador inyectan atributos en <body> antes de
          que React hidrate (ColorZilla mete cz-shortcut-listen, Grammarly los
          suyos). No es un desajuste nuestro: se ignoran los de este nodo. */}
      <body suppressHydrationWarning><Shell>{children}</Shell></body>
    </html>
  );
}
