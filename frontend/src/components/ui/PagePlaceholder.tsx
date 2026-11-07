interface PagePlaceholderProps {
  eyebrow: string;
  title: string;
  description: string;
}

export function PagePlaceholder({
  eyebrow,
  title,
  description,
}: PagePlaceholderProps) {
  return (
    <section className="max-w-2xl">
      <p className="text-sm font-semibold text-teal-700">{eyebrow}</p>
      <h1 className="mt-2 text-4xl font-semibold tracking-tight text-slate-950">
        {title}
      </h1>
      <p className="mt-4 text-lg leading-8 text-slate-600">{description}</p>
    </section>
  );
}
