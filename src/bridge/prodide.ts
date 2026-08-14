// Bridge Layer (docs/architecture.md)
// 책임: Python 소스(Parser/Analysis Layer)를 Pyodide FS에 적재하고,
//       SQL 문자열을 전달해 AnalysisResult(JSON)를 반환한다.
// 원칙: 경계를 넘는 데이터는 직렬화 가능한 JSON만. AST 객체를 JS로 넘기지 않는다.
// SQL은 브라우저를 떠나지 않는다 — Pyodide/sqlglot 자산 다운로드 외 네트워크 없음.

import type { AnalysisResult, DiffResult } from "../types";

const PYODIDE_VERSION = "0.26.4";
const PYODIDE_BASE = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;
const PY_ROOT = "/sqlnav";

// Python 소스 전체를 빌드 시점에 포함 (tests 제외)
const pySources = import.meta.glob("../python/**/*.py", {
  as: "raw",
  eager: true,
}) as Record<string, string>;

interface PyodideFS {
  mkdirTree(path: string): void;
  writeFile(path: string, data: string): void;
}

interface PyodideInterface {
  FS: PyodideFS;
  loadPackage(name: string): Promise<void>;
  pyimport(name: string): { install(pkg: string): Promise<void> };
  runPython(code: string): unknown;
  globals: {
    get(
      name: string,
    ): ((...args: string[]) => string) & { destroy?: () => void };
  };
}

declare global {
  interface Window {
    loadPyodide?: (opts: { indexURL: string }) => Promise<PyodideInterface>;
  }
}

let instance: Promise<PyodideInterface> | null = null;

function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const el = document.createElement("script");
    el.src = src;
    el.onload = () => resolve();
    el.onerror = () => reject(new Error(`스크립트 로딩 실패: ${src}`));
    document.head.appendChild(el);
  });
}

function writePythonSources(pyodide: PyodideInterface): void {
  pyodide.FS.mkdirTree(`${PY_ROOT}/rules`);
  for (const [path, source] of Object.entries(pySources)) {
    const rel = path.split("/python/")[1];
    if (!rel || rel.startsWith("tests/")) continue;
    pyodide.FS.writeFile(`${PY_ROOT}/${rel}`, source);
  }
}

async function init(): Promise<PyodideInterface> {
  if (!window.loadPyodide) {
    await loadScript(`${PYODIDE_BASE}pyodide.js`);
  }
  if (!window.loadPyodide) {
    throw new Error("Pyodide 로더를 찾을 수 없습니다.");
  }
  const pyodide = await window.loadPyodide({ indexURL: PYODIDE_BASE });
  await pyodide.loadPackage("micropip");
  const micropip = pyodide.pyimport("micropip");
  await micropip.install("sqlglot");
  writePythonSources(pyodide);
  pyodide.runPython(
    [`import sys`, `sys.path.insert(0, "${PY_ROOT}")`, `from main import analyze, diff`].join("\n"),
  );
  return pyodide;
}

/** Pyodide 초기화 (최초 1회, 이후 재사용). 실패 시 다음 호출에서 재시도. */
export function ensureBridge(): Promise<PyodideInterface> {
  if (!instance) {
    instance = init().catch((e) => {
      instance = null;
      throw e;
    });
  }
  return instance;
}

/** SQL(+선택 스키마 DDL) -> AnalysisResult. 분석은 전부 Python에서 끝나고 JSON만 넘어온다. */
export async function analyzeSql(sql: string, schemaDdl = ""): Promise<AnalysisResult> {
  const pyodide = await ensureBridge();
  const analyze = pyodide.globals.get("analyze");
  try {
    const json = analyze(sql, schemaDdl);
    return JSON.parse(json) as AnalysisResult;
  } finally {
    analyze.destroy?.();
  }
}

/** SQL Diff (v0.8): before/after SQL -> DiffResult. 비교는 전부 Python(AST 수준)에서 끝난다. */
export async function diffSql(
  sqlBefore: string,
  sqlAfter: string,
  schemaDdl = "",
): Promise<DiffResult> {
  const pyodide = await ensureBridge();
  const diff = pyodide.globals.get("diff");
  try {
    const json = diff(sqlBefore, sqlAfter, schemaDdl);
    return JSON.parse(json) as DiffResult;
  } finally {
    diff.destroy?.();
  }
}
