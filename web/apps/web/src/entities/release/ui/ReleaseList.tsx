import type { Release } from "../model/types";
import ReleaseCard from "./ReleaseCard";
import styles from "./ReleaseList.module.scss";

interface ReleaseListProps {
  releases: Release[];
}

export default function ReleaseList({ releases }: ReleaseListProps) {
  return (
    <ul className={styles.list}>
      {releases.map((release) => (
        <li key={release.id}>
          <ReleaseCard release={release} />
        </li>
      ))}
    </ul>
  );
}
