import { createRootRoute, createRoute, createRouter } from "@tanstack/react-router";
import { z } from "zod";
import ReleaseSearchPage from "../pages/release-search/ui/ReleaseSearchPage";
import App from "./App";

const rootRoute = createRootRoute({
  component: App,
});

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  validateSearch: z.object({
    q: z.string().trim().max(200).catch(""),
  }),
  component: ReleaseSearchPage,
});

const routeTree = rootRoute.addChildren([indexRoute]);

export const router = createRouter({
  routeTree,
  defaultPreload: "intent",
});

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
