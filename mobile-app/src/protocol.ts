export type Claim = {
  run_id: string;
  session_id: string;
  vehicle_id: string;
  token: string;
};
export type Pose = {
  x_m: number;
  y_m: number;
  speed_mps: number;
  edge_id: string;
};
export type Frame = {
  run_id: string;
  sim_time_s: number;
  payload: {
    vehicle_id: string;
    frame_id: string;
    state: string;
    pose: Pose | null;
  };
};
export type Offer = {
  advisory_id: string;
  vehicle_id: string;
  kind: string;
  message: string;
  expires_sim_s: number;
};
export type Own = {
  role: string;
  route_id: string;
  route_path: number[][][];
  paused: boolean;
  ended: boolean;
  offer?: { status: string };
};
export type Road = { shape: number[][]; width: number; internal: boolean };
export type World = { roads: Road[] };
export type ClientState = {
  connection: "offline" | "connecting" | "connected" | "rejoin";
  claim: Claim | null;
  frame: Frame | null;
  own: Own | null;
  offer: Offer | null;
  sharing: boolean;
  samples: number;
  notice: string;
  pending: boolean;
  fresh: boolean;
};
export const initialState = (): ClientState => ({
  connection: "offline",
  claim: null,
  frame: null,
  own: null,
  offer: null,
  sharing: false,
  samples: 0,
  notice: "",
  pending: false,
  fresh: false,
});
export function validWorld(value: World): boolean {
  return (
    Array.isArray(value?.roads) &&
    value.roads.length > 0 &&
    value.roads.every(
      (r) =>
        Number.isFinite(r.width) &&
        r.width >= 0 &&
        Array.isArray(r.shape) &&
        r.shape.length >= 2 &&
        r.shape.every(
          (p) =>
            Array.isArray(p) &&
            p.length >= 2 &&
            Number.isFinite(p[0]) &&
            Number.isFinite(p[1]),
        ),
    )
  );
}
export function validOwn(value: Own): boolean {
  return (
    typeof value?.role === "string" &&
    typeof value.route_id === "string" &&
    typeof value.paused === "boolean" &&
    Array.isArray(value.route_path) &&
    value.route_path.every(
      (shape) =>
        Array.isArray(shape) &&
        shape.every(
          (p) =>
            Array.isArray(p) && Number.isFinite(p[0]) && Number.isFinite(p[1]),
        ),
    )
  );
}
export function serverAddress(value: string): string {
  const u = new URL(value.trim());
  const host = u.hostname;
  const parts = host.split(".").map(Number),
    ipv4 =
      parts.length === 4 &&
      parts.every((p) => Number.isInteger(p) && p >= 0 && p <= 255);
  const local =
    host === "localhost" ||
    host === "127.0.0.1" ||
    host === "[::1]" ||
    (ipv4 &&
      (parts[0] === 10 ||
        (parts[0] === 192 && parts[1] === 168) ||
        (parts[0] === 172 && parts[1] >= 16 && parts[1] <= 31)));
  if (
    u.username ||
    u.password ||
    !["http:", "https:"].includes(u.protocol) ||
    (u.protocol === "http:" && !local)
  )
    throw Error(
      "Use HTTPS for an internet server, or HTTP for your local simulation laptop.",
    );
  return u.origin;
}
export function invitation(value: string): { code: string; server?: string } {
  const text = value.trim();
  if (/^traffix:\/\/join/i.test(text)) {
    const u = new URL(text);
    const code = u.searchParams.get("code"),
      server = u.searchParams.get("server");
    if (
      u.hostname !== "join" ||
      !code ||
      !server ||
      !/^[A-Za-z0-9_-]{6,128}$/.test(code)
    )
      throw Error("This invitation is incomplete.");
    return { code, server: serverAddress(server) };
  }
  if (/^https?:\/\//i.test(text)) {
    const u = new URL(text);
    const code = new URLSearchParams(u.hash.slice(1)).get("join");
    if (!code) throw Error("This link has no vehicle join code.");
    return { code, server: serverAddress(u.origin) };
  }
  if (!/^[A-Za-z0-9_-]{6,128}$/.test(text))
    throw Error(
      "Paste the join code or scan the invitation from the operator.",
    );
  return { code: text };
}
export function validFrame(frame: Frame, claim: Claim): boolean {
  const p = frame?.payload?.pose;
  return (
    frame.run_id === claim.run_id &&
    frame.payload?.vehicle_id === claim.vehicle_id &&
    Number.isFinite(frame.sim_time_s) &&
    frame.sim_time_s >= 0 &&
    typeof frame.payload.frame_id === "string" &&
    ((frame.payload.state === "arrived" && p === null) ||
      (frame.payload.state === "active" &&
        !!p &&
        Number.isFinite(p.x_m) &&
        Number.isFinite(p.y_m) &&
        Number.isFinite(p.speed_mps) &&
        p.speed_mps >= 0))
  );
}
export function eligible(
  offer: Offer | null,
  frame: Frame | null,
  fresh: boolean,
): boolean {
  return (
    !!offer &&
    !!frame &&
    fresh &&
    frame.payload.state === "active" &&
    offer.vehicle_id === frame.payload.vehicle_id &&
    frame.sim_time_s < offer.expires_sim_s
  );
}
export const friendly: Record<string, string> = {
  invalid_or_expired_code:
    "That invitation expired or was used. Ask the operator for a new one.",
  occupied_role:
    "That vehicle already has a driver. Choose another invitation.",
  expired_advisory: "The route offer expired. Continue on your original route.",
  past_decision_edge: "You have passed the turn. Keep your current route.",
  phone_evidence_unavailable:
    "There is not enough fresh traffic evidence. Keep your current route.",
  guidance_turned_off:
    "The operator withdrew this offer. Keep your current route.",
  too_late_for_safe_turn:
    "It is too late for this turn. Keep your current route.",
  bypass_blocked: "The alternative road is busy. Keep your current route.",
};
