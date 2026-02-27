import type {
  AgentActivityEvent,
  AgentActivityMeta,
  AgentActivityStage,
  AgentActivityStatus,
} from "@/components/chat/types";

const INTAKE_STAGE_LABEL = "Understanding question";

function buildEventId(turnId: string, stage: AgentActivityStage): string {
  return `${turnId}-${stage}`;
}

function nowIso(): string {
  return new Date().toISOString();
}

export type UpsertTurnStageEventInput = {
  turnId: string;
  stage: AgentActivityStage;
  status: AgentActivityStatus;
  label: string;
  startedAt?: string;
  endedAt?: string;
  details?: string;
  meta?: AgentActivityMeta;
};

export function buildInitialTurnEvents(turnId: string, startedAt: string = nowIso()): AgentActivityEvent[] {
  return [
    {
      id: buildEventId(turnId, "intake"),
      turnId,
      stage: "intake",
      status: "running",
      label: INTAKE_STAGE_LABEL,
      startedAt,
    },
  ];
}

export function upsertTurnStageEvent(
  events: AgentActivityEvent[],
  input: UpsertTurnStageEventInput
): AgentActivityEvent[] {
  const eventId = buildEventId(input.turnId, input.stage);
  const existingEvent = events.find((event) => event.id === eventId);

  const nextEvent: AgentActivityEvent = {
    id: eventId,
    turnId: input.turnId,
    stage: input.stage,
    status: input.status,
    label: input.label,
    startedAt: input.startedAt ?? existingEvent?.startedAt ?? nowIso(),
  };

  const endedAt = input.endedAt ?? existingEvent?.endedAt;
  if (endedAt !== undefined) {
    nextEvent.endedAt = endedAt;
  }

  const details = input.details ?? existingEvent?.details;
  if (details !== undefined) {
    nextEvent.details = details;
  }

  const meta = input.meta ?? existingEvent?.meta;
  if (meta !== undefined) {
    nextEvent.meta = meta;
  }

  if (!existingEvent) {
    return [...events, nextEvent];
  }

  return events.map((event) => (event.id === eventId ? nextEvent : event));
}
