"""Saved evidence only; no incomplete-cohort headline or seed cherry-picking."""
import argparse, csv, json, statistics, math
import xml.etree.ElementTree as ET
from pathlib import Path
from backend.simulation.results import compare_records

def valid_cohort(m):
    c=m.get('final_counts',{})
    journey=m.get('mean_journey_s')
    return (m.get('complete') is True and m.get('integrity')=='complete' and c.get('scheduled',0)>0 and c.get('arrived')==c.get('scheduled') and c.get('collisions')==0 and c.get('teleports')==0 and isinstance(journey,(int,float)) and not isinstance(journey,bool) and math.isfinite(journey) and journey>=0)

def build_report(paths, output):
    rows=[]; attempts=[]
    for path in paths:
        for attempt in json.loads(Path(path).read_text())["runs"]:
            attempts.append(attempt)
            m=attempt.get("manifest")
            if not m:
                rows.append({"seed":attempt["seed"],"policy":attempt["policy"],"valid":False,"reason":attempt.get("error","missing manifest")});continue
            rows.append({"seed":attempt["seed"],"policy":attempt["policy"],"run_id":m["run_id"],"valid":valid_cohort(m),"demand_per_hour":m.get("settings",{}).get("demand_per_hour"),"duration_s":m.get("settings",{}).get("duration_s"),"scheduled":m["final_counts"]["scheduled"],"arrived":m["final_counts"]["arrived"],"journey_s":m.get("mean_journey_s"),"co2_kg":m["final_counts"].get("co2_kg"),"collisions":m["final_counts"].get("collisions"),"teleports":m["final_counts"].get("teleports"),"reason":m.get("integrity")})
    for row in rows:
        if not row.get('run_id') or not row.get('valid'):continue
        tripfile=Path('runs')/row['run_id']/'trips.xml'
        if tripfile.exists():
            trips=ET.parse(tripfile).getroot().findall('tripinfo')
            if len(trips)==row['scheduled'] and all(float(t.get('arrival','-1'))>=0 for t in trips):
                waits=sorted(float(t.get('waitingTime','0')) for t in trips)
                row['mean_waiting_s']=statistics.mean(waits)
                row['p95_waiting_s']=statistics.quantiles(waits,n=100,method='inclusive')[94] if len(waits)>1 else waits[0]
                journeys=sorted(float(t.get('duration','0'))+float(t.get('departDelay','0')) for t in trips)
                row['p95_journey_s']=statistics.quantiles(journeys,n=100,method='inclusive')[94] if len(journeys)>1 else journeys[0]
        recordfile=Path('runs')/row['run_id']/'recording.json'
        if recordfile.exists():
            frames=json.loads(recordfile.read_text()).get('frames',[])
            row['sampled_peak_queued']=max((f.get('metrics',{}).get('queued',0) for f in frames),default=None)
            events=json.loads(recordfile.read_text()).get('events',[])
            row['confirmed_extensions']=sum(e.get('kind')=='signal_extension' for e in events)
            row['confirmed_phase_changes']=sum(e.get('kind')=='signal_transition_completed' for e in events)
    comparisons=[]
    for attempt in attempts:
        m=attempt.get("manifest",{})
        if not m or attempt["policy"]=="fixed":continue
        candidates=[a for a in attempts if a.get("manifest") and a["seed"]==attempt["seed"] and a["policy"]=="fixed"]
        for baseline in candidates:
            result=compare_records({"manifest":m},{"manifest":baseline["manifest"]})
            comparisons.append({"seed":attempt["seed"],"policy":attempt["policy"],**result})
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    payload={"runs":rows,"comparisons":comparisons,"assumptions":["OSM geometry; assumed mixed demand; not field-calibrated","All cohorts must arrive; zero collisions and teleports","SUMO modelled emissions, unreviewed fleet mapping","Synthetic simulation results, not Indian field effectiveness"]}
    (output/"report.json").write_text(json.dumps(payload,indent=2))
    keys=sorted(set().union(*(r.keys() for r in rows))) if rows else []
    with (output/"runs.csv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader();writer.writerows(rows)
    lines=["# Traffix measured benchmark", "", "Synthetic SUMO results; not field-calibrated. Negative outcomes and faults retained.","", "| Seed | Policy | Cohort | Integrity | Mean journey (s) | Modelled CO2 (kg) |", "|---|---|---|---|---|---|"]
    for r in rows:lines.append(f"| {r['seed']} | {r['policy']} | {r.get('arrived','?')}/{r.get('scheduled','?')} | {r['reason']} | {r.get('journey_s')} | {r.get('co2_kg')} |")
    lines += ["", "## Matched improvements (positive = better; negative = worse)", "", "| Seed | Policy | Valid comparison | Journey reduction % | CO2 reduction % |", "|---|---|---|---|---|"]
    for c in comparisons:
        d=c.get("differences") or {};lines.append(f"| {c['seed']} | {c['policy']} | {c['reason_code']} | {d.get('journey_reduction_pct')} | {d.get('co2_reduction_pct')} |")
    lines += ["", "## Waiting, tails and sampled queues", "", "P95 uses the inclusive linear percentile of completed trip XML values. Queue peaks are sampled from saved frames, not continuous maxima.", "", "| Seed | Policy | Mean stopped waiting (s) | P95 stopped waiting (s) | P95 journey (s) | Sampled peak queue |", "|---|---|---|---|---|---|"]
    def fmt(value):return f"{value:.2f}" if isinstance(value,(int,float)) else "unavailable"
    for r in rows:
        lines.append(f"| {r['seed']} | {r['policy']} | {fmt(r.get('mean_waiting_s'))} | {fmt(r.get('p95_waiting_s'))} | {fmt(r.get('p95_journey_s'))} | {fmt(r.get('sampled_peak_queued'))} |")
    for policy in sorted({c["policy"] for c in comparisons}):
        valid=[c for c in comparisons if c["policy"]==policy and c["available"]]
        if valid:
            values=[c["differences"]["journey_reduction_pct"] for c in valid]
            lines += ["",f"{policy}: {len(valid)} valid pairs; mean per-seed journey reduction {statistics.mean(values):.2f}%; range {min(values):.2f}% to {max(values):.2f}%. This is not a confidence interval."]
    (output/"report.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    return payload

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("inputs",nargs="+");p.add_argument("--output",required=True);a=p.parse_args();build_report(a.inputs,a.output)
