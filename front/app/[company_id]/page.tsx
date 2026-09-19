import { FichaEmpresa } from "@/components/ficha-empresa";

/** X-Ray como módulo de la propia empresa: se mira a sí misma. */
export default async function EmpresaPage({ params }: { params: Promise<{ company_id: string }> }) {
  const { company_id } = await params;
  return <FichaEmpresa id={company_id} vista="empresa" />;
}
