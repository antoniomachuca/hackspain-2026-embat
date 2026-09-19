import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // En desarrollo se entra tanto por localhost como por 127.0.0.1 y por la IP
  // de la red; sin esto Next bloquea sus recursos y la página no hidrata.
  allowedDevOrigins: ["127.0.0.1", "localhost", "192.168.1.46"],
};

export default nextConfig;
