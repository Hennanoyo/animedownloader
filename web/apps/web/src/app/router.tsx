import { createRootRoute, createRoute, createRouter } from "@tanstack/react-router";
import { z } from "zod";
import AnimeCreatePage from "../pages/anime-create/ui/AnimeCreatePage";
import AnimeDetailPage from "../pages/anime-detail/ui/AnimeDetailPage";
import AnimeListPage from "../pages/animes/ui/AnimeListPage";
import DownloadManagerPage from "../pages/downloads/ui/DownloadManagerPage";
import EpisodePlayerPage from "../pages/episode-player/ui/EpisodePlayerPage";
import ReleaseSearchPage from "../pages/release-search/ui/ReleaseSearchPage";
import ReleaseProfilesPage from "../pages/release-profiles/ui/ReleaseProfilesPage";
import App from "./App";

const rootRoute = createRootRoute({ component: App });

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  validateSearch: z.object({
    q: z.string().trim().max(200).catch(""),
  }),
  component: ReleaseSearchPage,
});

const animesRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/animes",
  component: AnimeListPage,
});

const animeCreateRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/animes/new",
  component: AnimeCreatePage,
});

const animeDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/animes/$animeId",
  component: AnimeDetailPage,
});

const releaseProfilesRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/release-profiles",
  component: ReleaseProfilesPage,
});

const downloadsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/downloads",
  validateSearch: z.object({
    status: z.enum(["all", "active", "failed", "history"]).catch("all"),
  }),
  component: DownloadManagerPage,
});

const episodePlayerRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/episodes/$episodeId",
  component: EpisodePlayerPage,
});

const routeTree = rootRoute.addChildren([
  indexRoute,
  animesRoute,
  animeCreateRoute,
  animeDetailRoute,
  releaseProfilesRoute,
  downloadsRoute,
  episodePlayerRoute,
]);

export const router = createRouter({
  routeTree,
  defaultPreload: "intent",
});

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
