import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <h1 className="text-4xl font-bold tracking-tight">404</h1>
      <p className="mt-2 text-muted-foreground">Page not found.</p>
      <Link href="/" className="mt-4 underline underline-offset-4 hover:text-primary">
        Return home
      </Link>
    </main>
  );
}
