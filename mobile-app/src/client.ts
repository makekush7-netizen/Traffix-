import {
  initialState,
  serverAddress,
  validFrame,
  validWorld,
  normalizeOwn,
  eligible,
  friendly,
} from "./protocol";
import type { Claim, Frame, Own, Offer, World, ClientState } from "./protocol";
async function timedFetch(url: string, options: RequestInit = {}) {
  const controller = new AbortController(),
    deadline = setTimeout(() => controller.abort(), 10000);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(deadline);
  }
}
export class TrafficClient {
  state = initialState();
  server = "";
  seq = 0;
  world: World | null = null;
  apiVersion: "1" | "2.0" = "1";
  private ws: WebSocket | null = null;
  private generation = 0;
  private stopped = true;
  private timer: ReturnType<typeof setInterval> | null = null;
  private retry: ReturnType<typeof setTimeout> | null = null;
  private lastFrame = 0;
  private lastServer = 0;
  private sent = new Set<string>();
  private requests = new Map<string, string>();
  private decisionTimer: ReturnType<typeof setTimeout> | null = null;
  private polling = false;
  constructor(
    private notify: (state: ClientState) => void,
    private persist: (claim: Claim | null, seq: number) => void,
  ) {}
  private publish(change: Partial<ClientState> = {}) {
    this.state = { ...this.state, ...change };
    this.notify({ ...this.state });
  }
  setHost(server: string) {
    this.server = serverAddress(server);
  }
  async configure(server: string) {
    this.server = serverAddress(server);
    const capabilities = await timedFetch(this.server + "/api/v2/capabilities");
    if (capabilities.ok) {
      const data = await capabilities.json();
      if (data.api_version !== "2.0") throw Error("Unsupported host API version.");
      this.apiVersion = "2.0";
      this.world = null;
      this.publish({ world: null });
      if (this.state.claim) await this.loadWorld(this.state.claim);
      return this.world;
    }
    if (capabilities.status !== 404) throw Error("Host discovery failed. Check the server connection.");
    this.apiVersion = "1";
    const r = await timedFetch(this.server + "/api/world");
    if (!r.ok)
      throw Error(
        "The simulation map is unavailable. Check the laptop server.",
      );
    const world = await r.json();
    if (!validWorld(world))
      throw Error("This host does not provide a supported simulation map.");
    this.world = world as World;
    this.publish({ world: this.world });
    return this.world;
  }
  private async loadWorld(claim: Claim) {
    if (this.apiVersion !== "2.0") return;
    const host = this.server;
    const response = await timedFetch(`${host}/api/v2/phones/world?session_id=${encodeURIComponent(claim.session_id)}&run_id=${encodeURIComponent(claim.run_id)}`, { headers: { Authorization: "Bearer " + claim.token } });
    if (!response.ok) throw Error("The driver map could not be loaded. Reconnect or request a fresh invitation.");
    const map = await response.json();
    if (!validWorld(map)) throw Error("The host returned an unsupported driver map.");
    if (this.server !== host || this.state.claim?.session_id !== claim.session_id) return;
    this.world = map;
    this.publish({ world: map });
  }
  async join(code: string) {
    if (this.state.claim)
      throw Error("Leave the current vehicle before joining another.");
    const controller = new AbortController();
    const deadline = setTimeout(() => controller.abort(), 10000);
    try {
      const r = await fetch(this.server + (this.apiVersion === "2.0" ? "/api/v2/phones/claim" : "/api/claim"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ join_code: code }),
        signal: controller.signal,
      });
      const c = await r.json();
      if (!r.ok)
        throw Error(
          friendly[c.detail] ||
            "Could not join this vehicle. Request a fresh invitation.",
        );
      if (!c.run_id || !c.vehicle_id || !c.session_id || !c.token)
        throw Error("Unsupported server response.");
      if (this.apiVersion === "2.0") c.api_version = "2.0";
      this.seq = 0;
      this.sent.clear();
      this.requests.clear();
      this.publish({ ...initialState(), world: this.world, claim: c, connection: "connecting" });
      this.persist(c, 0);
      try { await this.loadWorld(c); } catch (error) { this.publish({ notice: (error as Error).message }); }
      this.connect();
    } finally {
      clearTimeout(deadline);
    }
  }
  restore(claim: Claim, seq: number) {
    if (claim.api_version === "2.0") this.apiVersion = "2.0";
    this.seq = seq;
    this.publish({ claim, connection: "connecting" });
    this.connect();
  }
  private send(type: string, payload: unknown, stamp: number | null = null) {
    const c = this.state.claim;
    if (
      !c ||
      this.ws?.readyState !== WebSocket.OPEN ||
      (type !== "session.hello" && this.state.connection !== "connected")
    )
      return;
    const seq = ++this.seq,
      id = `msg.native.${seq}`;
    this.ws.send(
      JSON.stringify({
        v: 1,
        type,
        msg_id: id,
        run_id: c.run_id,
        sender_id: c.session_id,
        seq,
        sim_time_s: stamp,
        payload,
      }),
    );
    this.requests.set(id, type);
    if (this.requests.size > 100)
      this.requests.delete(this.requests.keys().next().value!);
    this.persist(c, seq);
    return id;
  }
  connect() {
    if (!this.state.claim) return;
    this.stopped = false;
    const generation = ++this.generation;
    if (this.retry) clearTimeout(this.retry);
    this.clearTimer();
    this.ws?.close();
    this.publish({
      connection: "connecting",
      sharing: false,
      fresh: false,
      offer: null,
      pending: false,
    });
    const ws = new WebSocket(this.server.replace(/^http/, "ws") + (this.apiVersion === "2.0" ? "/api/v2/phones/ws" : "/ws"));
    this.ws = ws;
    ws.onopen = () => {
      if (generation !== this.generation) return;
      this.send("session.hello", {
        token: this.state.claim!.token,
        last_server_seq: this.lastServer,
      });
    };
    ws.onmessage = (e) => {
      if (generation !== this.generation) return;
      let m;
      try {
        m = JSON.parse(e.data);
      } catch {
        return;
      }
      const c = this.state.claim;
      if (!c || m.run_id !== c.run_id) return;
      this.lastServer = m.seq;
      if (m.type === "session.ready") {
        if (m.payload.vehicle_id !== c.vehicle_id) return;
        this.publish({
          connection: "connected",
          sharing: false,
          notice: "Connected. Sharing stays off until you choose.",
        });
        this.startTimer();
        this.pollOwn();
        if (this.apiVersion === "2.0" && !this.world) this.loadWorld(c).catch(error => this.publish({ notice: error.message }));
      }
      if (m.type === "vehicle.frame") {
        const f = m as Frame;
        if (
          !validFrame(f, c) ||
          (this.state.frame && f.sim_time_s < this.state.frame.sim_time_s)
        )
          return;
        this.lastFrame = Date.now();
        const expired =
          this.state.offer && !eligible(this.state.offer, f, true);
        this.publish({
          frame: f,
          fresh: true,
          ...(expired
            ? {
                offer: null,
                pending: false,
                notice: "Route offer expired. Your original route continues.",
              }
            : {}),
        });
        this.echo();
      }
      if (m.type === "guidance") {
        const o = m.payload as Offer;
        if (
          o?.kind !== "reroute" ||
          o.vehicle_id !== c.vehicle_id ||
          typeof o.advisory_id !== "string" ||
          typeof o.message !== "string" ||
          !Number.isFinite(o.expires_sim_s)
        )
          return;
        if (this.state.frame && this.state.frame.sim_time_s >= o.expires_sim_s)
          return;
        this.publish({
          offer: o,
          pending: false,
          notice: "A route option is ready. Review it before moving.",
        });
      }
      if (m.type === "ack") {
        const kind = this.requests.get(m.payload.in_reply_to);
        this.requests.delete(m.payload.in_reply_to);
        const { status, reason } = m.payload;
        if (kind === "probe.toggle") {
          if (status === "applied") {
            this.publish({ sharing: reason === "sharing_on", pending: false });
            this.echo();
          } else
            this.publish({
              pending: false,
              notice: "Sharing change was not confirmed.",
            });
        }
        if (kind === "probe.sample" && status === "applied")
          this.publish({ samples: this.state.samples + 1 });
        if (kind === "driver.decision") {
          if (this.decisionTimer) clearTimeout(this.decisionTimer);
          this.publish({
            offer: null,
            pending: false,
            notice:
              status === "applied" && reason === "route_applied"
                ? "Route change applied. The server confirmed your route."
                : reason === "original_route_kept"
                  ? "Your original route continues."
                  : friendly[reason] ||
                    "The route change was not confirmed. Keep your current route.",
          });
          this.pollOwn();
        }
        if (kind === "driver.report")
          this.publish({
            notice:
              status === "received"
                ? "Report received. The operator will review it."
                : "Report not confirmed. Try again when connected.",
          });
      }
    };
    ws.onclose = (e) => {
      if (generation !== this.generation) return;
      this.clearTimer();
      this.publish({
        connection: "offline",
        sharing: false,
        fresh: false,
        offer: null,
        pending: false,
        notice: "Connection lost. Guidance and sharing are off.",
      });
      if (e.code === 1008 && e.reason !== "heartbeat_timeout") {
        this.publish({
          claim: null,
          frame: null,
          own: null,
          connection: "rejoin",
          notice: "The run or session ended. Get a fresh vehicle invitation.",
        });
        this.persist(null, 0);
        return;
      }
      if (!this.stopped) this.retry = setTimeout(() => this.connect(), 2000);
    };
    ws.onerror = () => {};
  }
  private startTimer() {
    this.clearTimer();
    this.timer = setInterval(() => {
      this.send("heartbeat", { visible: true });
      this.pollOwn();
      if (Date.now() - this.lastFrame > 5000) {
        if (this.state.sharing) this.send("probe.toggle", { enabled: false });
        this.publish({
          fresh: false,
          sharing: false,
          offer: null,
          notice: "Vehicle updates are stale. Wait for a fresh connection.",
        });
      }
    }, 2000);
  }
  private clearTimer() {
    if (this.timer) clearInterval(this.timer);
    this.timer = null;
  }
  private async pollOwn() {
    const c = this.state.claim,
      g = this.generation;
    if (!c || this.polling || this.state.connection !== "connected") return;
    this.polling = true;
    try {
      const r = await timedFetch(
        `${this.server}${this.apiVersion === "2.0" ? "/api/v2/phones/state" : "/api/driver/state"}?session_id=${encodeURIComponent(c.session_id)}&run_id=${encodeURIComponent(c.run_id)}`,
        { headers: { Authorization: "Bearer " + c.token } },
      );
      if (g !== this.generation) return;
      if (r.ok) {
        const own = normalizeOwn(await r.json(), this.world);
        if (!own) return;
        const scoped = own as Own & { vehicle_id?: string; run_id?: string };
        if (this.apiVersion === "2.0" && (scoped.vehicle_id !== c.vehicle_id || scoped.run_id !== c.run_id)) return;
        if (
          own.offer &&
          ["expired", "cancelled", "rejected"].includes(own.offer.status)
        )
          this.publish({ offer: null, pending: false });
        if (own.paused && this.state.frame) this.lastFrame = Date.now();
        this.publish({ own, ...(own.paused && this.state.frame ? { fresh: true } : {}) });
      } else if (r.status === 401 && this.apiVersion === "2.0") {
        this.leave();
        this.publish({ connection: "rejoin", notice: "This journey session expired. Ask the operator for a new invitation." });
      }
    } catch {
    } finally {
      this.polling = false;
    }
  }
  private echo() {
    const f = this.state.frame;
    if (
      !f ||
      !this.state.sharing ||
      !this.state.fresh ||
      f.payload.state !== "active" ||
      this.sent.has(f.payload.frame_id)
    )
      return;
    const id = this.send(
      "probe.sample",
      {
        frame_id: f.payload.frame_id,
        vehicle_id: f.payload.vehicle_id,
        pose: f.payload.pose,
      },
      f.sim_time_s,
    );
    if (id) {
      this.sent.add(f.payload.frame_id);
      if (this.sent.size > 200)
        this.sent.delete(this.sent.values().next().value!);
    }
  }
  toggle(enabled: boolean) {
    if (this.state.pending || this.state.connection !== "connected") return;
    if (this.send("probe.toggle", { enabled })) {
      this.publish({ pending: true });
      setTimeout(() => {
        if (this.state.pending) this.publish({ pending: false });
      }, 6000);
    }
  }
  decide(choice: "accept" | "ignore") {
    const { offer, frame } = this.state;
    if (
      this.state.pending ||
      this.state.connection !== "connected" ||
      !eligible(offer, frame, this.state.fresh)
    )
      return;
    this.send("driver.decision", { advisory_id: offer!.advisory_id, choice });
    this.publish({
      pending: true,
      notice: "Waiting for the server. Your route has not changed yet.",
    });
    this.decisionTimer = setTimeout(() => {
      if (this.state.pending)
        this.publish({
          pending: false,
          notice:
            "Confirmation delayed. Check your current route before trying again.",
        });
    }, 10000);
  }
  report() {
    const f = this.state.frame;
    if (!f || !this.state.fresh || f.payload.state !== "active") return;
    this.send(
      "driver.report",
      {
        frame_id: f.payload.frame_id,
        vehicle_id: f.payload.vehicle_id,
        category: "slow_traffic",
      },
      f.sim_time_s,
    );
  }
  suspend() {
    this.stopped = true;
    ++this.generation;
    if (this.retry) clearTimeout(this.retry);
    if (this.decisionTimer) clearTimeout(this.decisionTimer);
    this.clearTimer();
    this.ws?.close();
    this.ws = null;
    this.publish({
      connection: "offline",
      sharing: false,
      fresh: false,
      offer: null,
      pending: false,
    });
  }
  leave() {
    this.suspend();
    this.seq = 0;
    this.sent.clear();
    this.requests.clear();
    this.world = null;
    this.publish(initialState());
    this.persist(null, 0);
  }
}
