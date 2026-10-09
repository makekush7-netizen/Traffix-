import { useEffect, useState, useCallback, useRef } from "react";
import * as SecureStore from "expo-secure-store";
import { newProfile, readProfile } from "./profile";
import type { Profile } from "./profile";
let writes: Promise<void> = Promise.resolve();
export function useProfile() {
  const [profile, setProfile] = useState<Profile>(newProfile);
  const [loaded, setLoaded] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [profileError, setProfileError] = useState("");
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    let active = true;
    SecureStore.getItemAsync("traffix.profile").then(raw => {
      if (active) setProfile(readProfile(raw));
    }).catch(() => {
      if (active) setProfileError("Your local profile could not be loaded. Changes can be saved again; connection credentials are separate.");
    }).finally(() => { if (active) setLoaded(true); });
    return () => { active = false; mounted.current = false; };
  }, []);
  useEffect(() => {
    if (!loaded || !dirty) return;
    const data = JSON.stringify(profile);
    writes = writes.catch(() => {}).then(() => SecureStore.setItemAsync("traffix.profile", data));
    writes.then(() => { if (mounted.current) setProfileError(""); }).catch(() => {
      if (mounted.current) setProfileError("Changes are visible, but could not be saved to this device. Please try again.");
    });
  }, [loaded, profile, dirty]);
  const updateProfile = useCallback((update: (p: Profile) => Profile) => { setProfile(update); setDirty(true); }, []);
  return { profile, updateProfile, loaded, profileError };
}
