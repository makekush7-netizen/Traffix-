import { createContext, useContext } from "react";
import type { Dispatch, SetStateAction } from "react";
import type { TrafficClient } from "./client";
import type { ClientState, World } from "./protocol";
import type { Tab } from "./ui";
import type { Profile } from "./profile";
type DriverContextValue = {
  profile: Profile;
  profileLoaded: boolean;
  profileError: string;
  updateProfile: (update: (p: Profile) => Profile) => void;
  state: ClientState;
  world: World | null;
  api: TrafficClient;
  finished: boolean;
  speed: number | null;
  readyOffer: boolean;
  online: boolean;
  active: boolean;
  server: string;
  draftServer: string;
  error: string;
  working: boolean;
  openJoin: () => void;
  setTab: (tab: Tab) => void;
  setLesson: Dispatch<SetStateAction<number | null>>;
  setDraftServer: Dispatch<SetStateAction<string>>;
  saveServer: () => Promise<void>;
  leave: () => void;
};
export const DriverContext = createContext<DriverContextValue | null>(null);
export function useDriver() {
  const value = useContext(DriverContext);
  if (!value)
    throw Error("Driver screen requires the persistent session owner.");
  return value;
}
