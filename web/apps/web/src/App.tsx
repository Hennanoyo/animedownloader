import { useEffect, useState } from "react";
import { fetchHealth, getApiBaseUrl } from "./lib/api";
import "./styles.css";

const apiBaseUrl = getApiBaseUrl(import.meta.env.VITE_API_URL);

export default function App() {
  const [apiStatus, setApiStatus] = useState("checking");

  useEffect(() => {
    let cancelled = false;

    void fetchHealth(apiBaseUrl)
      .then(() => {
        if (!cancelled) {
          setApiStatus("online");
        }
      })
      .catch(() => {
        if (!cancelled) {
          setApiStatus("offline");
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main className="app">
      <section className="card">
        <span className="eyebrow">AnimeDownloader</span>
        <h1>Media library foundation</h1>
        <p>
          The application workspace is ready. Feature work will be added in
          small, testable increments.
        </p>
        <div className="status">
          <span>API</span>
          <strong data-status={apiStatus}>{apiStatus}</strong>
        </div>
      </section>
    </main>
  );
}
