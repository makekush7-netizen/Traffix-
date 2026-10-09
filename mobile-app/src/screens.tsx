import React from "react";
import { View, Text, Pressable, Image, Switch, TextInput } from "react-native";
import { useDriver } from "./driver-context";
import { C, s, Icon, Button, Card, lessons } from "./ui";
import { TripMap } from "./Map";
export function HomeScreen() {
  const { state, openJoin, setTab, setLesson } = useDriver();
  return (
    <>
      <Text style={s.eyebrow}>A LITTLE LESS STOP. A BETTER TRIP.</Text>
      <Text style={s.h1}>Hello, traveller 👋</Text>
      <Text style={s.body}>Your next journey, with a clearer picture.</Text>
      <View style={s.hero}>
        <View style={s.heroTop}>
          <Text style={s.heroTag}>LET’S GET MOVING</Text>
          <Text style={s.heroTitle}>Small choices.{"\n"}Smoother roads.</Text>
          <Text style={s.heroBody}>
            Join a drive and get guidance that follows your vehicle.
          </Text>
        </View>
        <Image
          source={require("../assets/traffic-island.png")}
          style={s.heroArt}
          resizeMode="contain"
        />
        <View style={{ padding: 20, paddingTop: 0 }}>
          <Button
            label={state.claim ? "Open your ride" : "Join a simulated ride"}
            onPress={() => (state.claim ? setTab("Ride") : openJoin())}
          />
        </View>
      </View>
      <View style={s.sectionHeading}>
        <Text style={s.h2}>Your impact</Text>
        <Pressable onPress={() => setLesson(3)}>
          <Text style={s.textLink}>How it works</Text>
        </Pressable>
      </View>
      <View style={s.grid}>
        <View style={[s.tile, { backgroundColor: C.mint }]}>
          <Icon name="Leaf" color="#137D62" />
          <Text style={s.metric}>—</Text>
          <Text style={s.tileTitle}>CO₂ saved</Text>
          <Text style={s.small}>Awaiting a matched trip</Text>
        </View>
        <View style={[s.tile, { backgroundColor: C.peach }]}>
          <Icon name="Ride" color="#B05332" />
          <Text style={s.metric}>{state.samples}</Text>
          <Text style={s.tileTitle}>Traffic samples</Text>
          <Text style={s.small}>Confirmed this session</Text>
        </View>
      </View>
      <Card>
        <Text style={s.h2}>One simple connection</Text>
        <Text style={s.body}>
          Get an invitation from your operator. Join one vehicle. Choose whether
          to share samples.
        </Text>
        <Pressable style={s.linkRow} onPress={openJoin}>
          <Text style={s.textLink}>Connect to the simulation</Text>
          <Icon name="Arrow" color={C.purple} />
        </Pressable>
      </Card>
      <Pressable
        onPress={() => setLesson(0)}
        style={[s.card, { backgroundColor: C.yellow }]}
      >
        <Text style={s.eyebrow}>GOOD TO KNOW</Text>
        <Text style={s.h2}>A green light needs a clear exit.</Text>
        <Text style={s.body}>A 30-second read for a better junction.</Text>
      </Pressable>
      <Text style={s.footnote}>
        SIMULATION PROTOTYPE · Your position comes from SUMO, not phone GPS.
      </Text>
    </>
  );
}
export function RideScreen() {
  const {
    state,
    world,
    api,
    finished,
    speed,
    readyOffer,
    online,
    active,
    openJoin,
    leave,
  } = useDriver();
  return (
    <>
      <Text style={s.eyebrow}>YOUR SIMULATED JOURNEY</Text>
      <Text style={s.h1}>
        {finished ? "You’ve arrived." : state.own?.role || "Your ride"}
      </Text>
      <Text style={s.body}>
        {state.claim
          ? state.own?.paused
            ? "The operator has paused the simulation."
            : finished
              ? "Your simulated journey is complete."
              : "Your route and advice stay with your vehicle."
          : "Join a vehicle to see its route and live speed."}
      </Text>
      {!state.claim ? (
        <>
          <Image
            source={require("../assets/traffic-island.png")}
            style={{ width: "100%", height: 250 }}
            resizeMode="contain"
          />
          <Button label="Join a vehicle" onPress={openJoin} />
        </>
      ) : (
        <>
          <TripMap
            world={world}
            frame={state.frame}
            own={state.own}
            fresh={state.fresh}
          />
          <View style={s.grid}>
            <View style={[s.tile, { backgroundColor: C.lavender }]}>
              <Text style={s.small}>CURRENT SPEED</Text>
              <Text style={s.metric}>
                {speed ?? "—"}
                <Text style={{ fontSize: 14, fontWeight: "500" }}> km/h</Text>
              </Text>
              <Text style={s.small}>
                {speed === null
                  ? "Position unavailable"
                  : speed === 0
                    ? "Vehicle stopped"
                    : "Live simulation speed"}
              </Text>
            </View>
            <View style={[s.tile, { backgroundColor: C.mint }]}>
              <Text style={s.small}>CURRENT ROUTE</Text>
              <Text style={[s.metric, { fontSize: 26 }]}>
                {state.own?.route_id === "route.demo.B"
                  ? "Route B"
                  : state.own?.route_id === "route.demo.A"
                    ? "Route A"
                    : "—"}
              </Text>
              <Text style={s.small}>
                {state.own?.route_id === "route.demo.B"
                  ? "Server-confirmed change"
                  : "Assigned by the server"}
              </Text>
            </View>
          </View>
          {state.offer && (
            <Card color={C.lavender}>
              <Text style={s.eyebrow}>A ROUTE OPTION FOR YOU</Text>
              <Text style={s.h2}>Slowdown ahead</Text>
              <Text style={s.body}>{state.offer.message}</Text>
              <Text style={s.small}>
                Time saved is unavailable. Your route stays unchanged until
                confirmation.
              </Text>
              <View style={{ marginTop: 16, gap: 10 }}>
                <Button
                  label={state.pending ? "Confirming…" : "Take Route B"}
                  onPress={() => api.decide("accept")}
                  disabled={!readyOffer || state.pending}
                />
                <Button
                  label="Keep my route"
                  onPress={() => api.decide("ignore")}
                  secondary
                  disabled={!readyOffer || state.pending}
                />
              </View>
            </Card>
          )}
          <Card>
            <View style={s.shareRow}>
              <View style={{ flex: 1 }}>
                <Text style={s.h2}>Share traffic samples</Text>
                <Text style={s.small}>
                  {state.sharing
                    ? "On · validated simulated samples"
                    : "Off · always your choice"}
                </Text>
              </View>
              <Switch
                accessibilityLabel="Share traffic samples"
                value={state.sharing}
                onValueChange={(v) => api.toggle(v)}
                disabled={!online || state.pending || (finished && !state.sharing)}
                trackColor={{ false: "#DED8E8", true: "#B7A4FF" }}
                thumbColor={state.sharing ? C.purple : "#FFF"}
              />
            </View>
            <Text style={s.small}>
              No GPS is collected. Sharing turns off when the connection or app
              session changes.
            </Text>
          </Card>
          <Card color={C.yellow}>
            <Text style={s.h2}>A steady pace is a good start.</Text>
            <Text style={s.body}>
              {finished
                ? "Your journey ended. Review your outcome with the operator."
                : speed === 0
                  ? "Wait for the signal and a safe gap. Keep crossings clear."
                  : "Leave a gap and follow the posted limit. A numeric speed recommendation needs reliable signal-arrival prediction."}
            </Text>
          </Card>
          <Button
            label="Report slow traffic"
            secondary
            disabled={!online || !state.fresh || !active}
            onPress={() => api.report()}
          />
          <Text style={s.small}>
            Reports are unverified until the operator reviews them.
          </Text>
          <Pressable onPress={leave} style={s.linkRow}>
            <Text style={{ color: "#9D4152", fontWeight: "700" }}>
              Leave this vehicle
            </Text>
          </Pressable>
          <Text style={s.footnote}>
            Review guidance before moving, or ask a passenger.
          </Text>
        </>
      )}
    </>
  );
}
export function LearnScreen() {
  const { setLesson } = useDriver();
  return (
    <>
      <Text style={s.eyebrow}>SMALL LESSONS, BETTER JOURNEYS</Text>
      <Text style={s.h1}>Road sense.</Text>
      <Text style={s.body}>Practical ideas for smoother, safer movement.</Text>
      {lessons.map((l, i) => (
        <Pressable
          key={l.title}
          onPress={() => setLesson(i)}
          style={[s.card, { backgroundColor: l.color }]}
          accessibilityRole="button"
        >
          <Text style={s.eyebrow}>{l.tag}</Text>
          <Text style={s.h2}>{l.title}</Text>
          <View style={s.linkRow}>
            <Text style={s.small}>Read the tip · under a minute</Text>
            <Icon name="Arrow" />
          </View>
        </Pressable>
      ))}
    </>
  );
}
export function SettingsScreen() {
  const {
    state,
    draftServer,
    error,
    working,
    setDraftServer,
    saveServer,
    leave,
  } = useDriver();
  return (
    <>
      <Text style={s.eyebrow}>YOU’RE IN CONTROL</Text>
      <Text style={s.h1}>Your connection.</Text>
      <Text style={s.body}>
        Connect over USB or the same network as the simulation laptop.
      </Text>
      <Card>
        <Text style={s.h2}>Simulation host</Text>
        <Text style={s.small}>
          USB forwarding: http://127.0.0.1:8004. Wi-Fi: use the laptop’s
          address.
        </Text>
        <TextInput
          accessibilityLabel="Simulation server address"
          style={s.input}
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="url"
          value={draftServer}
          onChangeText={setDraftServer}
        />
        <Button
          label={working ? "Connecting…" : "Check connection"}
          onPress={saveServer}
          disabled={working}
        />
      </Card>
      {error && (
        <Text style={s.error} accessibilityLiveRegion="polite">
          {error}
        </Text>
      )}
      <Card color={C.lavender}>
        <Text style={s.h2}>What this version does</Text>
        <Text style={s.body}>
          Connects to the current simulation host. Shows your vehicle, current
          route, optional sample sharing and accepted route advice.
        </Text>
        <Text style={s.body}>
          Works while the app is open. Background notifications and real GPS
          trips are not enabled in this preview.
        </Text>
      </Card>
      <Card>
        <Text style={s.h2}>Private by default</Text>
        <Text style={s.body}>
          Session credentials stay in Android secure storage. Your camera is
          used only when you choose to scan an invitation.
        </Text>
        {state.claim && (
          <Button label="Leave current vehicle" onPress={leave} secondary />
        )}
      </Card>
    </>
  );
}
