import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useSyncExternalStore } from "react";

import { api } from "../api/client";
import type { Me, Theme } from "../api/types";
import { ME_KEY } from "../hooks/useMe";
import { applyTheme, DARK_QUERY, toggledTheme, type EffectiveTheme } from "./theme";

function subscribe(onChange: () => void): () => void {
  const query = window.matchMedia(DARK_QUERY);
  query.addEventListener("change", onChange);
  return () => {
    query.removeEventListener("change", onChange);
  };
}

/** El tema de la persona (guardado en el servidor), el que se ve y cómo cambiarlo. */
export function useTheme(theme: Theme) {
  const queryClient = useQueryClient();
  const systemIsDark = useSyncExternalStore(subscribe, () => window.matchMedia(DARK_QUERY).matches);
  const save = useMutation({
    mutationFn: (next: Theme) => api.patch("/api/v1/me/preferences/", { theme: next }),
    onMutate: (next) => {
      applyTheme(next);
      queryClient.setQueryData<Me>(ME_KEY, (me) => (me ? { ...me, user: { ...me.user, theme: next } } : me));
    },
    onError: () => queryClient.invalidateQueries({ queryKey: ME_KEY }),
  });

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  const systemShown: EffectiveTheme = systemIsDark ? "dark" : "light";
  const shown: EffectiveTheme = theme === "system" ? systemShown : theme;
  return {
    theme,
    shown,
    toggle: () => {
      save.mutate(toggledTheme(theme));
    },
    useSystem: () => {
      save.mutate("system");
    },
  };
}
