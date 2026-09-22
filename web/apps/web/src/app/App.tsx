import { Link, Outlet } from "@tanstack/react-router";
import styles from "./App.module.scss";

export default function App() {
  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <div className={styles.brand}>
          <span className={styles.brandMark}>AD</span>
          <span>AnimeDownloader</span>
        </div>
        <nav className={styles.nav} aria-label="Primary navigation">
          <Link
            className={styles.navLink}
            activeProps={{ className: styles.navLinkActive }}
            search={{ q: "" }}
            to="/"
          >
            Release search
          </Link>
          <Link
            className={styles.navLink}
            activeProps={{ className: styles.navLinkActive }}
            to="/animes"
          >
            Anime
          </Link>
        </nav>
      </header>
      <Outlet />
    </div>
  );
}
