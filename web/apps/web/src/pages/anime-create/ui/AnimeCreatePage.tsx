import AnimeCreateForm from "../../../features/anime-create/ui/AnimeCreateForm";
import styles from "./AnimeCreatePage.module.scss";

export default function AnimeCreatePage() {
  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <p className={styles.kicker}>Anime management</p>
        <h1>Create anime</h1>
        <p>
          Enter schedule details, select a Nyaa release for each episode, and
          clean up the episode titles before saving.
        </p>
      </section>

      <section className={styles.panel}>
        <AnimeCreateForm />
      </section>
    </main>
  );
}
