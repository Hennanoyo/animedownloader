import { Outlet } from "@tanstack/react-router";
import styles from "./App.module.scss";

export default function App() {
  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <div className={styles.brand}>
          <span className={styles.brandMark}>AD</span>
          <span>AnimeDownloader</span>
        </div>
        <span className={styles.headerText}>Release search</span>
      </header>
      <Outlet />
    </div>
  );
}
