import React from "react";
import { View, Text, StyleSheet, Pressable } from "react-native";
import Svg, { Path } from "react-native-svg";
export const C = {
  ink: "#26243C",
  muted: "#655D78",
  purple: "#6C4DFF",
  cream: "#FFFCF7",
  mint: "#D8F5EA",
  peach: "#FFE4D6",
  lavender: "#EEE8FF",
  yellow: "#FFF0BB",
};
export type Tab = "Home" | "Ride" | "Learn" | "Settings";
const paths: Record<string, string> = {
  Home: "M3 10 12 3l9 7v11h-6v-7H9v7H3Z",
  Ride: "M5 16 3 13l2-7h14l2 7-2 3M5 16v4M19 16v4M3 13h18M7 16h1M16 16h1",
  Learn: "M3 4h7l2 2 2-2h7v15h-7l-2 2-2-2H3ZM12 6v15",
  Settings: "M4 7h16M4 17h16M8 4v6M16 14v6",
  Arrow: "M4 12h16M14 6l6 6-6 6",
  Link: "M9 15l6-6M7 14l-2 2a3 3 0 0 0 4 4l4-4M11 8l4-4a3 3 0 0 1 4 4l-2 2",
  Leaf: "M20 3C7 2 2 8 5 15c5 7 15 0 15-12ZM5 20 16 7",
  Back: "M15 5l-7 7 7 7",
  Scan: "M8 3H3v5M16 3h5v5M3 16v5h5M21 16v5h-5M7 7h4v4H7ZM14 7h3v3h-3ZM14 14h3v3h-3ZM7 14h3v3H7Z",
};
export function Icon({
  name,
  color = C.ink,
  size = 24,
}: {
  name: string;
  color?: string;
  size?: number;
}) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Path
        d={paths[name] || paths.Link}
        stroke={color}
        strokeWidth={1.8}
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </Svg>
  );
}
export function Button({
  label,
  onPress,
  disabled = false,
  secondary = false,
}: {
  label: string;
  onPress: () => void;
  disabled?: boolean;
  secondary?: boolean;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled }}
      onPress={onPress}
      disabled={disabled}
      style={[
        s.button,
        secondary && s.secondary,
        disabled && { opacity: 0.45 },
      ]}
    >
      <Text style={[s.buttonText, secondary && { color: C.purple }]}>
        {label}
      </Text>
      <Icon name="Arrow" color={secondary ? C.purple : "#FFF"} size={20} />
    </Pressable>
  );
}
export function Card({
  children,
  color = "#FFF",
}: {
  children: React.ReactNode;
  color?: string;
}) {
  return <View style={[s.card, { backgroundColor: color }]}>{children}</View>;
}
export const lessons = [
  {
    title: "Keep the junction clear",
    tag: "AT THE SIGNAL",
    color: C.mint,
    text: "Enter only when there is room beyond the crossing. A green signal cannot clear a blocked exit. Give pedestrians their space.",
  },
  {
    title: "A smoother pace",
    tag: "ON YOUR WAY",
    color: C.yellow,
    text: "Leave a steady gap and avoid unnecessary acceleration and hard braking. Follow the posted speed limit. Never speed up to catch a changing light.",
  },
  {
    title: "A route is your choice",
    tag: "TRAFFIC GUIDANCE",
    color: C.lavender,
    text: "Review directions before moving or ask a passenger. The prototype proposes an alternate route only when the operator has evidence. A suggestion changes nothing until you accept and the server confirms.",
  },
  {
    title: "What carbon saved means",
    tag: "YOUR IMPACT",
    color: C.peach,
    text: "We compare completed, matching simulated journeys before estimating avoided tailpipe emissions. An unavailable estimate means we do not have that comparison. Electric tailpipe emissions and lifecycle emissions are different.",
  },
];
export const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: C.cream },
  header: {
    flexWrap: "wrap",
    gap: 8,
    paddingHorizontal: 22,
    paddingTop: 10,
    paddingBottom: 14,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  logo: { flexDirection: "row", gap: 8, alignItems: "center" },
  logoImg: { width: 30, height: 30, borderRadius: 9 },
  wordmark: { fontSize: 24, fontWeight: "900", letterSpacing: -1 },
  status: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    backgroundColor: "#F0ECF4",
    paddingHorizontal: 10,
    paddingVertical: 9,
    borderRadius: 20,
  },
  dot: { width: 6, height: 6, borderRadius: 3 },
  statusText: { fontSize: 10, color: C.muted, fontWeight: "600" },
  content: { padding: 22, paddingBottom: 36 },
  eyebrow: {
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 1.3,
    color: C.muted,
    marginBottom: 10,
  },
  h1: {
    fontSize: 32,
    fontWeight: "800",
    color: C.ink,
    letterSpacing: -1,
    marginBottom: 8,
  },
  h2: { fontSize: 19, fontWeight: "800", color: C.ink, letterSpacing: -0.3 },
  body: {
    fontSize: 14,
    lineHeight: 22,
    color: C.muted,
    marginTop: 7,
    marginBottom: 10,
  },
  hero: {
    marginTop: 22,
    borderRadius: 28,
    backgroundColor: C.lavender,
    overflow: "hidden",
    marginBottom: 26,
  },
  heroTop: { padding: 22, paddingBottom: 0 },
  heroTag: {
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 1.4,
    color: C.purple,
    marginBottom: 12,
  },
  heroTitle: {
    fontSize: 31,
    fontWeight: "800",
    lineHeight: 36,
    color: C.ink,
    letterSpacing: -0.8,
  },
  heroBody: {
    fontSize: 14,
    lineHeight: 21,
    color: "#6A5D8A",
    marginTop: 10,
    maxWidth: 270,
  },
  heroArt: { width: "100%", height: 200 },
  button: {
    minHeight: 54,
    backgroundColor: C.purple,
    borderRadius: 17,
    paddingHorizontal: 18,
    paddingVertical: 14,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 10,
  },
  buttonText: { fontSize: 15, fontWeight: "800", color: "#FFF", flexShrink: 1 },
  secondary: {
    backgroundColor: C.lavender,
    borderWidth: 1,
    borderColor: "#DCCFFF",
  },
  card: {
    padding: 20,
    borderRadius: 23,
    marginVertical: 10,
    borderWidth: 1,
    borderColor: "#EFEAF0",
  },
  grid: { flexDirection: "row", gap: 12, marginBottom: 10 },
  tile: { flex: 1, padding: 18, borderRadius: 22, minHeight: 145 },
  metric: {
    fontSize: 34,
    fontWeight: "800",
    color: C.ink,
    marginVertical: 10,
    letterSpacing: -1,
  },
  tileTitle: { fontSize: 14, fontWeight: "800", color: C.ink, marginBottom: 4 },
  small: { fontSize: 12, lineHeight: 18, color: C.muted, marginTop: 4 },
  sectionHeading: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 14,
  },
  textLink: { fontSize: 12, fontWeight: "800", color: C.purple },
  linkRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 10,
    marginVertical: 16,
  },
  footnote: {
    fontSize: 11,
    lineHeight: 18,
    color: C.muted,
    textAlign: "center",
    marginTop: 18,
  },
  shareRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    marginBottom: 8,
  },
  tabs: {
    flexDirection: "row",
    backgroundColor: "#FFF",
    borderTopWidth: 1,
    borderTopColor: "#EEE9F0",
    paddingHorizontal: 14,
    paddingVertical: 9,
    gap: 5,
  },
  tab: {
    flex: 1,
    minHeight: 55,
    alignItems: "center",
    justifyContent: "center",
    gap: 4,
    borderRadius: 15,
  },
  activeTab: { backgroundColor: C.lavender },
  tabText: { fontSize: 10, fontWeight: "700" },
  alertDot: {
    position: "absolute",
    right: 15,
    top: 5,
    width: 7,
    height: 7,
    borderRadius: 4,
    backgroundColor: "#EA7952",
  },
  input: {
    minHeight: 54,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "#DDD5E7",
    backgroundColor: "#FFF",
    padding: 15,
    color: C.ink,
    fontSize: 14,
    marginVertical: 12,
  },
  label: {
    fontSize: 10,
    color: C.muted,
    fontWeight: "800",
    letterSpacing: 1,
    marginTop: 14,
  },
  error: {
    fontSize: 13,
    lineHeight: 20,
    color: "#AC375A",
    backgroundColor: "#FFE4EB",
    padding: 14,
    borderRadius: 14,
    marginVertical: 12,
  },
  notice: {
    marginHorizontal: 16,
    marginBottom: 7,
    backgroundColor: "#EDE7F8",
    borderRadius: 14,
    padding: 12,
  },
  noticeText: { fontSize: 12, lineHeight: 18, color: "#574478" },
});
