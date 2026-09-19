/** Isotipo de Embat, tomado de su favicon.svg oficial (viewBox 156). */
export function Isotipo({ size = 20, color = "#fff", ...r }: { size?: number; color?: string } & React.SVGProps<SVGSVGElement>) {
  return (
    <svg width={size} height={size} viewBox="30 27 96 101" fill="none" aria-hidden {...r}>
      <path d="M30 108.71L89.3674 128L52.6764 77.4977L30 108.71Z" fill={color} />
      <path d="M30 46.2897L52.6764 77.4978L89.3674 27L30 46.2897Z" fill={color} />
      <path d="M89.3677 27V128L126.054 77.4978L89.3677 27Z" fill={color} />
    </svg>
  );
}
