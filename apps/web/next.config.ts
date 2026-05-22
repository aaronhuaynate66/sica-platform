import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // En monorepo: apunta a la raíz para que Next.js trace correctamente las
  // dependencias hoisted en node_modules de la raíz. Sin esto, el tracer
  // puede emitir warnings sobre lockfile no encontrado.
  outputFileTracingRoot: path.join(process.cwd(), "../.."),
  reactStrictMode: true,
  // NOTA: `output: 'standalone'` se omite deliberadamente. En Vercel no
  // aporta (Vercel hace su propio bundling) y en Windows el build local
  // falla intentando crear symlinks que requieren permisos administrador.
  // Si en el futuro self-hosteamos en Cloud Run, agregarlo entonces.
};

export default nextConfig;
