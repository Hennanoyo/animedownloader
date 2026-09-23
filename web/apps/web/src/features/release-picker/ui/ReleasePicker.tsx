import { useState } from "react";
import { Button } from "react-aria-components";
import type { Release } from "../../../entities/release/model/types";
import { useReleaseSearch } from "../../release-search/model/useReleaseSearch";
import ReleaseSearchForm from "../../release-search/ui/ReleaseSearchForm";
import styles from "./ReleasePicker.module.scss";

interface ReleasePickerProps {
  release: Release | null;
  onSelect: (release: Release) => void;
}

export default function ReleasePicker({
  release,
  onSelect,
}: ReleasePickerProps) {
  const [query, setQuery] = useState("");
  const [isPicking, setIsPicking] = useState(release === null);
  const search = useReleaseSearch(query);

  return (
    <div className={styles.picker}>
      {release && !isPicking ? (
        <div className={styles.selected}>
          <div>
            <strong>{release.title}</strong>
            <span>
              {release.size ?? "Unknown size"} · Seeders{" "}
              {release.seeders ?? "—"}
            </span>
          </div>
          <Button
            className={styles.changeButton}
            type="button"
            onPress={() => setIsPicking(true)}
          >
            Change
          </Button>
        </div>
      ) : (
        <>
          <ReleaseSearchForm
            embedded
            initialQuery={query}
            onSearch={(value) => setQuery(value)}
          />

          {query ? (
            <div className={styles.results} aria-live="polite">
              {search.isPending ? <p>Searching Nyaa...</p> : null}
              {search.isError ? (
                <p>Search failed: {search.error.message}</p>
              ) : null}
              {search.isSuccess && search.data.items.length === 0 ? (
                <p>No matching releases.</p>
              ) : null}
              {search.isSuccess
                ? search.data.items.map((item) => (
                    <article className={styles.result} key={item.id}>
                      <div>
                        <strong>{item.title}</strong>
                        <span>
                          {item.size ?? "Unknown size"} · Seeders{" "}
                          {item.seeders ?? "—"}
                        </span>
                      </div>
                      <Button
                        className={styles.selectButton}
                        type="button"
                        onPress={() => {
                          onSelect(item);
                          setQuery("");
                          setIsPicking(false);
                        }}
                      >
                        Select
                      </Button>
                    </article>
                  ))
                : null}
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}
