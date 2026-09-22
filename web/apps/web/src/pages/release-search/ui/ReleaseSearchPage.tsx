import { useNavigate, useSearch } from "@tanstack/react-router";
import { ApiRequestError } from "../../../shared/api/client";
import {
  ReleaseSearchResponseError,
} from "../../../entities/release/api/searchReleases";
import ReleaseList from "../../../entities/release/ui/ReleaseList";
import { useReleaseSearch } from "../../../features/release-search/model/useReleaseSearch";
import ReleaseSearchForm from "../../../features/release-search/ui/ReleaseSearchForm";
import styles from "./ReleaseSearchPage.module.scss";

function getSearchErrorMessage(error: unknown): string {
  if (error instanceof ReleaseSearchResponseError) {
    return error.message;
  }

  if (error instanceof ApiRequestError) {
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Unknown error";
}

export default function ReleaseSearchPage() {
  const { q } = useSearch({ from: "/" });
  const navigate = useNavigate({ from: "/" });
  const query = q.trim();
  const search = useReleaseSearch(query);

  function handleSearch(value: string) {
    void navigate({
      to: "/",
      search: {
        q: value,
      },
    });
  }

  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <p className={styles.kicker}>Nyaa RSS</p>
        <h1 className={styles.heading}>Find anime releases before downloading.</h1>
        <p className={styles.description}>
          Search Nyaa without coupling the UI to the upstream feed. Results are fetched
          through the API and cached by TanStack Query.
        </p>
      </section>

      <section className={styles.searchPanel} aria-label="Release search">
        <ReleaseSearchForm key={q} initialQuery={q} onSearch={handleSearch} />
      </section>

      {query ? (
        <section aria-live="polite">
          <div className={styles.resultsHeader}>
            <h2 className={styles.resultsTitle}>Results</h2>
            {!search.isPending && !search.isError ? (
              <span className={styles.count}>{search.data.items.length} releases</span>
            ) : null}
          </div>

          {search.isPending ? <p className={styles.state}>Searching Nyaa...</p> : null}

          {search.isError ? (
            <p className={[styles.state, styles.errorState].join(" ")}>
              Search failed: {getSearchErrorMessage(search.error)}
            </p>
          ) : null}

          {search.isSuccess && search.data.items.length === 0 ? (
            <p className={styles.state}>No matching releases were found.</p>
          ) : null}

          {search.isSuccess && search.data.items.length > 0 ? (
            <ReleaseList releases={search.data.items} />
          ) : null}
        </section>
      ) : (
        <p className={styles.state}>Enter an anime title, release group, or quality.</p>
      )}
    </main>
  );
}
