import Escenarios from "@/app/empresa/[id]/escenarios/page";

export default async function Page({ params }: { params: Promise<{ company_id: string }> }) {
  const { company_id } = await params;
  return <Escenarios params={Promise.resolve({ id: company_id })} />;
}
