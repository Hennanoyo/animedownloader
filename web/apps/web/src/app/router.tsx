import { createRootRoute, createRoute, createRouter } from "@tanstack/react-router";
import { z } from "zod";
import AnimeCreatePage from "../pages/anime-create/ui/AnimeCreatePage";
import AnimeListPage from "../pages/animes/ui/AnimeListPage";
import ReleaseSearchPage from "../pages/release-search/ui/ReleaseSearchPage";
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

const routeTree = rootRoute.addChildren([
  indexRoute,
  animesRoute,
  animeCreateRoute,
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
