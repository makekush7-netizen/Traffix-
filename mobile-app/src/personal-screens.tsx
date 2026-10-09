import React, { useState } from "react";
import { View, Text, TextInput, Pressable, Alert } from "react-native";
import { router } from "expo-router";
import { useDriver } from "./driver-context";
import { C, s, Card, Button, Icon } from "./ui";
import { avatars, vehicles, profileName, newProfile } from "./profile";
function Back() { return <Pressable accessibilityRole="button" accessibilityLabel="Back to settings" onPress={() => router.replace("/settings")} style={s.linkRow}><Icon name="Back"/><Text style={s.textLink}>Settings</Text></Pressable>; }
export function ProfileScreen() {
  const { profile, profileLoaded, updateProfile, profileError } = useDriver();
  const [name, setName] = useState(profile.name);
  const [avatar, setAvatar] = useState(profile.avatar);
  const [vehicle, setVehicle] = useState(profile.vehicle);
  const [error, setError] = useState("");
  return <><Back/><Text style={s.eyebrow}>MAKE IT YOURS</Text><Text style={s.h1}>Your profile.</Text><Text style={s.body}>A little personality for every journey. Saved only on this device.</Text>
    <Card color={C.lavender}><Text style={{ fontSize: 56, textAlign: "center" }}>{avatar}</Text><Text style={[s.h2, { textAlign: "center", marginTop: 12 }]}>{name.trim() || "Your name here"}</Text><Text style={[s.small, { textAlign: "center" }]}>Traffix traveller · Local profile</Text></Card>
    <Text style={s.label}>YOUR NAME</Text><TextInput style={s.input} accessibilityLabel="Your profile name" value={name} onChangeText={setName} placeholder="e.g. Kush" maxLength={64} autoCapitalize="words" />
    <Text style={s.label}>CHOOSE AN AVATAR</Text><View style={[s.grid, { flexWrap: "wrap" }]}>{avatars.map(a => <Pressable key={a} accessibilityRole="radio" accessibilityLabel={`Avatar ${a}`} accessibilityState={{ checked: avatar === a }} onPress={() => setAvatar(a)} style={{ minHeight: 58, minWidth: 58, padding: 12, borderRadius: 18, borderWidth: 2, borderColor: avatar === a ? C.purple : "#E8E1ED", backgroundColor: avatar === a ? C.lavender : "#FFF" }}><Text style={{ fontSize: 26 }}>{a}</Text></Pressable>)}</View>
    <Text style={s.label}>USUALLY TRAVELLING BY</Text><View style={[s.grid, { flexWrap: "wrap" }]}>{vehicles.map(v => <Pressable key={v} accessibilityRole="radio" accessibilityState={{ checked: vehicle === v }} onPress={() => setVehicle(v)} style={{ padding: 16, minHeight: 50, borderRadius: 16, backgroundColor: vehicle === v ? C.lavender : "#FFF", borderWidth: 1, borderColor: vehicle === v ? C.purple : "#E8E1ED" }}><Text style={{ color: C.ink, fontWeight: "700" }}>{v}</Text></Pressable>)}</View>
    <Text style={s.small}>This preference never changes your operator-assigned simulation vehicle.</Text>
    {!!(error || profileError) && <Text accessibilityLiveRegion="polite" style={s.error}>{error || profileError}</Text>}
    <View style={{ marginTop: 20 }}><Button label="Save my profile" disabled={!profileLoaded} onPress={() => { try { const clean = profileName(name); updateProfile(p => ({ ...p, name: clean, avatar, vehicle })); setError(""); router.replace("/settings"); } catch (e) { setError((e as Error).message); } }} /></View>
    <Card><Text style={s.h2}>About your account</Text><Text style={s.body}>This is a local profile, with no email, password or cloud account yet. Vehicle access uses a separate secure invitation from the operator.</Text></Card>
    <Button secondary label="Erase local profile & activity" disabled={!profileLoaded} onPress={() => Alert.alert("Erase your local profile?", "This clears your name, preferences, lessons and ride history on this phone. It does not leave your current vehicle or delete operator records.", [{ text: "Keep", style: "cancel" }, { text: "Erase", style: "destructive", onPress: () => { updateProfile(() => newProfile()); setName(""); setAvatar(avatars[0]); setVehicle("Passenger"); } }])} />
  </>;
}
export function ImpactScreen() {
  const { profile, setLesson } = useDriver();
  const completed = profile.rides.filter(r => r.arrived).length;
  const samples = profile.rides.reduce((sum, r) => sum + r.samples, 0);
  return <><Back/><Text style={s.eyebrow}>SMALL CHOICES ADD UP</Text><Text style={s.h1}>{profile.name ? `${profile.name}’s impact.` : "Your impact."}</Text>
    <Card color={C.mint}><Icon name="Leaf" color="#137D62" size={36}/><Text style={s.metric}>— <Text style={{ fontSize: 18 }}>kg CO₂</Text></Text><Text style={s.h2}>Savings waiting for evidence</Text><Text style={s.body}>Your app is ready to show avoided tailpipe emissions once the host provides a verified completed-trip comparison. No estimate is available in this preview.</Text><Button secondary label="Understand the calculation" onPress={() => setLesson(3)} /></Card>
    <View style={s.grid}><View style={[s.tile, { backgroundColor: C.lavender }]}><Text style={s.metric}>{completed}</Text><Text style={s.tileTitle}>Arrivals observed</Text></View><View style={[s.tile, { backgroundColor: C.peach }]}><Text style={s.metric}>{samples}</Text><Text style={s.tileTitle}>Samples confirmed</Text></View></View>
    <Card><Text style={s.h2}>Road sense progress</Text><Text style={s.body}>{profile.learned.length} of 4 lessons learned</Text><View style={{ height: 8, borderRadius: 4, backgroundColor: C.lavender }}><View style={{ height: 8, borderRadius: 4, backgroundColor: C.purple, width: `${profile.learned.length * 25}%` }}/></View></Card>
    <Text style={[s.h2, { marginTop: 24 }]}>Recent simulation activity</Text><Text style={s.small}>Last 20 vehicles observed on this device. These are simulated trips, not real GPS journeys.</Text>
    {profile.rides.length === 0 ? <Card><Text style={s.h2}>Your first ride starts here.</Text><Text style={s.body}>Link a vehicle to begin your own activity record.</Text></Card> : [...profile.rides].reverse().map(r => <Card key={r.id}><Text style={s.h2}>{r.role}</Text><Text style={s.body}>{r.arrived ? "Arrival observed" : "Joined · completion not observed"}</Text><Text style={s.small}>{new Date(r.date).toLocaleDateString()} · {r.samples} confirmed samples</Text></Card>)}
    <Text style={s.footnote}>Counters are local records. Leaving, losing connection or resetting a simulation does not count as completing a trip. CO₂ and time savings require host evidence.</Text>
  </>;
}
