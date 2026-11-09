import { Button } from "../../components/ui/Button";

export function UnexpectedErrorPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-stone-50 px-5 py-12">
      <section className="max-w-xl rounded-3xl border border-stone-200 bg-white p-8 text-center shadow-sm">
        <p className="text-sm font-bold tracking-widest text-rose-700 uppercase">
          Непредвиденная ошибка
        </p>
        <h1 className="mt-3 text-3xl font-semibold text-slate-950">
          Интерфейс не смог продолжить работу
        </h1>
        <p className="mt-4 leading-7 text-slate-600">
          Обновите страницу. Если ошибка повторяется, проверьте консоль разработки
          и состояние сервера.
        </p>
        <Button className="mt-7" onClick={() => window.location.reload()}>
          Обновить страницу
        </Button>
      </section>
    </main>
  );
}
