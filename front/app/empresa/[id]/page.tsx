import { redirect } from "next/navigation";

export default async function Ficha({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  redirect(`/${id}`);
}
