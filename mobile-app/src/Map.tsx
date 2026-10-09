import React from "react";
import { View, Text, StyleSheet } from "react-native";
import Svg, { Polyline, Circle } from "react-native-svg";
import type { World, Frame, Own } from "./protocol";
export function TripMap({
  world,
  frame,
  own,
  fresh,
}: {
  world: World | null;
  frame: Frame | null;
  own: Own | null;
  fresh: boolean;
}) {
  const pose = frame?.payload.pose,
    center = pose ? [pose.x_m, pose.y_m] : [0, 0];
  const point = (p: number[]) =>
    `${150 + (p[0] - center[0]) * 0.6},${120 - (p[1] - center[1]) * 0.6}`;
  const roads =
    world?.roads
      .filter(
        (r) =>
          !r.internal &&
          r.shape.some(
            (p) =>
              Math.abs(p[0] - center[0]) < 320 &&
              Math.abs(p[1] - center[1]) < 260,
          ),
      )
      .slice(0, 100) || [];
  return (
    <View style={s.wrap}>
      <Svg width="100%" height="250" viewBox="0 0 300 240">
        {roads.map((r, i) => (
          <Polyline
            key={"b" + i}
            points={r.shape.map(point).join(" ")}
            stroke="#DDE1DC"
            strokeWidth={Math.max(4, r.width * 0.6 + 3)}
            fill="none"
          />
        ))}
        {roads.map((r, i) => (
          <Polyline
            key={i}
            points={r.shape.map(point).join(" ")}
            stroke="#FFFDF6"
            strokeWidth={Math.max(2, r.width * 0.6)}
            fill="none"
          />
        ))}
        {own?.route_path.map((p, i) => (
          <Polyline
            key={"r" + i}
            points={p.map(point).join(" ")}
            stroke={own.route_id === "route.demo.B" ? "#09856E" : "#6C4DFF"}
            strokeWidth={3}
            fill="none"
            strokeDasharray="5,3"
          />
        ))}
        {pose && fresh && (
          <>
            <Circle cx={150} cy={120} r={20} fill="#6C4DFF22" />
            <Circle
              cx={150}
              cy={120}
              r={8}
              fill="#6C4DFF"
              stroke="white"
              strokeWidth={3}
            />
          </>
        )}
      </Svg>
      <Text style={s.label}>
        {fresh ? "YOUR SIMULATED POSITION" : "WAITING FOR FRESH POSITION"}
      </Text>
      <Text style={s.credit}>
        © OpenStreetMap contributors · local geometry
      </Text>
    </View>
  );
}
const s = StyleSheet.create({
  wrap: {
    backgroundColor: "#EAF0E5",
    borderRadius: 24,
    overflow: "hidden",
    marginVertical: 16,
  },
  label: {
    position: "absolute",
    top: 16,
    left: 14,
    fontSize: 10,
    fontWeight: "700",
    color: "#36513B",
    backgroundColor: "#FFFFFFDD",
    padding: 7,
    borderRadius: 9,
  },
  credit: { fontSize: 9, color: "#51654F", padding: 10, textAlign: "right" },
});
