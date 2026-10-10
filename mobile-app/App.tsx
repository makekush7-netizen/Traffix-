import React, { useEffect, useRef, useState } from "react";
import {
  View,
  Text,
  ScrollView,
  Pressable,
  Image,
  TextInput,
  Modal,
  ActivityIndicator,
  Alert,
  AppState,
  KeyboardAvoidingView,
  Platform,
  Linking,
} from "react-native";
import { StatusBar } from "expo-status-bar";
import * as SecureStore from "expo-secure-store";
import * as SplashScreen from "expo-splash-screen";
import { CameraView, useCameraPermissions } from "expo-camera";
import { SafeAreaProvider, SafeAreaView } from "react-native-safe-area-context";
import { Slot, router, usePathname } from "expo-router";
import { DriverContext } from "./src/driver-context";
import { C, s, Icon, Button, lessons } from "./src/ui";
import type { Tab } from "./src/ui";
import { TrafficClient } from "./src/client";
import {
  initialState,
  invitation,
  serverAddress,
  eligible,
} from "./src/protocol";
import type { ClientState, World, Claim } from "./src/protocol";
import { useProfile } from "./src/use-profile";
import { recordRide } from "./src/profile";
import { LessonDetail } from "./src/LessonDetail";
// Keep the native logo until local UI data is ready; never wait for the host.
SplashScreen.preventAutoHideAsync().catch(() => {});
SplashScreen.setOptions({ duration: 200, fade: true });
let sessionWrites: Promise<void> = Promise.resolve();
function persistSession(claim: Claim | null, seq: number) {
  const data = claim ? JSON.stringify({ claim, seq }) : null;
  sessionWrites = sessionWrites
    .catch(() => {})
    .then(async () => {
      if (data) await SecureStore.setItemAsync("traffix.session", data);
      else await SecureStore.deleteItemAsync("traffix.session");
    });
}
function Main() {
  const { profile, updateProfile, loaded: profileLoaded, profileError } = useProfile();
  useEffect(() => {
    if (profileLoaded) SplashScreen.hideAsync().catch(() => {});
  }, [profileLoaded]);
  const pathname = usePathname();
  const tab: Tab =
    pathname === "/ride"
      ? "Ride"
      : pathname === "/learn"
        ? "Learn"
        : pathname === "/settings" || pathname === "/profile" || pathname === "/impact"
          ? "Settings"
          : "Home";
  const setTab = (next: Tab) =>
    router.replace(
      next === "Home" ? "/" : (("/" + next.toLowerCase()) as "/ride"),
    );
  const [state, setState] = useState<ClientState>(initialState),
    [world, setWorld] = useState<World | null>(null),
    [server, setServer] = useState("http://127.0.0.1:8004"),
    [draftServer, setDraftServer] = useState("http://127.0.0.1:8004"),
    [code, setCode] = useState(""),
    [joinOpen, setJoinOpen] = useState(false),
    [scanning, setScanning] = useState(false),
    [working, setWorking] = useState(false),
    [error, setError] = useState(""),
    [lesson, setLesson] = useState<number | null>(null);
  const [permission, requestPermission] = useCameraPermissions();
  const scanned = useRef(false);
  const [api] = useState(() => new TrafficClient(setState, persistSession));
  const rideId = state.claim ? JSON.stringify([server, state.claim.run_id, state.claim.vehicle_id]) : null;
  const rideRole = state.own?.role || "Simulated vehicle";
  const arrived = state.frame?.payload.state === "arrived";
  useEffect(() => {
    if (!profileLoaded || !rideId) return;
    updateProfile(p => recordRide(p, { id: rideId, role: rideRole, samples: state.samples, arrived, date: new Date().toISOString() }));
  }, [profileLoaded, rideId, rideRole, state.samples, arrived, updateProfile]);
  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const url =
          (await SecureStore.getItemAsync("traffix.server")) ||
          "http://127.0.0.1:8004";
        if (!mounted) return;
        setServer(url);
        setDraftServer(url);
        api.setHost(url);
        try {
          setWorld(await api.configure(url));
        } catch {}
        const saved = await SecureStore.getItemAsync("traffix.session");
        if (saved && mounted) {
          const data = JSON.parse(saved) as { claim: Claim; seq: number };
          if (data.claim?.token && Number.isInteger(data.seq))
            api.restore(data.claim, data.seq);
        }
      } catch {
        setError(
          "Saved connection could not be restored. Connect to your laptop again.",
        );
      }
    })();
    const sub = AppState.addEventListener("change", (next) => {
      if (next === "active" && api.state.claim) api.connect();
      else if (next !== "active") api.suspend();
    });
    const showInvitation = (url: string) => {
      try {
        const p = invitation(url);
        setCode(p.code);
        if (p.server) setDraftServer(p.server);
        setJoinOpen(true);
      } catch {}
    };
    const link = Linking.addEventListener("url", (e) => showInvitation(e.url));
    Linking.getInitialURL().then((url) => {
      if (url && mounted) showInvitation(url);
    });
    return () => {
      mounted = false;
      sub.remove();
      link.remove();
      api.suspend();
    };
  }, [api]);
  async function saveServer() {
    try {
      const url = serverAddress(draftServer);
      if (state.claim && url !== server)
        throw Error("Leave your current vehicle before changing hosts.");
      setWorking(true);
      setWorld(await api.configure(url));
      setServer(url);
      await SecureStore.setItemAsync("traffix.server", url);
      setError("");
      Alert.alert(
        "Laptop connected",
        "Join using the invitation on its dashboard.",
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setWorking(false);
    }
  }
  async function join() {
    setWorking(true);
    setError("");
    try {
      const p = invitation(code),
        url = p.server || serverAddress(draftServer);
      setWorld(await api.configure(url));
      await api.join(p.code);
      setServer(url);
      setDraftServer(url);
      await SecureStore.setItemAsync("traffix.server", url);
      setJoinOpen(false);
      setCode("");
      setTab("Ride");
    } catch (e) {
      setError(
        (e as Error).message.includes("Network")
          ? "Cannot reach the laptop. Check its address, server and USB connection."
          : (e as Error).message,
      );
    } finally {
      setWorking(false);
    }
  }
  const online = state.connection === "connected",
    active = state.frame?.payload.state === "active",
    finished = state.frame?.payload.state === "arrived",
    speed =
      state.fresh && state.frame?.payload.pose
        ? Math.round(state.frame.payload.pose.speed_mps * 3.6)
        : null;
  const readyOffer = eligible(state.offer, state.frame, state.fresh) && online,
    status = online
      ? state.fresh
        ? "Connected"
        : "Waiting for updates"
      : state.connection === "connecting"
        ? "Connecting…"
        : "Not connected";
  const openJoin = () => {
    setError("");
    setJoinOpen(true);
  };
  const leave = () =>
    Alert.alert(
      "Leave this vehicle?",
      "Sharing will stop. The operator must reset the run or assign an unbound vehicle before you can join again.",
      [
        { text: "Stay", style: "cancel" },
        {
          text: "Leave",
          style: "destructive",
          onPress: () => {
            api.leave();
            setTab("Home");
          },
        },
      ],
    );
  return (
    <DriverContext.Provider
      value={{
        profile,
        profileLoaded,
        profileError,
        updateProfile,
        state,
        world,
        api,
        finished,
        speed,
        readyOffer,
        online,
        active,
        server,
        draftServer,
        error,
        working,
        openJoin,
        setTab,
        setLesson,
        setDraftServer,
        saveServer,
        leave,
      }}
    >
      <SafeAreaView style={s.safe} edges={["top", "bottom"]}>
        <StatusBar style="dark" />
        <View style={s.header}>
          <View style={s.logo}>
            <Image
              source={require("./assets/traffix-icon.png")}
              style={s.logoImg}
            />
            <Text style={s.wordmark}>
              traffix<Text style={{ color: C.purple }}>.</Text>
            </Text>
          </View>
          <Pressable
            onPress={() => setTab("Settings")}
            accessibilityRole="button"
            accessibilityLabel="Connection settings"
            style={s.status}
          >
            <View
              style={[
                s.dot,
                { backgroundColor: online ? "#119A75" : "#B6AFC0" },
              ]}
            />
            <Text style={s.statusText}>{status}</Text>
          </Pressable>
        </View>
        <ScrollView
          key={pathname}
          contentContainerStyle={s.content}
          keyboardShouldPersistTaps="handled"
        >
          {profileLoaded ? <Slot /> : <ActivityIndicator accessibilityLabel="Loading your profile" color={C.purple} />}
        </ScrollView>
        {state.offer && tab !== "Ride" && (
          <Pressable
            style={s.notice}
            onPress={() => setTab("Ride")}
            accessibilityRole="button"
            accessibilityLabel="Review route option"
          >
            <Text style={s.noticeText}>
              A route option is ready · Review your ride →
            </Text>
          </Pressable>
        )}
        {!!state.notice && tab === "Ride" && (
          <View style={s.notice}>
            <Text style={s.noticeText} accessibilityLiveRegion="polite">
              {state.notice}
            </Text>
          </View>
        )}
        <View style={s.tabs}>
          {(["Home", "Ride", "Learn", "Settings"] as Tab[]).map((t) => (
            <Pressable
              key={t}
              onPress={() => setTab(t)}
              accessibilityRole="tab"
              accessibilityState={{ selected: tab === t }}
              style={[s.tab, tab === t && s.activeTab]}
            >
              <Icon name={t} color={tab === t ? C.purple : C.muted} />
              <Text
                style={[s.tabText, { color: tab === t ? C.purple : C.muted }]}
              >
                {t}
              </Text>
              {t === "Ride" && state.offer && <View style={s.alertDot} />}
            </Pressable>
          ))}
        </View>
        <Modal
          visible={joinOpen}
          animationType="slide"
          onRequestClose={() => {
            setJoinOpen(false);
            setScanning(false);
          }}
        >
          <SafeAreaView style={s.safe}>
            <KeyboardAvoidingView
              style={{ flex: 1 }}
              behavior={Platform.OS === "ios" ? "padding" : undefined}
            >
              <ScrollView
                contentContainerStyle={s.content}
                keyboardShouldPersistTaps="handled"
              >
                <Pressable
                  onPress={() => {
                    setJoinOpen(false);
                    setScanning(false);
                  }}
                  style={s.linkRow}
                  accessibilityRole="button"
                  accessibilityLabel="Back"
                >
                  <Icon name="Back" />
                  <Text style={s.h2}>Back</Text>
                </Pressable>
                <Text style={s.eyebrow}>ONE PHONE. ONE VEHICLE.</Text>
                <Text style={s.h1}>Let’s link your ride.</Text>
                <Text style={s.body}>
                  Ask the operator for a fresh vehicle invitation. Scan the QR
                  or paste its code.
                </Text>
                {scanning && permission?.granted ? (
                  <View
                    style={{
                      height: 300,
                      borderRadius: 24,
                      overflow: "hidden",
                      marginVertical: 20,
                    }}
                  >
                    <CameraView
                      style={{ flex: 1 }}
                      barcodeScannerSettings={{ barcodeTypes: ["qr"] }}
                      onBarcodeScanned={(e) => {
                        if (scanned.current) return;
                        scanned.current = true;
                        try {
                          const p = invitation(e.data);
                          setCode(p.code);
                          if (p.server) setDraftServer(p.server);
                          setScanning(false);
                          setError("");
                        } catch (err) {
                          setScanning(false);
                          setError((err as Error).message);
                        }
                      }}
                    />
                  </View>
                ) : (
                  <Pressable
                    style={[
                      s.card,
                      {
                        backgroundColor: C.lavender,
                        alignItems: "center",
                        gap: 12,
                      },
                    ]}
                    onPress={async () => {
                      scanned.current = false;
                      const p = permission?.granted
                        ? permission
                        : await requestPermission();
                      if (p.granted) setScanning(true);
                      else
                        setError(
                          "Camera access is off. Paste the code instead.",
                        );
                    }}
                  >
                    <Icon name="Scan" size={42} color={C.purple} />
                    <Text style={s.h2}>Scan an invitation</Text>
                  </Pressable>
                )}
                <Text style={s.label}>LAPTOP ADDRESS</Text>
                <TextInput
                  style={s.input}
                  accessibilityLabel="Join server address"
                  value={draftServer}
                  onChangeText={setDraftServer}
                  keyboardType="url"
                  autoCapitalize="none"
                  autoCorrect={false}
                />
                <Text style={s.label}>YOUR JOIN CODE OR LINK</Text>
                <TextInput
                  style={s.input}
                  accessibilityLabel="Vehicle join code"
                  value={code}
                  onChangeText={setCode}
                  placeholder="Paste the invitation"
                  autoCapitalize="none"
                  autoCorrect={false}
                />
                {error && <Text style={s.error}>{error}</Text>}
                <Button
                  label={working ? "Joining your ride…" : "Join my vehicle"}
                  disabled={working || !code.trim() || !!state.claim}
                  onPress={join}
                />
                {working && (
                  <ActivityIndicator
                    style={{ marginTop: 16 }}
                    color={C.purple}
                  />
                )}
                <Text style={s.footnote}>
                  Invitations expire after two minutes and can be used once.
                  Joining never turns sharing on automatically.
                </Text>
              </ScrollView>
            </KeyboardAvoidingView>
          </SafeAreaView>
        </Modal>
        <Modal
          visible={lesson !== null}
          animationType="slide"
          onRequestClose={() => setLesson(null)}
        >
          <SafeAreaView
            style={[s.safe, { backgroundColor: lessons[lesson ?? 0].color }]}
          >
            <ScrollView key={lesson ?? "closed"} contentContainerStyle={s.content}>
              <Pressable
                style={s.linkRow}
                onPress={() => setLesson(null)}
                accessibilityLabel="Close lesson"
              >
                <Icon name="Back" />
                <Text style={s.h2}>Back</Text>
              </Pressable>
              <LessonDetail key={lesson ?? 0} index={lesson ?? 0} onClose={() => setLesson(null)} />
            </ScrollView>
          </SafeAreaView>
        </Modal>

      </SafeAreaView>
    </DriverContext.Provider>
  );
}
export default function App() {
  return (
    <SafeAreaProvider>
      <Main />
    </SafeAreaProvider>
  );
}
