// Renderer Layer (docs/architecture.md)
// 책임: JoinGraph(JSON) -> 화면 좌표 모델. 순수 함수 — Component 밖 (docs/ui.md).
// SQL/AST 해석은 하지 않는다. 분석은 Analysis Layer에서 끝났다.

import type { JoinGraph, JoinGraphEdge, JoinGraphNode } from "../types";

export interface PositionedNode extends JoinGraphNode {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface PositionedEdge extends JoinGraphEdge {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  labelX: number;
  labelY: number;
}

export interface GraphLayout {
  width: number;
  height: number;
  nodes: PositionedNode[];
  edges: PositionedEdge[];
}

const NODE_HEIGHT = 44;
const CHAR_WIDTH = 8;
const NODE_PADDING = 24;
const MIN_NODE_WIDTH = 90;

function nodeLabel(n: JoinGraphNode): string {
  if (n.kind === "subquery") return n.alias ?? "(subquery)";
  return n.alias && n.alias !== n.table ? `${n.table} (${n.alias})` : (n.table ?? n.id);
}

function nodeWidth(n: JoinGraphNode): number {
  return Math.max(MIN_NODE_WIDTH, nodeLabel(n).length * CHAR_WIDTH + NODE_PADDING);
}

/**
 * 원형 배치. 노드가 1~2개면 수평 배치.
 * 접점이 많은 노드(허브)를 먼저 배치해 엣지 교차를 줄인다.
 */
export function layoutJoinGraph(graph: JoinGraph): GraphLayout {
  const n = graph.nodes.length;
  const width = Math.max(480, 200 + n * 110);
  const height = Math.max(320, 160 + n * 60);
  const cx = width / 2;
  const cy = height / 2;

  // 연결 수 내림차순 정렬 후 각도 배치 (허브가 12시 방향)
  const degree = new Map<string, number>();
  for (const e of graph.edges) {
    degree.set(e.source, (degree.get(e.source) ?? 0) + 1);
    degree.set(e.target, (degree.get(e.target) ?? 0) + 1);
  }
  const ordered = [...graph.nodes].sort(
    (a, b) => (degree.get(b.id) ?? 0) - (degree.get(a.id) ?? 0),
  );

  const radiusX = Math.max(120, width / 2 - 120);
  const radiusY = Math.max(80, height / 2 - 70);

  const nodes: PositionedNode[] = ordered.map((node, i) => {
    let x = cx;
    let y = cy;
    if (n === 1) {
      // 중앙
    } else if (n === 2) {
      x = cx + (i === 0 ? -radiusX / 1.5 : radiusX / 1.5);
    } else {
      const angle = (2 * Math.PI * i) / n - Math.PI / 2;
      x = cx + radiusX * Math.cos(angle);
      y = cy + radiusY * Math.sin(angle);
    }
    return { ...node, x, y, width: nodeWidth(node), height: NODE_HEIGHT };
  });

  const byId = new Map(nodes.map((node) => [node.id, node]));
  const edges: PositionedEdge[] = [];
  for (const e of graph.edges) {
    const s = byId.get(e.source);
    const t = byId.get(e.target);
    if (!s || !t) continue;
    edges.push({
      ...e,
      x1: s.x,
      y1: s.y,
      x2: t.x,
      y2: t.y,
      labelX: (s.x + t.x) / 2,
      labelY: (s.y + t.y) / 2,
    });
  }

  return { width, height, nodes, edges };
}

export { nodeLabel };
