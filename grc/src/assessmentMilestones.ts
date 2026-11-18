type Event = { action: string; assessment?: string; creation: string };
/** Customer presentation only: retain the complete source history for staff. */
export function assessmentMilestones<T extends Event>(events: T[]): T[] {
  const milestones = new Map<string, T>();
  for (const event of events) {
    if (!event.assessment || !["Assessment started", "Submitted", "Resubmitted"].includes(event.action))
      continue;
    const started = event.action === "Assessment started";
    const key = event.assessment + ":" + (started ? "started" : "finished");
    const previous = milestones.get(key);
    if (!previous || (started ? event.creation < previous.creation : event.creation > previous.creation))
      milestones.set(key, { ...event, action: started ? "Assessment started" : "Assessment finished" });
  }
  return [...milestones.values()].sort((a, b) => b.creation.localeCompare(a.creation));
}
