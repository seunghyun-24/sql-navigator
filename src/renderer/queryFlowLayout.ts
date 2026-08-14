// Renderer Layer (docs/architecture.md)
// 책임: DataFlow(JSON) -> 화면 좌표 모델. 순수 함수 — Component 밖 (docs/ui.md).
// scope(main / cte:* / sub:*)별로 lane을 나누고, lane 안에서는 생성 순서
// (= 논리 실행 순서)대로 위에서 아래로 쌓는다. CTE/서브쿼리 lane이 왼쪽,
// main이 오른쪽 — 데이터가 왼쪽에서 오른쪽으로 흘러들어온다.

import type { DataFlow, FlowEdge, FlowStep } from "../types";

export interface PositionedStep extends FlowStep {
  x: number; // 중심 좌표
  y: number;
  width: number;
  height: number;
}

export interface PositionedFlowEdge extends FlowEdge {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  sameLane: boolean;
}

export interface FlowLayout {
  width: number;
  height: number;
  steps: PositionedStep[];
  edges: PositionedFlowEdge[];
  lanes: { scope: string; x: number; width: number }[];
}

const NODE_HEIGHT = 46;
const V_GAP = 20;
const LANE_GAP = 56;
const PAD = 28;
const CHAR_WIDTH = 7;
const MIN_WIDTH = 130;
const MAX_WIDTH = 250;

function stepWidth(s: FlowStep): number {
  const chars = Math.max(s.label.length, Math.min(s.detail.length, 32));
  return Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, chars * CHAR_WIDTH + 28));
}

export function layoutQueryFlow(flow: DataFlow): FlowLayout {
  // scope 등장 순서 유지, main은 항상 마지막(오른쪽) lane
  const scopes: string[] = [];
  for (const s of flow.steps) {
    if (s.scope !== "main" && !scopes.includes(s.scope)) scopes.push(s.scope);
  }
  scopes.push("main");

  const byScope = new Map<string, FlowStep[]>(scopes.map((sc) => [sc, []]));
  for (const s of flow.steps) byScope.get(s.scope)?.push(s);

  // lane 폭 = 해당 scope에서 가장 넓은 노드
  const lanes: { scope: string; x: number; width: number }[] = [];
  let cursorX = PAD;
  for (const scope of scopes) {
    const steps = byScope.get(scope) ?? [];
    if (steps.length === 0) continue;
    const width = Math.max(...steps.map(stepWidth));
    lanes.push({ scope, x: cursorX + width / 2, width });
    cursorX += width + LANE_GAP;
  }
  const laneX = new Map(lanes.map((l) => [l.scope, l.x]));

  const steps: PositionedStep[] = [];
  let maxY = 0;
  for (const scope of scopes) {
    const list = byScope.get(scope) ?? [];
    list.forEach((s, i) => {
      const y = PAD + i * (NODE_HEIGHT + V_GAP) + NODE_HEIGHT / 2;
      maxY = Math.max(maxY, y + NODE_HEIGHT / 2);
      steps.push({
        ...s,
        x: laneX.get(scope) ?? PAD,
        y,
        width: stepWidth(s),
        height: NODE_HEIGHT,
      });
    });
  }

  const byId = new Map(steps.map((s) => [s.id, s]));
  const edges: PositionedFlowEdge[] = [];
  for (const e of flow.edges) {
    const s = byId.get(e.source);
    const t = byId.get(e.target);
    if (!s || !t) continue;
    const sameLane = s.scope === t.scope;
    edges.push(
      sameLane
        ? { ...e, x1: s.x, y1: s.y + s.height / 2, x2: t.x, y2: t.y - t.height / 2, sameLane }
        : {
            ...e,
            x1: s.x + s.width / 2, // lane 간 연결은 좌우 측면으로
            y1: s.y,
            x2: t.x - t.width / 2,
            y2: t.y,
            sameLane,
          },
    );
  }

  return {
    width: Math.max(480, cursorX - LANE_GAP + PAD),
    height: Math.max(280, maxY + PAD),
    steps,
    edges,
    lanes,
  };
}
