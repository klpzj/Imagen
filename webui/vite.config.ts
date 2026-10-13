import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  // Relative asset URLs allow the built tool to live at /workshop/imagen/tool/
  // behind the PersonalStation BFF as well as at the standalone root.
  base: process.env.VITE_BASE_PATH ?? "./",
  server: {
    host: "127.0.0.1",
    port: 5173,
    allowedHosts: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:18000",
        changeOrigin: true
      },
      "/outputs": {
        target: "http://127.0.0.1:18000",
        changeOrigin: true
      }
    }
  }
});
