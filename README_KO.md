# Kong Agent + MCP 데모

한국어 가이드입니다. Jaeger/Opik 속성 전체 목록·긴 cURL 예시·검증 run id 등 부록은 [README.md](README.md)를 함께 참고하세요.

이 저장소는 Kong이 에이전트 간(A2A) 트래픽과 MCP 도구 트래픽을 모두 어떻게 거버넌스하는지 보여 주는 Konnect 하이브리드 데모입니다.

## 목차

- [사전 요구 사항](#사전-요구-사항)
- [데모 시작 방법](#데모-시작-방법)
- [프로젝트 개요](#프로젝트-개요)
- [현재 UI](#현재-ui)
  - [상단 컨트롤](#상단-컨트롤)
  - [주요 UI 동작](#주요-ui-동작)
  - [다이어그램 뷰](#다이어그램-뷰)
- [데모에서 보여 주는 것](#데모에서-보여-주는-것)
- [런타임 구성](#런타임-구성)
- [관측성](#관측성)
  - [Konnect 관측성](#konnect-관측성)
  - [Loki 및 Grafana](#loki-및-grafana)
  - [Jaeger](#jaeger)
  - [Opik](#opik)

## 사전 요구 사항

데모를 실행하기 전에 다음이 준비되어 있어야 합니다.

- Docker Desktop 또는 `docker compose`가 동작하는 로컬 Docker Engine
- `python3`
- `curl`
- `jq`
- `deck`
- 대상 컨트롤 플레인에 접근 가능한 유효한 Konnect Personal Access Token
- [.env.example](.env.example)을 기반으로 채운 `.env` 파일
- 조직에서 MCP Registry 활성화

집중 거버넌스 시나리오에 필요한 Cloudsmith 호스팅 이미지:

- `docker.cloudsmith.io/kong/ai-pii/service:v0.1.4-en`
- `docker.cloudsmith.io/kong/ai-compress/service:v0.0.2`

로컬에 해당 이미지가 없다면:

```bash
docker login docker.cloudsmith.io
docker pull docker.cloudsmith.io/kong/ai-pii/service:v0.1.4-en
docker pull docker.cloudsmith.io/kong/ai-compress/service:v0.0.2
```

참고:

- Cloudsmith 이미지는 `PII Sanitization`, `Prompt Compression` 시나리오에 사용됩니다
- Registry 인증 정보는 Konnect PAT와 별도입니다
- AI PII 이미지, AI compression 이미지:
  - 사용자명: `1Password 공유 vault`
  - 비밀번호: `1Password 공유 vault`
- Prompt Compression은 메모리가 필요합니다. Docker에 16GB를 할당해 두었습니다

메인 시작 흐름에 필요한 최소 환경 변수:

- `KONNECT_TOKEN`
- `KONNECT_CONTROL_PLANE_NAME`
- `KONG_CLUSTER_CONTROL_PLANE`
- `KONG_CLUSTER_SERVER_NAME`
- `OPENAI_API_KEY`
- `DECK_OPENAI_API_KEY`
- `DECK_GEMINI_API_KEY`
- `DECK_REDIS_HOST`

선택: Semantic 시나리오 임베딩을 LM Studio로 전환:

- `.env`에 `DECK_LM_STUDIO_URL`이 있으면, `Semantic Load Balancing` / `Semantic Guard` / `Semantic Cache`의 임베딩 요청을 LM Studio로 보냅니다. 없으면 기존처럼 OpenAI 임베딩을 사용합니다.
- 전환 시 Redis에 저장된 기존 시맨틱 데이터(임베딩)가 호환되지 않을 수 있으므로, 필요하면 `Semantic Cache`의 `Clear Semantic Cache`를 실행하거나 Redis를 초기화하세요.
- LM Studio에서 토큰을 요구하면 `.env`의 `DECK_LM_STUDIO_API_KEY`를 설정하세요.

선택/전체 거버넌스 시나리오에 추가로 필요한 환경 변수:

- `DECK_LAKERA_API_KEY`
- `DECK_LAKERA_PROJECT`

시작 흐름이 기대하는 것:

- 시작 스크립트가 Konnect 컨트롤 플레인을 생성하거나 재사용할 수 있음
  - 기본 이름: `AA Demo`
  - `KONNECT_CONTROL_PLANE_NAME`으로 재정의 가능
- Konnect 커스텀 플러그인 스키마 생성 또는 업데이트 가능
- `deck gateway sync`로 현재 Kong 설정을 대상 컨트롤 플레인에 기록 가능
- 로컬 스택이 다음 포트로 기동 가능:
  - UI `8000`
  - Grafana `3001`
  - Opik `5173`
  - Jaeger `16686`

## 데모 시작 방법

1. [.env.example](.env.example)을 복사해 `.env`를 채웁니다.
2. 전체 데모 스택을 시작합니다:

```bash
./scripts/start_rag_demo.sh
```

시작 흐름은 다음을 수행합니다:

- Konnect 컨트롤 플레인 생성 또는 재사용
  - 기본 이름: `AA Demo`
  - `KONNECT_CONTROL_PLANE_NAME`으로 재정의 가능
- 커스텀 플러그인 스키마 동기화
- `deck gateway sync` 실행
- Konnect 대시보드 업로드
- Konnect MCP Registry 항목 등록
- 데모 RAG 지식 베이스 수집(ingest)

3. 주요 로컬 엔드포인트를 엽니다:

- UI: [http://localhost:8000](http://localhost:8000)
- Grafana: [http://localhost:3001](http://localhost:3001)
- Opik: [http://localhost:5173](http://localhost:5173)
- Jaeger: [http://localhost:16686](http://localhost:16686)

4. 전체를 중지하려면:

```bash
./scripts/stop_rag_demo.sh
```

데모에서 사용하는 주요 링크:

- Kong MCP remote: [http://localhost:8000/mock-mcp](http://localhost:8000/mock-mcp)
- Kong 경유 Support agent card: [http://localhost:8000/support-agent/.well-known/agent-card.json](http://localhost:8000/support-agent/.well-known/agent-card.json)
- Kong 경유 Success agent card: [http://localhost:8000/success-agent/.well-known/agent-card.json](http://localhost:8000/success-agent/.well-known/agent-card.json)

## 프로젝트 개요

이 프로젝트는 Konnect 하이브리드 모드에서 Kong 뒤에 동작하는 작고 시각적으로 명확한 에이전트 시스템을 시연합니다.

예시 화면:

정상 거버넌스 흐름:

![Normal governed flow](img/image1.png)

시나리오 선택기 및 기본 에스컬레이션 입력:

![Scene selector and baseline input](img/image2.png)

PII sanitization 집중 거버넌스 시나리오 예:

![PII sanitization scenario](img/image3.png)

거버넌스 경로에 AI PII Service가 포함된 집중 토폴로지 뷰:

![PII topology view](img/image4.png)

데모 구성:

- LangGraph 오케스트레이터 1개
- LangGraph 서브 에이전트 2개
- 요청 분류 및 경영진 요약을 위한 오케스트레이터 LLM 단계
- 오케스트레이터·서브 에이전트의 LLM 호출은 Kong AI Proxy Advanced 경유
- 오케스트레이터·서브 에이전트용 별도 Kong AI 라우트
- 오케스트레이터와 서브 에이전트 간 에이전트 검색, A2A 실행, A2A 관측을 위한 Kong `ai-a2a-proxy` 플러그인
- 백엔드 REST API 1개
- 해당 API를 MCP 도구로 노출하는 Kong `ai-mcp-proxy` 플러그인
- 내부 검색용 데모 MCP 서버 게시를 위한 Konnect MCP Registry
- 에이전트별 도구 가시성 제어를 위한 Consumer 및 Consumer Group
- 실시간 흐름을 보여 주는 경량 UI

비즈니스 시나리오는 단순한 고객 에스컬레이션입니다:

- 고객이 갱신을 하지 않을 위험이 있음
- 청구 문제를 보고함
- 제품 이슈도 보고함
- 시스템이 빠르게 경영진 에스컬레이션 브리프를 만들어야 함

데모의 핵심은 Kong이 모든 중요 홉의 중간에 있다는 점입니다:

- UI → 오케스트레이터
- 오케스트레이터 → MCP 도구
- 오케스트레이터 → 서브 에이전트
- 서브 에이전트 → MCP 도구

Kong의 역할을 설명하기 쉽습니다:

- 라우트 제어
- 인증
- Kong을 통한 A2A 에이전트 검색 및 실행
- MCP를 통한 도구 노출
- Konnect MCP Registry를 통한 MCP 서버 등록
- AI Proxy Advanced를 통한 LLM 라우팅
- 에이전트별 도구 제한
- 에이전트 트래픽 관측

MCP 검색 구조:

- 런타임 MCP 트래픽은 여전히 Kong의 `/mock-mcp`를 경유
- 동일 서버가 Konnect에도 등록됨:
  - registry: `AA Demo MCP Registry`
  - server: `com.aa-demo/mock-mcp`
  - remote: `http://localhost:8000/mock-mcp`
- 검색/거버넌스 메타데이터는 Konnect에 두고, Kong은 인증·라우팅·관측의 런타임 제어점으로 유지

## 핵심 거버넌스 컴포넌트

- `AI A2A Proxy`
  - Kong이 오케스트레이터와 support/success 에이전트 간 서브 에이전트 검색 및 A2A `message/stream` 실행을 처리합니다.
- `AI MCP Proxy`
  - Kong이 백엔드 REST API를 MCP 도구로 노출하고, 에이전트별 도구 접근을 강제합니다.
- `AI Proxy Advanced`
  - Kong이 오케스트레이터·서브 에이전트 LLM 트래픽을 설정된 모델 공급자로 라우팅하며, 데모에서 페일오버 동작도 지원합니다.
- `AI Semantic Prompt Guard`
  - Kong이 임베딩과 Redis로 거부 테마와 의미적으로 유사한 프롬프트를 차단합니다.
- `AI Semantic Cache`
  - Kong이 Redis에서 의미적으로 유사한 프롬프트를 찾아, 모델을 다시 호출하지 않고 캐시 응답을 반환할 수 있습니다.
- `AI Sanitizer / AI PII Service`
  - PII 시나리오에서 Kong이 요청·응답 본문을 AI PII Service로 보내 민감 데이터를 익명화하거나 차단합니다.
- `AI Prompt Compressor`
  - Kong이 장문 프롬프트를 AI Prompt Compressor 서비스로 보내 모델 호출 전에 토큰 절감·프롬프트 크기 거버넌스를 시연합니다.
- `AI Lakera Guard`
  - Kong이 모델에 도달하기 전 Lakera로 프롬프트 정책 검사를 수행합니다.
- `Workflow Graph`
  - Kong이 합성 워크플로 트리를 만들어 Opik로보내, 원시 요청 트레이스뿐 아니라 워크플로 지향 AI 트레이스를 보여 줍니다.

## 현재 UI

UI는 Kong을 컨트롤 플레인으로 두는 데 맞춰져 있습니다.

### 상단 컨트롤

- `Scenes`
  - 거버넌스 시나리오 선택 및 데모 입력 편집 모달
- `View Diagrams`
  - 시퀀스 다이어그램, 오케스트레이터·서브 에이전트 LangGraph 상태 다이어그램
- `Reset Scene`
  - 현재 실행 상태 초기화, 토폴로지를 유휴 데모 뷰로 복원
- `Reset Observability`
  - Loki/Grafana 데모 상태 및 UI 최근 실행 목록 초기화
- `View Run Output`
  - 선택한 실행의 구조화된 비즈니스 출력
- `?`
  - 데모 시나리오 요약 및 각 에이전트/컴포넌트 역할 도움말

### 주요 UI 동작

- 토폴로지에서 Kong이 시각적으로 항상 중심
- 모든 토폴로지 노드에 `+` 버튼으로 상세 정보
- 리셋/실행 종료 후에도 Kong과 MCP가 강조되어 게이트웨이·도구 플레인 관계가 유지됨
- 트레이스 사이드바에 인메모리 `TraceBroker` 기반 `Recent Runs`
- `Reset Observability`는 Loki/Grafana와 UI 최근 실행 목록을 함께 초기화

### 다이어그램 뷰

- `View Diagrams`에 정상 시나리오 UML 스타일 시퀀스 흐름
- 동일 모달에 LangGraph 상태 다이어그램:
  - orchestrator
  - support-agent
  - success-agent
- 시퀀스 다이어그램 `Open Full Width`로 별도 팝업에서 전체 폭 확인

## 데모에서 보여 주는 것

- 오케스트레이터 에이전트 1개
- 서브 에이전트 2개
- Kong `ai-mcp-proxy`로 MCP 도구로 노출된 백엔드 REST API 1개
- Consumer·Consumer Group으로 강제되는 에이전트별 도구 가시성
- LangGraph 기반 결정적 에이전트 워크플로
- 계획·합성을 위한 오케스트레이터 LLM 호출
- 요청 흐름을 시각화하는 경량 UI
- 각 박스 역할을 설명하는 노드별 상세 팝업
- 정상 E2E 흐름 시퀀스 다이어그램
- 세 에이전트 모두의 LangGraph 워크플로 다이어그램

## 런타임 구성

- `ui`: 데모 시작 및 트레이스 표시
- `orchestrator`: Play 요청 수신 및 실행 조율
- `support-agent`: 제품·런북 조사
- `success-agent`: 고객 후속 조치·액션 아이템
- `mock-api`: 7개 도구용 백엔드 REST API
- `ai-llm-service`: Kong AI Proxy Advanced 경유 LLM 트래픽
- `redis-stack`: 시맨틱 가드 시나리오용 벡터 DB
- `kong-dp`: Konnect 하이브리드 모드 Kong Gateway `3.14.0.6`

## 관측성

데모는 세 가지 주요 관측 표면을 제공합니다:

- 관리형 분석 대시보드용 Konnect 관측성
- 게이트웨이 로그·실행 범위 테이블·거버넌스 대시보드용 Loki 및 Grafana
- 원시 OpenTelemetry 트레이스 트리용 Jaeger
- Kong `workflow-graph` 플러그인이보내는 합성 워크플로 AI 트레이스용 Opik

### Konnect 관측성

- Konnect는 컨트롤 플레인 관리형 관측 대시보드에 사용
- 저장소 시작 흐름이 데모 대시보드 정의를 Konnect에 업로드
- 로컬 Grafana와 별도의 관리형 분석 표면

### Loki 및 Grafana

- Grafana UI: `http://localhost:3001`
- Loki API: `http://localhost:3100`
- Kong이 전역 `http-log` 경로로 구조화된 게이트웨이 로그를 Loki에 전송
- Grafana 주요 용도: 거버넌스 대시보드, 실행 트레이스 테이블, 정책 이벤트, 요청/응답 탐색

### Jaeger

Jaeger는 데모용 로컬 원시 OTEL 트레이스 뷰어입니다. `kong-dp` 트레이싱, [kong/deck/kong.yaml](kong/deck/kong.yaml)의 `opentelemetry` 플러그인, [docker-compose.yml](docker-compose.yml)의 collector·Jaeger, OTLP `http://otel-collector:4318/v1/traces` → Jaeger `http://jaeger:4318` 파이프라인이 포함됩니다. UI: `http://localhost:16686`.

시그널 분리: `LLM`(`ai-proxy-advanced`), `A2A`(`ai-a2a-proxy`), `MCP`(게이트웨이 스팬 + `ai-mcp-proxy` 로그/메트릭). 앱이 W3C `traceparent`/`tracestate`/`baggage`를 전파해 E2E 실행을 단일 트레이스로 연결합니다.

### Opik

- Opik UI: `http://localhost:5173`
- `workflow-graph`가 `demo.run_id` 키의 합성 워크플로 트리를 직접 기록 (Jaeger와 별도 파이프라인)
- `ngx.timer.at(...)`로 백그라운드 HTTP 기록

필드 소유권·Jaeger 스팬 속성·collector 보강의 상세 속성 목록은 [README.md](README.md)의 Observability 절을 참고하세요. API·플러그인 계약 필드명은 영문 그대로입니다.

로컬 검증:

```bash
docker compose up -d --build
```

Jaeger: 서비스 `aa-demo-kong`, 태그 `demo.run_id=<run_id>`. Opik: `docker compose --profile opik up -d`.

## 라우트

- `/orchestrator`, `/support-agent`, `/success-agent`, `/api`, `/mock-mcp`, `/ai`
- `/ai/orchestrator/chat/completions`, `/ai/subagent/chat/completions`

UI는 Kong `8000`에서 호스팅됩니다. A2A는 `/.well-known/agent-card.json` 검색, `message/stream` 실행, `a2a-sdk==0.3.26`, 프로토콜 `0.3.0`을 사용합니다.

시나리오별 AI 라우트 전체 목록은 [README.md](README.md#routes)를 참고하세요. 핵심: `/mock-mcp`는 `ai-mcp-proxy`로 MCP 도구 노출, 오케스트레이터·서브 에이전트 LLM은 `/ai/orchestrator/...`, `/ai/subagent/...`로 분리됩니다.

## A2A 프로토콜 · 트레이스

- `context_id`, `task_id`, `message_id`, `task_state` — 원문과 동일 의미
- 오케스트레이터는 서브 에이전트에 `message/stream` 사용
- Trace Explorer: `/orchestrator/trace/context/{context_id}/events` (Loki → A2A/MCP/LLM 정규화)

## Kong 경유 cURL 테스트

명령·JSON은 [README.md](README.md#curl-tests-through-kong)와 동일합니다. `apikey: orchestrator-demo-key`, 헤더 `x-demo-run-id`, `x-demo-context-id`를 포함합니다.

1. Support/Success agent card: `GET .../.well-known/agent-card.json`
2. `message/send`, `message/stream`, `tasks/get` — `http://localhost:8000/support-agent/a2a`

## 거버넌스 시나리오

UI에 `Governance Scenario` 선택기가 있습니다. 고객 에스컬레이션 스토리는 동일하고, 선택에 따라 Kong이 거버넌스하는 AI 경로만 바뀝니다.

`Play` 요청의 `governance_scenario`가 라우트를 결정합니다. [services/orchestrator/app.py](services/orchestrator/app.py)의 `ai_route_for_scenario()` 매핑:

- `normal` → `/ai/orchestrator/chat/completions`
- `load_balancing` → failover / semantic load balance / model-based 데모 라우트
- `token_limit` → `/ai/orchestrator-token-demo/chat/completions`
- `prompt_enhancement` → prompt-enhance 데모 라우트
- `prompt_compression` → prompt-compress 데모 라우트
- `semantic_guard` → semantic-guard 데모 라우트
- `semantic_cache` → semantic-cache 데모 라우트
- `llm_as_judge` → judge 데모 라우트
- `lakera_guard` → lakera 데모 라우트
- `rag` → rag before/after 데모 라우트
- `pii_sanitizer` → pii placeholder/synthetic/block 데모 라우트

### 1. Normal (정상)

기본 실행. 오케스트레이터는 표준 `/ai/orchestrator/chat/completions`, 서브 에이전트는 `/ai/subagent/chat/completions`. MCP·ACL·A2A 트래픽은 모두 Kong 경유. 표준 해피 패스 시연용.

### 2. Load Balancing (로드 밸런싱)

하위 시나리오: `LLM Failover`, `Semantic Load Balancing`, `Model-Based Routing`.

**LLM Failover** — 주 모델 실패 시 동작 시연. `/ai/orchestrator-failover-demo/...`, `ai-proxy-advanced` 페일오버 실험. 현재는 디버깅/실험 경로이며, per-target `upstream_url`이 페일오버 격리를 방해할 수 있어 결정적 데모로 보기 어렵습니다.

**Semantic Load Balancing** — 프롬프트 의미 기반 모델 라우팅. `balancer.algorithm: semantic`, `text-embedding-3-small`, Redis에 저장된 타깃 설명과 비교. 프리셋: Support/Operational → OpenAI 4o mini, Creative/Marketing → Gemini 2.5 Flash.

**Model-Based Routing** — `datakit`이 selector 라우트(`/ai/orchestrator-model-selector/...`)로 `simple`/`complex`만 반환받아 본문 `model`을 재작성한 뒤 tier별 alias로 라우팅.

### 3. AI Token Limit (토큰 한도)

- `Model Token Rate Limit`: `/ai/orchestrator-token-demo/...`, `ai-rate-limiting-advanced`, 300초에 1회 등
- `Consumer Cost Rate Limit`: `/ai/orchestrator-consumer-cost-demo/...`, consumer별 비용 한도 (`consumer1` $5, `consumer2` $10 / 300초, `team-a` 그룹)

Kong `429`를 오케스트레이터가 구조화된 차단 결과로 변환합니다.

### 4. Prompt Decorator (프롬프트 데코레이터)

`Without Decorator` / `With Decorator` 비교. 동일 입력, decorated 라우트만 `ai-prompt-decorator`로 경영진 에스컬레이션 형식·정책 문구 주입. 전체 MCP/서브 에이전트 흐름 대신 집중 프로브.

### 5. Prompt Compression (프롬프트 압축)

`By Ratio (50%)` / `By Token Count (100)`. `ai-prompt-compressor` + Cloudsmith `ai-compress/service:v0.0.2`. Grafana에 토큰 절감 패널 포함.

### 6. Semantic Guard (시맨틱 가드)

`/ai/orchestrator-semantic-guard-demo/...`, `ai-semantic-prompt-guard` + Redis. 거부 주제와 의미 유사 시 LLM 호출 전 차단. UI `+` 패널에 threshold 설명.

### 7. Semantic Cache (시맨틱 캐시)

동일·유사 triage 프롬프트 두 번 호출: miss → hit. `Send First Request`, `Send Second Request`, `Clear Semantic Cache`. Redis 상태는 실행 간 유지되므로 deterministic 데모 전 캐시 클리어 권장.

### 8. RAG

`Run Baseline` / `Run With RAG`. before/after 라우트, `ai-rag-injector`, KB는 [rag/atlasflow-support-kb/](rag/atlasflow-support-kb/). 수집: [scripts/ingest_rag_kb.py](scripts/ingest_rag_kb.py), [scripts/ingest_rag_kb.lua](scripts/ingest_rag_kb.lua) (`kong runner` 사용).

### 9. PII Sanitization (PII 정화)

Placeholder / Synthetic / Block. `ai-sanitizer` + Cloudsmith `ai-pii/service:v0.1.4-en`. 요청·응답 양방향 정화 또는 차단.

### 10. LLM as Judge

후보 `gpt-4o-mini`, 심사 `gemini-2.5-flash`. `ai-llm-as-judge` + Grafana 평가 테이블. 후보 타깃은 OpenAI만 (Gemini 충돌 방지).

### 11. Lakera Policy Guard

Safe / Content Moderation / Prompt Defense / Data Leak Prevention. `ai-lakera-guard`로 제3자 안전 정책 시연.

## Play 버튼을 누르면

1. UI가 Kong 경유 오케스트레이터에 단일 요청 (거버넌스 시나리오 포함)
2. 오케스트레이터 LangGraph 시작, 라이브 트레이스
3. 시나리오별 Kong AI 라우트 선택
4. `/mock-mcp`로 허용된 도구만 목록·호출 (`get_customer_account`, `get_renewal_risk`, `get_open_tickets`)
5. 요청 분류 브리프 LLM 호출
6. support-agent A2A `message/stream` → 허용 MCP (`get_incident_status`, `search_runbook`) + 서브 에이전트 LLM
7. success-agent → (`draft_customer_reply`, `create_followup_task`) + LLM
8. 최종 경영진 브리프 LLM 호출 후 UI에 토폴로지·이벤트·결과 표시

LangGraph가 워크플로, Kong이 네트워크 경로·도구 가시성을 담당합니다.

## 데이터 흐름

### 1. UI 입력

`customer_id`, `account_name`, `issue_summary`, `product_issue`, `billing_issue`, `incident_id`

### 2. 오케스트레이터 MCP 보강

`get_customer_account`, `get_renewal_risk`, `get_open_tickets`

### 3. 요청 분류 브리프

오케스트레이터 AI 라우트로 상황·다음 조치·커뮤니케이션 자세 요약 → 양쪽 서브 에이전트에 전달

### 4. Support 서브 에이전트

입력: `customer_id`, `account_name`, `product_issue`, `incident_id`, `triage_brief`  
출력: `incident`, `runbook`, `technical_response`, `recommended_actions` 등

### 5. Success 서브 에이전트

입력: `account_name`, `csm`, `issue_summary`, `renewal_risk`, `technical_summary`, `triage_brief`  
출력: `customer_reply`, `followup_task`, `success_plan` 등

### 6. 최종 조립

오케스트레이터가 전체 컨텍스트로 `executive_brief` 생성 → UI 렌더링

## 데모 참고

### API 키

- `ui-demo-key` — UI → 오케스트레이터·`/orchestrator/trace`
- `consumer1-demo-key`, `consumer2-demo-key` — Consumer 비용 한도 프로브
- `orchestrator-demo-key` — MCP, A2A, 오케스트레이터 AI
- `support-demo-key`, `success-demo-key` — 각 서브 에이전트 MCP·AI

정의: [kong/deck/kong.yaml](kong/deck/kong.yaml)

### 시나리오 입력 기본값

- `customer_id = cust_acme`
- `account_name = Acme Health`
- `issue_summary = Customer reports a billing dispute and workflow-agent sync delays.`
- `product_issue = workflow agent sync delays`
- `billing_issue = billing overcharge on enterprise add-ons`
- `incident_id = INC-1007`

정의: [ui/index.html](ui/index.html), [services/orchestrator/app.py](services/orchestrator/app.py)

### 최종 출력 필드

`headline`, `available_tools`, `account_context`, `renewal_risk`, `open_tickets`, `triage_brief`, `support_track`, `success_track`, `executive_brief`, `recommended_summary` — [services/orchestrator/app.py](services/orchestrator/app.py) `finalize_response`

## 에이전트 역할

- **Orchestrator**: UI 수신, MCP 컨텍스트, 요청 분류·최종 브리프, 서브 에이전트 조율, 트레이스 스트리밍
- **Support**: 인시던트·런북 조사, 기술 요약
- **Success**: 고객 회신 초안, 후속 태스크, CS 요약

## 예상 LLM 호출 수 (정상 실행)

- orchestrator: 5 (플래너 3 + 요청 분류 1 + 경영진 요약 1)
- support-agent: 3
- success-agent: 3

`gpt-4o-mini` 5회, `gemini-2.5-flash` 6회. Grafana 집계가 맞지 않으면 Loki의 `run_id` 전파를 먼저 확인.

## 구현된 서비스

- [ui/index.html](ui/index.html) — 정적 데모 UI
- [services/orchestrator/app.py](services/orchestrator/app.py) — `POST /play`, `WS /trace`, 트레이스 API
- [services/common/llm.py](services/common/llm.py) — Kong `/ai` 공용 LLM 클라이언트
- [services/support_agent/app.py](services/support_agent/app.py), [services/success_agent/app.py](services/success_agent/app.py)
- [services/mock_api/app.py](services/mock_api/app.py) — 7개 도구 REST API
- [services/common/mcp_client.py](services/common/mcp_client.py) — MCP 클라이언트

## Kong 커스텀 플러그인

- [trace-enricher](kong/plugins/trace-enricher) — 트레이스/로그 페이로드 보강
- [workflow-graph](kong/plugins/workflow-graph) — Opik 합성 워크플로
- [prompt-capture](kong/plugins/prompt-capture) — 시맨틱 가드 차단 시에도 입력 프롬프트 로깅

## 도구 접근 모델

| 에이전트 | 도구 |
|--------|------|
| orchestrator-agent | `get_customer_account`, `get_renewal_risk`, `get_open_tickets` |
| support-agent | `get_incident_status`, `search_runbook` |
| success-agent | `draft_customer_reply`, `create_followup_task` |

Kong MCP 프록시의 Consumer·Consumer Group ACL로 강제.

## 백엔드 API

[services/mock_api/app.py](services/mock_api/app.py). 호스트 접근은 Kong `/api` 경유.

| 도구 | 엔드포인트 |
|------|-----------|
| get_customer_account | `GET /api/customers/{customer_id}` |
| get_renewal_risk | `GET /api/customers/{customer_id}/renewal-risk` |
| get_open_tickets | `GET /api/customers/{customer_id}/tickets` |
| get_incident_status | `GET /api/incidents/{incident_id}` |
| search_runbook | `GET /api/runbooks/search?q=...` |
| draft_customer_reply | `POST /api/drafts/customer-reply` |
| create_followup_task | `POST /api/tasks/followup` |

Kong 경유 curl 예시:

```bash
curl -s http://localhost:8000/api/health | jq
curl -s http://localhost:8000/api/customers/cust_acme | jq
curl -s http://localhost:8000/api/incidents/INC-1007 | jq
```

Kong 우회(컨테이너 네트워크 디버깅):

```bash
docker exec orchestrator curl -s http://mock-api:8000/customers/cust_acme
```

## 저장소 주요 파일

- `docker-compose.yml` — 로컬 토폴로지
- `.env.example` — 하이브리드 환경 변수 템플릿
- `kong/deck/kong.yaml` — 서비스·라우트·인증·MCP 설정
- `services/` — FastAPI 서비스
- `ui/` — 프론트엔드

## 빠른 시작

### 1. env 파일

```bash
cp .env.example .env
```

### 2. `.env` 편집

```bash
KONG_CLUSTER_CONTROL_PLANE=YOUR_KONNECT_CP_HOST:443
KONG_CLUSTER_SERVER_NAME=YOUR_KONNECT_CP_HOST
KONG_CLUSTER_TELEMETRY_ENDPOINT=YOUR_KONNECT_TELEMETRY_HOST:443
OPENAI_API_KEY=YOUR_OPENAI_API_KEY
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
DECK_OPENAI_API_KEY=YOUR_OPENAI_API_KEY
DECK_GEMINI_API_KEY=YOUR_GEMINI_API_KEY
DECK_OPENAI_MODEL=gpt-4o-mini
DECK_GEMINI_MODEL=gemini-2.5-flash
DECK_REDIS_HOST=redis-stack
KONNECT_TOKEN=YOUR_KONNECT_PAT
KONNECT_CONTROL_PLANE_NAME=AA Demo
UI_LANG=ko
```

대시보드 UI를 한국어로 보려면 `UI_LANG=ko`를 설정한 뒤 UI 컨테이너를 재기동하세요 (`en`, `ja`, `ko` 지원).

### 3. 하이브리드 인증서

```bash
mkdir -p kong/certs
# kong/certs/tls.crt, kong/certs/tls.key
```

`KONG_CLUSTER_CONTROL_PLANE`, `KONG_CLUSTER_SERVER_NAME`, 인증서는 조인할 컨트롤 플레인과 일치해야 합니다.

### 4. decK용 env 로드

```bash
set -a
source .env
set +a
```

### 5. Kong 설정 검증

```bash
deck file validate kong/deck/kong.yaml
```

### 6. Konnect 동기화

`./scripts/start_rag_demo.sh`는 `kong/plugins/*/schema.lua` 스키마를 자동 등록합니다. 수동 sync:

```bash
deck gateway sync \
  --konnect-token "$KONNECT_TOKEN" \
  --konnect-control-plane-name "$KONNECT_CONTROL_PLANE_NAME" \
  kong/deck/kong.yaml
```

### 7. 스택 시작

```bash
docker compose up --build -d
```

또는 전체 데모:

```bash
./scripts/start_rag_demo.sh
```

### 8. UI

```text
http://localhost:8000/
```

Grafana: `http://localhost:3001/` (admin/admin), Loki: `http://localhost:3100/`

디버깅용 UI 컨테이너 직접 접근: `http://localhost:3000/` (실제 데모 진입점은 Kong `8000`)

## 유용한 명령

```bash
deck file validate kong/deck/kong.yaml
deck gateway sync --konnect-token "$KONNECT_TOKEN" --konnect-control-plane-name "$KONNECT_CONTROL_PLANE_NAME" kong/deck/kong.yaml
docker compose up --build -d
docker compose ps
docker compose logs -f
docker compose down
./scripts/stop_rag_demo.sh
```

## 관측성 상세 (Loki · Grafana · Konnect)

### Loki 라벨

`gateway`, `component` (llm/mcp/agent/backend/ui/gateway), `service`, `route`, `consumer`, `method`, `status`, `status_class`, `run_id` (`x-demo-run-id`)

### component 분류

- `mock-mcp-route` → mcp
- `ai-*` 서비스 → llm
- orchestrator/support/success → agent
- `mock-api-service` → backend
- `ui-service` → ui

### run_id 상관

UI가 `run_id`·`x-demo-run-id` 생성 → 오케스트레이터·서브 에이전트·Kong 로그·Loki·Grafana가 동일 키로 조인. 전파 누락 시 per-run 패널이 과소 집계됩니다.

### Grafana

`Kong Governance Overview`: 컴포넌트별 요청/에러, LLM/MCP/에이전트, 시맨틱 가드/캐시, **임베딩 모델 호출·지연**, RAG, LLM as Judge, 로그 스트림. `Run ID` 변수로 단일 실행 스코프.

- `LLM Calls By Model` / `Total Cost By Model`은 **chat completion** 모델(`gpt-4o-mini` 등)만 집계합니다.
- `Embedding Calls By Model` / `Avg Embedding Latency By Model`은 **임베딩** 모델(`text-embedding-mxbai-embed-large-v1`, `text-embedding-3-small` 등)을 집계합니다. LM Studio 로컬 임베딩은 **비용 패널에 포함되지 않습니다**.

`Kong Consumer Cost Overview`: consumer·팀 비용 패널 — [observability/grafana/dashboards/kong-consumer-cost-overview.json](observability/grafana/dashboards/kong-consumer-cost-overview.json)

### Konnect 대시보드 import

- [observability/konnect/dashboards/aa-demo-api-analytics.json](observability/konnect/dashboards/aa-demo-api-analytics.json)
- [observability/konnect/dashboards/aa-demo-ai-dashboard.json](observability/konnect/dashboards/aa-demo-ai-dashboard.json)

업로더: [scripts/upload_konnect_dashboards.py](scripts/upload_konnect_dashboards.py)

```bash
python3 scripts/upload_konnect_dashboards.py \
  --control-plane-id "$KONNECT_CP_ID" \
  --pat "$KONNECT_TOKEN"
```

`Reset Observability`는 Loki 컨테이너 재생성 + Grafana 재시작 (데모 전용).

## 참고

- 데모는 의도적으로 단순·결정적입니다.
- 도구 정의의 소스 오브 트루스는 백엔드 API입니다.
- 에이전트·MCP 트래픽의 공개 진입점은 Kong뿐입니다.
- 라이브 Konnect 검증·sync에는 실제 PAT, CP 이름, 하이브리드 인증서가 필요합니다.

영문 원문 및 속성·필드 전체 목록: [README.md](README.md)
