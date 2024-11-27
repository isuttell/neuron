import { useRouteError } from "react-router-dom";

export default function ErrorPage() {
  const error: Error | any = useRouteError();
  console.error(error);

  return (
    <div className="flex flex-col items-center justify-center h-screen max-h-screen">
      <h1 className="text-2xl font-bold">Oops!</h1>
      <p className="text-lg">Sorry, an unexpected error has occurred.</p>
      <div className="mt-6">
        <div className="font-bold text-center">
          {error.statusText || error.toString()}
        </div>
        {typeof error.stack === "string" && (
          <pre className="mt-6 text-xs">{error.stack.slice(0, 1000)}</pre>
        )}
      </div>
    </div>
  );
}
