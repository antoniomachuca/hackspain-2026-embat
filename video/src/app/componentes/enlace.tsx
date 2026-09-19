/**
 * Sustituto de next/link. En un vídeo no hay navegación, pero tiene que
 * seguir siendo un <a>: media hoja del CSS del front cuelga de selectores
 * como `.rail a .tip`, y con un <span> el raíl enseña sus tooltips.
 */
export default function Link(
  {href, children, ...r}: {href: string; children: React.ReactNode} & React.AnchorHTMLAttributes<HTMLAnchorElement>,
) {
  return (
    <a data-href={href} {...r}>
      {children}
    </a>
  );
}
