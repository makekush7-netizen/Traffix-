export type RideRecord = { id: string; role: string; samples: number; arrived: boolean; date: string };
export type Profile = {
  version: 1; name: string; avatar: string; vehicle: string;
  units: "km/h" | "m/s"; illustrations: boolean; homeTips: boolean;
  learned: number[]; rides: RideRecord[];
};
export const avatars = ["🟣", "🌿", "🌞", "🛵"];
export const vehicles = ["Car", "Bike", "Auto", "Passenger"];
export const newProfile = (): Profile => ({ version: 1, name: "", avatar: avatars[0], vehicle: "Passenger", units: "km/h", illustrations: true, homeTips: true, learned: [], rides: [] });
export function profileName(value: string): string {
  const clean = value.replace(/[\u0000-\u001f\u007f]/g, "").trim().replace(/\s+/g, " ");
  if (!clean || [...clean].length > 32) throw Error("Enter a name between 1 and 32 characters.");
  return clean;
}
export function readProfile(raw: string | null): Profile {
  if (!raw) return newProfile();
  const p = JSON.parse(raw);
  if (p.version !== 1 || typeof p.name !== "string" || !Array.isArray(p.learned) || !Array.isArray(p.rides)) throw Error("Invalid local profile");
  return { ...newProfile(), name: p.name ? profileName(p.name) : "",
    avatar: avatars.includes(p.avatar) ? p.avatar : avatars[0],
    vehicle: vehicles.includes(p.vehicle) ? p.vehicle : "Passenger",
    units: p.units === "m/s" ? "m/s" : "km/h",
    illustrations: p.illustrations !== false, homeTips: p.homeTips !== false,
    learned: [...new Set<number>(p.learned.filter((i: unknown) => Number.isInteger(i) && Number(i) >= 0 && Number(i) < 4))],
    rides: p.rides.filter((r: RideRecord) => r && typeof r.id === "string" && r.id.length < 400 && typeof r.role === "string" && typeof r.date === "string" && Number.isSafeInteger(r.samples) && r.samples >= 0 && typeof r.arrived === "boolean").slice(-20),
  };
}
export function recordRide(p: Profile, record: RideRecord): Profile {
  const old = p.rides.find(r => r.id === record.id);
  if (old && old.role === record.role && old.samples >= record.samples && (old.arrived || !record.arrived)) return p;
  const next = old ? { ...old, role: record.role, samples: Math.max(old.samples, record.samples), arrived: old.arrived || record.arrived } : record;
  return { ...p, rides: [...p.rides.filter(r => r.id !== record.id), next].slice(-20) };
}
