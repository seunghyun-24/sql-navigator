# UI

## Philosophy

Notion의 정돈됨 + Linear의 밀도 + VSCode의 에디터 경험 + DataGrip의 SQL 친화성.

도구는 조용해야 한다. 분석 결과가 주인공이다.

## 기술

- Tailwind + shadcn/ui + React Aria **만** 사용한다 (다른 UI 라이브러리 금지)
- Business Logic은 React Component 내부에 작성하지 않는다
  - Component는 AnalysisResult를 받아 그리기만 한다
  - 분석·변환·계산은 Analysis/Renderer Layer의 일 (architecture.md)

## Layout

```
┌──────────┬───────────────────┬──────────────┐
│ Sidebar  │      Center       │    Right     │
│          │                   │              │
│ Explorer │    SQL Editor     │   Analysis   │
│ (쿼리    │  (입력, 하이라이트, │  (Warnings,  │
│  목록,   │   에러 위치 표시)   │   Metrics,   │
│  스키마) │                   │   탭 전환)    │
└──────────┴───────────────────┴──────────────┘
                    하단 또는 탭:
        AST Explorer / Join Graph / Query Flow
```

- Right 패널 탭: Warnings | Structure | Graph | Flow | Diff (v0.8)
- Warning 클릭 → Center 에디터의 해당 위치 하이라이트 (location 기반, v0.7 완성)

## Colors (severity와 1:1 매핑)

| 색 | 의미 | 대응 |
|----|------|------|
| Blue | 정보 | INFO |
| Yellow | 주의 | WARNING |
| Red | 위험 | CRITICAL |
| Green | 추천 | Suggestion (Refactoring 제안) |

색상 의미는 rules.md의 severity와 항상 일치시킨다.

## Warning 표시 원칙

Explainability(principles.md)를 UI로 강제한다:

- 접힌 상태: severity 색 + 한 줄 message
- 펼친 상태: 이유 / 예시(before) / 수정(after) — 3단 구성
- 수정 예시는 코드 블록으로, 복사 버튼 제공

### Fix Apply (v0.9)

- `fixSql`이 있는 Warning에만 **Apply 버튼(Green)** 을 펼친 상태 하단에 표시
- Apply 클릭 → 에디터 내용을 fixSql로 교체 → 자동 재분석 → 해당 Warning
  해소가 목록에서 확인된다
- Component는 문자열 교체와 재분석 요청만 한다 — SQL 변환 로직 금지
  (fixSql 생성은 Analysis Layer, analyzer.md "Fix Apply")
- 교체 전 원본은 undo로 복구 가능해야 한다

## Diff 탭 (v0.8)

- 입력: 현재 에디터 SQL(after) + 비교 대상 SQL(before, 붙여넣기)
- 표시: AST 수준 변경 목록 + Warning 수/Complexity Score의 before-after 비교
- 개선된 항목은 Green, 악화된 항목은 Red로 표시 (색상 의미 유지)

## 그래프 (Join Graph / Query Flow)

- 노드: 테이블(Join Graph), 연산 단계(Query Flow)
- 위험 요소는 그래프 위에 직접 표시 (예: Cartesian Product 엣지를 빨간색으로)
- 노드 클릭 → 해당 SQL 위치로 이동
