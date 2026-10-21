import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "DeployPilot AI · Workflow operations",
  description:
    "Configure, deploy, evaluate and monitor policy-bound enterprise AI workflows.",
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
