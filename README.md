# 루미(Lumi) · 버추얼 아이돌 AI 에이전트 — Starter Code

> AI Backend Engineering (Service Deployment, LLMOps) 실습용 스타터 코드

팬들의 "덕질"을 도와주는 버추얼 아이돌 **루미(Lumi)** AI 에이전트 서비스입니다.
대화, 스케줄·프로필 정보 제공, 캘린더 등록·팬레터 저장 같은 액션을 수행하는 에이전트를
**FastAPI + LangGraph + Upstage Solar + Supabase(pgvector)** 로 단계별로 구현해 나갑니다.

이 저장소는 **출발점(starter)** 입니다. 여기서부터 실습을 따라가며 **LangGraph 에이전트**(state·nodes·edges·graph), **RAG 문서 검색**, **툴(Tool) 실행**, **SSE 스트리밍**, **CI 파이프라인**, **Docker 배포**까지 단계별로 직접 구현해 나갑니다.

---

## ✅ 사전 준비물 (Prerequisites)

- **Python 3.11 이상**
- **[uv](https://docs.astral.sh/uv/)** (파이썬 패키지·가상환경 매니저)
  ```bash
  # macOS / Linux
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- **Upstage API 키** — [https://console.upstage.ai/](https://console.upstage.ai/) 에서 발급
- **Supabase 프로젝트** — [https://supabase.com/](https://supabase.com/) 에서 생성 (URL + API Key) · *RAG 실습 시 필요*

---

## 🚀 빠른 시작 (Quick Start)

### 1. 의존성 설치

```bash
uv sync
```

> `uv` 가 `pyproject.toml` / `uv.lock` 을 읽어 `.venv/` 가상환경을 자동으로 만들고
> 필요한 패키지를 설치합니다. (`requires-python >=3.11`)

> 💡 **개발·실습 도구 설치**
>
> ```bash
> uv sync --extra dev      # 테스트·린트 (CI 실습시 활용: pytest·ruff) — CI도 이 명령을 사용
> uv sync --all-extras     # 위 + Jupyter 노트북까지 한 번에 (study/ 노트북 실행용)
> ```
>
> `study/` 참고 노트북을 열려면 Jupyter가 필요합니다 (`notebook` extra).
> 노트북만 추가하려면 `uv sync --extra notebook`, 노트북 열기: `uv run jupyter lab`

### 2. 환경변수 설정

`.env.example` 을 복사해 `.env` 를 만들고 본인의 키를 채웁니다.

```bash
# macOS / Linux
cp .env.example .env

# Windows (CMD / PowerShell)
copy .env.example .env
```

```dotenv
# .env
ENVIRONMENT=development
DEBUG=true

# Upstage Solar API 키 (필수)
UPSTAGE_API_KEY=발급받은_본인의_키
LLM_MODEL=solar-pro3

# Supabase 설정 (RAG 실습 시 필요)
SUPABASE_URL=https://<your-project-ref>.supabase.co
SUPABASE_KEY=발급받은_본인의_키
```

> ⚠️ `.env` 에는 **본인의 키만** 넣으세요. `.env` 는 절대 공유·커밋하지 않습니다(`.gitignore` 에 등록되어 있음).

### 3. 서버 실행

```bash
# 개발 서버 (코드 변경 시 자동 리로드)
uv run uvicorn app.main:app --reload
```

서버가 뜨면 아래 주소로 접속합니다.

| 항목                  | URL                                                     |
| --------------------- | ------------------------------------------------------- |
| 루트                  | [http://localhost:8000/](http://localhost:8000/)           |
| Swagger UI (API 문서) | [http://localhost:8000/docs](http://localhost:8000/docs)   |
| ReDoc                 | [http://localhost:8000/redoc](http://localhost:8000/redoc) |

정상 동작 확인:

```bash
curl http://localhost:8000/
# {"message":"Lumi Agent API에 오신 것을 환영합니다!", ...}
```

---

## ⚙️ 환경변수

| 변수                | 설명                                                                  | 기본값          |
| ------------------- | --------------------------------------------------------------------- | --------------- |
| `ENVIRONMENT`     | 실행 환경 (`development` / `staging` / `production` / `test`) | `development` |
| `DEBUG`           | 디버그 모드 (개발 시`true`)                                         | `true`        |
| `UPSTAGE_API_KEY` | Upstage Solar API 키                                                  | —              |
| `LLM_MODEL`       | 사용할 Solar 모델명                                                   | `solar-pro3`  |
| `SUPABASE_URL`    | Supabase 프로젝트 URL                                                 | —              |
| `SUPABASE_KEY`    | Supabase API 키                                                       | —              |

설정은 `app/core/config.py` 의 `Settings` 클래스에서 타입 안전하게 로드됩니다.

---

## 📁 프로젝트 구조

```
starter_code/
├── app/                       # 애플리케이션 코드
│   ├── main.py                # FastAPI 진입점 (앱 생성·미들웨어·라우터 등록)
│   ├── ui.py                  # Gradio 채팅 UI (`/ui` 에 마운트) — 제공됨
│   ├── core/
│   │   └── config.py          # 환경변수 설정 (pydantic-settings)
│   ├── schemas/
│   │   └── chat.py            # 채팅 요청/응답 스키마
│   └── static/                # UI 정적 파일 (파비콘·OG 이미지)
│       ├── favicon.svg
│       └── og-image.png
├── data/                      # 데이터 & 적재 스크립트
│   ├── supabase_schema.sql    # Supabase 테이블·pgvector·검색 함수 정의
│   ├── lumi_worldview_v2.5.md / .pdf   # 루미 세계관 문서 (active, RAG 원본)
│   ├── lumi_worldview_v1.0.md / .pdf   # 구버전 (deprecated, 메타필터용 distractor)
│   └── scripts/
│       ├── ingest_data.py     # 스케줄 샘플 데이터 적재
│       └── ingest_rag.py      # 세계관 문서 → 벡터 DB 적재 (RAG)
├── scripts/
│   └── ai_reviewer.py         # CI용 AI 코드 리뷰 스크립트 (CI 실습시 활용)
├── study/
│   └── langgraph-개념정리.ipynb   # LangGraph 개념 참고 노트북 (읽기용·실습 X)
├── tests/                     # pytest 테스트 (CI 실습시 활용)
│   ├── test_agent.py
│   └── test_api.py
├── .env.example               # 환경변수 템플릿
├── .pre-commit-config.yaml    # pre-commit 훅 (ruff 등) — CI 실습시 활용
├── pyproject.toml             # 의존성·도구 설정
└── uv.lock                    # 잠금 파일 (재현 가능한 설치)
```

> 위는 **제공되는 출발점**이고, 실습을 진행하며 `app/graph/`(state·nodes·edges·graph) ·
> `app/api/`(routes) · `app/tools/` · `app/repositories/`, 그리고 `Dockerfile` ·
> `docker-compose.yml` · `.github/workflows/`(CI·CD) 등을 **직접 추가·구현**합니다.

---

## 🗄️ 데이터 준비 (Supabase + RAG)

> RAG·스케줄 조회 실습 단계에서 진행합니다. 기본 서버 실행만 할 때는 건너뛰어도 됩니다.

### 1) 테이블·확장·함수 생성

Supabase 대시보드 → **SQL Editor** 에서 [`data/supabase_schema.sql`](data/supabase_schema.sql) 의 내용을 실행합니다.
`schedules`, `fan_letters`, `documents` 테이블과 `pgvector` 확장, `match_documents()` 검색 함수가 생성됩니다.

### 2) 스케줄 샘플 데이터 적재

```bash
uv run python data/scripts/ingest_data.py
```

### 3) 세계관 문서 적재 (RAG)

```bash
# 기본: v2.5(active) + v1.0(deprecated) 모두 적재
uv run python data/scripts/ingest_rag.py

# v2.5(active)만 적재
uv run python data/scripts/ingest_rag.py --active-only
```

> 이 스크립트는 **멱등성**을 보장합니다 — 실행할 때마다 기존 `documents` 를 비우고 새로 적재합니다.
> `v1.0(deprecated)` 문서는 메타데이터 필터링을 시연하기 위한 **Distractor(방해 문서)** 입니다.

---

## 📌 참고

- **API 문서**: 서버 실행 후 `/docs`(Swagger) · `/redoc` 에서 인터랙티브하게 확인할 수 있습니다.
- **Upstage Solar**: [https://console.upstage.ai/](https://console.upstage.ai/)
- **Supabase pgvector**: [https://supabase.com/docs/guides/database/extensions/pgvector](https://supabase.com/docs/guides/database/extensions/pgvector)
- **LangGraph**: [https://langchain-ai.github.io/langgraph/](https://langchain-ai.github.io/langgraph/)
- **FastAPI**: [https://fastapi.tiangolo.com/](https://fastapi.tiangolo.com/)

---

## 강의 노트 
- 1강 핵심 목표 : StartCode의 핵심 구조 이해


### TODO - 1강 
- [v] 환경 세팅
    - [v] Code Class Live Share 익스텐션 설치 
        - [v] 화면 공유 테스트
    - [v] 가상 환경 생성
        - uv sync --all-extras
    - [v] .env 환경 변수 설정
    - [v] Supabase 설정
        - [v] 프로젝트에 data/supabase_schema.sql 실행
        - [v] 스케줄 데이터 저장
            - uv run python data/scripts/ingest_data.py 
        - [v] RAG 데이터 저장
            - uv run python data/scripts/ingest_rag.py
    - [v] 프로젝트 실행 
        - uv run uvicorn app.main:app --reload
    
- [v] StartCode 구조 이해 
    - [v] 1강 핵심 코드 이해 
        ├── app/                  
        ├── [v] main.py                # FastAPI 진입점 (앱 생성·미들웨어·라우터 등록)
        ├── core/
        │   └── [v] config.py          # 환경변수 설정 
        ├── schemas/
            └── [v] chat.py            # 채팅 요청/응답 스키마
    - [v] 기타 코드
        - [v] data/ — Supabase 스키마 · 세계관 문서 · 데이터 적재 스크립트 (스케줄 및 RAG용 루미 프로필 문서)
        - app/ui.py — Gradio 채팅 UI (다음 시간 활용)
        - scripts/ — CI용 AI 코드 리뷰 스크립트 (내일 CI 실습시 활용)
        - tests/ — pytest 스펙 테스트 (내일 CD 실습시 활용)


# 강의 노트 2강
- 2강의 핵심 목표 : LangGraph 이용해서 에이전트 MVP 구현


### 프로젝트 구조 (2강 완성 목표)

```
app/
├── core/
│   ├── config.py          ← 설정 관리 (pydantic-settings)
│   └── prompts.py         ← 프롬프트 분리
├── schemas/
│   └── chat.py            ← API 요청/응답 모델
├── graph/                 ← 노트북에서 만든 에이전트
│   ├── state.py           ← State 정의
│   ├── nodes.py           ← 노드 구현
│   ├── edges.py           ← 라우팅 로직
│   └── graph.py           ← 그래프 조립 + 싱글톤
├── repositories/          ← DB 접근 계층 
│   ├── rag.py             ← RAG 검색 (Supabase pgvector)
│   ├── schedule.py        ← 스케줄 조회
│   └── fan_letter.py      ← 팬레터 저장
├── tools/
│   └── executor.py        ← Tool 실행 (Repository 활용)
├── api/routes/
│   └── chat.py            ← REST API 엔드포인트
├── ui.py                  ← Gradio UI (/ui)
└── main.py                ← FastAPI 앱 (lifespan, CORS)
```


### TODO 정리
- [v] graph 구현 : Agent 핵심 로직 (노트북 코드 가져와서 필요한 부분 수정)
    - [v] graph/state.py 구현 : 노드가 공유하는 데이터
    - [v] graph/nodes.py 구현 : 실제로 작업을 수행하는 함수
        - [v] router 노드 : 메세지 의도분류
            - [v] core/prompts.py : router 프롬프트 구현
        - [v] rag 노드 : 문서 검색
            - [v] repositories 폴더 생성
                - [v] repositories/__init__.py : DB연결 구현
                - [v] repositories/rag.py : 루미 문서 정보 검색
        - [v] tool 노드 : 툴 실행
            - [v] tools/executor.py 구현 : tool 실행 로직
            - [v] repositories/schedule.py : 루미 스케쥴 데이터 조회
            - [v] repositories/fan_letter.py : 팬들의 메시지 저장
        - [v] response 노드 : 루미 응답
            - [v] core/prompts.py 구현
    - [v] edges.py 구현 : 조건부 엣지 구현
    - [v] graph.py 구현 : 그래프 빌드 (싱글톤)
- [v] API 서버 구현
    - [v] api/routes/chat.py : 엔드포인트에 따라 서비스 제공 (루미 챗봇)
- [v] 프론트엔드 구현
    - [v] ui.py : Gradio 사용 
- [v] main.py : lifespan에서 graph 싱글톤 로드 + 채팅 라우터 등록

### 이번 시간 강의의 핵심
- 구현 과정 익히기 위해 직접 보며 클론 코딩으로 연습
- 기능별로 관심사를 분리한 Layered Architecture 로 프로젝트 구조화
- MVP의 핵심인 Graph(에이전트 워크플로우) 로직 구현

---

## 강의 노트 3강  
- 핵심 목표 : 실시간 스트리밍 구현 (2강에서의 MVP 개선)

- 스트리밍 구현을 위한 SSE 핵심
    - 서버에서 클라이언트로 단방향 실시간 데이터를 전송하는 HTTP 기반 프로토콜
    - 형식 : "data: {JSON}\n\n" 형태로 이벤트 전송

(1) 이벤트 형태 정의 (스키마 설계)
- 왜? 백엔드와 프론트는 서로 "글자 스트림"만 주고받는다.
  그냥 텍스트만 오면 받는 쪽은 답인지·상태인지·에러인지·끝인지 모른다.
  그래서 보내기 전에 "이런 모양으로 줄게"를 미리 약속한다.
- 정하는 것 3가지
  - type: 조각의 정체 (thinking / token / response / error / done)
  - type별로 채워지는 필드 (실제 chat_stream이 보내는 값)
    - thinking : content = 진행 상태 메시지 (예: "🔀 루미 생각 중...")
    - token    : content = LLM 토큰 한 조각 (예: "안")
    - response : content = 최종 응답 전체 + tool_used = 사용한 도구 이름(있을 때만)
    - error    : error   = 에러 메시지
    - done     : 필드 없음 (끝 신호만)

- 실제로 흘러오는 예시 ("안녕?" 질문 → "안녕!" 답):
    data: {"type":"thinking","content":"🔀 루미 생각 중..."}
    data: {"type":"token","content":"안"}
    data: {"type":"token","content":"녕"}
    data: {"type":"token","content":"!"}
    data: {"type":"response","content":"안녕!"}
    data: {"type":"done"}

- 코드: schemas/chat.py 의 StreamEvent, to_sse()

(2) 백엔드 (이벤트 전송)
- LLM을 스트리밍 실행 → 조각이 나올 때마다 이벤트를 yield
- StreamingResponse(media_type="text/event-stream") 로 반환
- 코드: api/routes/chat.py 의 stream_with_status, chat_stream

(3) 프론트 (이벤트 수신)
- 스트림을 한 줄씩 읽어 "data: " 떼고 JSON 파싱
- type으로 분기 → token은 이어붙여 누적, done이면 종료
- 코드: ui.py 의 chat_with_lumi_sse

### TODO
- [] app/schemas/chat.py : StreamEvent, to_sse()
- [] app/api/routes/chat.py : SSE 구현. stream_with_status 함수
  - [] SSE 엔드포인트 추가
- [] app/ui.py : 스트리밍 데이터를 받아서 처리할 수 있도록 함수 

### 이번 시간 강의의 핵심
- SSE 구현을 어떻게 하는가?
- 목표는 바닥부터 직접 짜는 것이 아니라, 개념과 기술을 잘 이해하고 나의 프로젝트에 기술적 선택의 근거로 말할 수 있고 프로젝트에 활용함 (AI의 도움을 받아도됨)
- 작업 순서: (1) 이벤트 형태 정의 → (2) 백엔드(전송) → (3) 프론트(수신)

## 강의 노트 4강
- 핵심 목표 : CI 파이프라인 구축 - 코드를 main에 합치기 전에 기계가 자동으로 검사(린트,테스트,AI리뷰)하게 만들기

### 핵심 개념 
- **CI (Continuous Integration)** : 코드를 합치기(Merge) 전에 린트·테스트를 자동으로 실행해, 불량 코드가 main에 들어가는 걸 막는 자동화.
- **Pull Request (PR)** : "내 브랜치의 변경사항을 main에 합쳐주세요"라고 요청하는 것. 이 시점에 코드 리뷰 + CI 검사가 돌고, 통과해야 Merge 한다.
- **단위 테스트 (Unit Test)** : 함수·API 하나가 기대한 대로 동작하는지 검증하는 자동화 코드(pytest). 코드를 고쳐도 기존 기능이 안 깨졌는지 즉시 확인 가능.
- **린트 (Lint)** : 코드를 실행하지 않고 안 쓰는 import·문법 실수·스타일 문제를 잡아주는 정적 검사(Ruff).
- **포맷팅 (Format)** : 들여쓰기·공백 등 코드 "모양"을 팀 규칙대로 자동 정리(ruff format). 스타일 논쟁을 기계에게 맡긴다.
- **GitHub Actions** : GitHub이 제공하는 자동화 서버. `.github/workflows/*.yml` 에 적어두면 push/PR 때 알아서 실행해 준다.

### TODO
- [] GitHub 준비
    - [] GitHub에서 새 repo 생성
    - [] 3강 완성 코드를 main에 업로드
      ```bash
      git init
      git add .
      git commit -m "feat: 3강 완성 코드"
      git branch -M main
      git remote add origin https://github.com/woojinwoojin/lumi-agent2.git
      git push -u origin main
      ```
    - [] GitHub Secrets 등록 
        - repo → Settings → Secrets and variables → Actions → New repository secret
        - `UPSTAGE_API_KEY` / `SUPABASE_URL` / `SUPABASE_KEY` 3개 등록
- [] CI 워크플로우 추가 (새 브랜치 → push → PR)
    - [] 새 브랜치 생성 & 체크아웃
      ```bash
      git checkout -b feat/ci
      ```
    - [] `.github/workflows/ci.yml` 작성 
    - [] 변경된 파일 git add, commit, push
      ```bash
      git add .github/workflows/ci.yml
      git commit -m "update: ci.yml"
      git push --set-upstream origin feat/ci
      ```
    - [] GitHub에서 **Compare & pull request** 버튼 → PR 생성
    - [] PR의 Checks / Actions 탭에서 CI 결과 확인 — 실행 순서: lint → (test · ai-review 병렬) → comment
    - [] 초록불(✅) 확인 후 Merge
- [] 로컬 사전 검사 ① — 명령어 직접 실행 (CI가 돌리는 것과 똑같은 검사를 손으로 실행)
    - [] 일부러 문제 있는 `test.py` 를 만들기 (안 쓰는 import + 줄 끝 공백)
      ```python
      import os  # 안 쓰는 import (Ruff가 잡음)
      x   =     1     # 뒤에 불필요한 공백 
      ```
    - [] 린트 (안 쓰는 import·문법 실수 검사)
      ```bash
      uv run ruff check test.py          # 확인: 문제만 보여줌 (파일 안 고침) — CI가 쓰는 명령
      uv run ruff check test.py --fix    # 수정: 자동 수정 가능한 것 실제로 고침
      ```
    - [] 포맷 (들여쓰기·공백 등 코드 모양 정리)
      ```bash
      uv run ruff format test.py --check # 확인: 규칙에 맞는지 검사만 (다르면 실패) — CI가 쓰는 명령
      uv run ruff format test.py         # 수정: 실제로 모양을 정리
      ```
    - [] 단위 테스트 (확인만 — pytest는 자동 수정 없음. 실패하면 코드를 직접 고침)
      ```bash
      uv run pytest tests/ -v            # CI의 test Job과 동일한 명령. push 전에 로컬에서 먼저 통과 확인
      ```
        - [] health API 등록 
    - [] 확인 끝났으면 `test.py` 삭제
- [] 로컬 사전 검사 ② — pre-commit 훅 (commit할 때 위 검사를 자동으로) — 아래 섹션 참고
    - [] `uv run pre-commit install` — Git 훅 등록 (한 번만)
    - [] 다시 문제 있는 `test.py` 를 만들고 `git add` → `git commit` → 훅이 자동으로 잡아서 수정하는지 확인
    - [] 이미 push된 파일 전체 검사: `uv run pre-commit run --all-files`
    - [] Unsafe 항목(F841·E402)은 직접 수정
- [] Test가 통과되어야 Merge 가능하도록 설정 (Ruleset)
    - [] Settings → Rules → Rulesets → New ruleset → **New branch ruleset**
    - [] Ruleset Name: `protect main branch` / Enforcement status: **Active**
    - [] Target branches: Add target → **Include default branch** (= main)
    - [] Rules 체크: **Require a pull request before merging** + **Require status checks to pass** → 검색창에서 **Code Quality** 와 **Unit Tests** 선택
        - 목록에는 YAML의 job id(lint/test)가 아니라 **Job의 표시 이름**(`name:` 값)이 뜬다
        - 이 목록은 CI가 최소 한 번 실행된 뒤에만 나타남 (앞 단계에서 이미 돌렸으므로 보임)
- [] AI 코드 리뷰 (CodeRabbit 연동 - 과제 교안보고 직접 해보기)
    - [] https://app.coderabbit.ai/login 접속 → **GitHub Cloud** 로 회원가입 후 인증(Authorize)
    - [] 내 repo에 권한(Grant) 부여
    - [] 연동만 해두면 이후 **PR을 열 때마다 자동으로 리뷰 코멘트**가 달림
    - [] 리뷰 제안 프롬프트를 바탕으로 **코드 자동 수정 커밋**까지 만들어 주는 것 확인 (fix: apply CodeRabbit auto-fixes)