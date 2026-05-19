import { Nav } from "@/components/nav";
import { Footer } from "@/components/footer";
import { DemoInit } from "@/components/demo-init";
import { brandTokens } from "@/lib/brand-tokens";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        backgroundColor: brandTokens.colors.light,
      }}
    >
      <DemoInit />
      <Nav />
      <main style={{ flex: 1 }}>{children}</main>
      <Footer />
    </div>
  );
}
