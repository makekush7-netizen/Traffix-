import React, { useState } from "react";
import { View, Text, Image, Pressable } from "react-native";
import { C, s, lessons, Button, Card } from "./ui";
import { useDriver } from "./driver-context";
export const lessonArt = [
  require("../assets/lesson-junction.png"), require("../assets/lesson-pace.png"),
  require("../assets/lesson-route.png"), require("../assets/lesson-impact.png"),
];
export const lessonDescriptions = [
  "A car waits before a crossing until there is space at the exit.",
  "Vehicles leave a generous following gap on the same road.",
  "A driver can review two road options before setting off.",
  "Vehicles and green trees illustrate environmental impact.",
];
const checks = [
  { question: "Green signal, but the exit is blocked. What helps?", choices: ["Wait before the junction", "Move into the crossing"], answer: 0, why: "Keep the crossing clear until there is room beyond it." },
  { question: "The light ahead is changing. What should you do?", choices: ["Accelerate to catch it", "Keep a safe pace and gap"], answer: 1, why: "A steady, safe pace matters more than catching a signal." },
  { question: "When does an accepted route change take effect?", choices: ["As soon as a suggestion appears", "After the server confirms it"], answer: 1, why: "Suggestions are optional. The simulation must confirm the change." },
  { question: "No matched completed comparison. What is CO₂ saved?", choices: ["Unavailable for now", "A guessed positive number"], answer: 0, why: "We need a matching baseline and completed journey before reporting savings." },
];
export function LessonDetail({ index, onClose }: { index: number; onClose: () => void }) {
  const { profile, updateProfile } = useDriver();
  const [selected, setSelected] = useState<number | null>(null);
  const l = lessons[index], check = checks[index], correct = selected === check.answer;
  return <>
    <Text style={s.eyebrow}>{l.tag} · {index + 1} / {lessons.length}</Text>
    <Text style={s.h1}>{l.title}</Text>
    {profile.illustrations && <Image source={lessonArt[index]} accessibilityLabel={lessonDescriptions[index]} accessible style={{ width: "100%", height: 230, marginVertical: 12 }} resizeMode="contain" />}
    <Text style={[s.body, { fontSize: 18, lineHeight: 29 }]}>{l.text}</Text>
    <Card>
      <Text style={s.eyebrow}>A QUICK CHECK</Text>
      <Text style={s.h2}>{check.question}</Text>
      <View style={{ gap: 10, marginTop: 16 }}>
        {check.choices.map((choice, i) => <Pressable key={choice} accessibilityRole="radio" accessibilityState={{ checked: selected === i }} onPress={() => setSelected(i)} style={[s.input, { borderColor: selected === i ? C.purple : "#DDD6EB", backgroundColor: selected === i ? C.lavender : C.cream, marginVertical: 0 }]}><Text style={[s.body, { marginVertical: 0, color: C.ink }]}>{choice}</Text></Pressable>)}
      </View>
      {selected !== null && <Text accessibilityLiveRegion="polite" style={s.body}>{correct ? "That’s right. " : "Try again. "}{check.why}</Text>}
    </Card>
    <Button label={profile.learned.includes(index) ? "Done · Back to learning" : "Save lesson as learned"} disabled={!correct} onPress={() => { updateProfile(p => ({ ...p, learned: [...new Set([...p.learned, index])] })); onClose(); }} />
    <Pressable accessibilityRole="button" onPress={onClose} style={[s.linkRow, { justifyContent: "center" }]}><Text style={s.textLink}>Finish later</Text></Pressable>
    <Text style={s.footnote}>Read while stationary. Illustrations explain an idea, not a live road condition.</Text>
  </>;
}
