import { Nav } from "@/components/nav";
import { Footer } from "@/components/footer";
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
      <Nav />
      <main style={{ flex: 1 }}>{children}</main>
      <Footer />
    </div>
  );
}
