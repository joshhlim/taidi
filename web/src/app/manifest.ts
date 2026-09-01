import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "GamBROle",
    short_name: "GamBROle",
    description: "Live score keeping for game night — Taidi, mahjong, poker",
    start_url: "/",
    display: "standalone",
    background_color: "#F7F5F0",
    theme_color: "#1E3A2F",
    icons: [{ src: "/icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" }],
  };
}
