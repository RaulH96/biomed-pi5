import type { NextConfig } from "next";
import os from "os";

// En modo desarrollo Next bloquea sus recursos internos (JS, HMR, fuentes) para
// cualquier host que no esté en allowedDevOrigins: abrir la PWA por IP la dejaba
// sin hidratar ("Cargando..."). Se agregan las IPv4 que tenga la Pi al arrancar,
// así funciona aunque el router le cambie la IP.
const localIPs = Object.values(os.networkInterfaces())
  .flat()
  .filter((i): i is os.NetworkInterfaceInfo => !!i && i.family === "IPv4" && !i.internal)
  .map((i) => i.address);

const nextConfig: NextConfig = {
  allowedDevOrigins: ["harlink.local", "*.local", ...localIPs],

  // La API (FastAPI en :8000) se sirve a través de Next bajo /backend.
  // El navegador solo habla con el mismo origen de la página, así que funciona
  // por HTTP o HTTPS (sin bloqueo de "mixed content"), por harlink.local o por IP,
  // y sin depender de NEXT_PUBLIC_API_URL ni de .env.local.
  async rewrites() {
    return [
      { source: "/backend/:path*", destination: "http://127.0.0.1:8000/:path*" },
    ];
  },
};

export default nextConfig;
