import { FichaEmpresa } from "@/components/ficha-empresa";

/** La misma ficha, leída desde Embat: un cliente de su cartera. */
export default async function ClientePage({ params }: { params: Promise<{ company_id: string }> }) {
  const { company_id } = await params;
  return <FichaEmpresa id={company_id} vista="embat" />;
}
