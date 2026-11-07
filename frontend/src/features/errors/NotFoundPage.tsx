import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <section className="mx-auto max-w-xl py-12 text-center">
      <p className="text-sm font-bold tracking-widest text-teal-700 uppercase">
        Ошибка 404
      </p>
      <h1 className="mt-3 text-4xl font-semibold tracking-tight text-slate-950">
        Страница не найдена
      </h1>
      <p className="mt-4 leading-7 text-slate-600">
        Возможно, адрес изменился или в ссылке есть опечатка.
      </p>
      <Link
        className="mt-7 inline-flex min-h-11 items-center rounded-xl bg-teal-700 px-4 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-800 focus-visible:outline-2"
        to="/"
      >
        Вернуться на главную
      </Link>
    </section>
  );
}
