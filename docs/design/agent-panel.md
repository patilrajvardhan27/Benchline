# Design: Ask Benchline (agent panel)

Status: built. Written before the code; the last section lists where the build differs and why.

## Problem

Answering "is 0.06 a fair price for sertraline 50 mg?" today takes three pages: find the item, open its
benchmark, check the anomaly list. The panel answers in one question, shows every lookup it made, and
links each claim to the item page it came from.

## Scope

- One question in, one answer out, with the steps visible as they happen.
- Read-only. The agent can look things up; it cannot change a price, review an anomaly or see member data.
- Three tools, no more: `get_benchmark`, `list_anomalies`, `find_equivalents`.
- Not in scope: memory across page loads, follow-up questions that reuse earlier tool results, voice.

## Flow

```
browser                         ml-service (FastAPI)                     model via LiteLLM
  | POST /api/v1/agent/runs       |                                          |
  |  {question}  Bearer token  -->| check token (scope agent:run), rate limit |
  |                               |-- messages + 3 tool specs -------------->|
  |<-- event: thinking -----------|<- "I'll check the benchmark first" + call |
  |<-- event: tool_call ----------|                                          |
  |                               |-- run tool (read-only SQL) --> Postgres   |
  |<-- event: tool_result --------|-- tool result -------------------------->|
  |        ... at most 6 steps ...                                           |
  |<-- event: answer -------------|<- final text                             |
  |<-- event: done ---------------|                                          |
```

## Event contract (Server-Sent Events)

Each event is `id: <n>`, `event: <type>`, `data: <json>`. A `: keep-alive` comment every 15 s keeps proxies
from closing a quiet stream.

| Event | Data | Panel shows |
|---|---|---|
| `run` | `run_id` | nothing; kept for logs |
| `thinking` | `text` | the sentence, in a muted style |
| `tool_call` | `call_id`, `name`, `arguments` | a collapsed row "Looking up …" with a skeleton under it |
| `tool_result` | `call_id`, `name`, `summary`, `ok`, `citations[]` | the row's summary; details hold arguments and result |
| `answer` | `text`, `citations[]` | the answer, then its sources as links to `/items/<id>` |
| `error` | `message`, `retryable` | an error box, with Retry when `retryable` |
| `done` | `steps`, `tokens`, `cost_usd` | the step count |

A stream that ends without `done` is a dropped stream, never a finished one.

## Panel

```
+-------------------------------------------------------------+
| Ask Benchline                                               |
| [ Is 0.06 a fair price for sertraline 50 mg?      ] [Ask]   |
| Try: (fair price for ...) (any odd moves in ...) (...)      |
|-------------------------------------------------------------|
| Q  Is 0.06 a fair price for sertraline 50 mg?               |
|    Checking the benchmark first.                 (thinking) |
|    > Looked up benchmark: SERTRALINE HCL 50 MG ...  [v]     |
|    > Found 12 equivalent products                   [v]     |
|    [ skeleton while the next step is pending ]              |
|    Answer ...                                               |
|    Sources: SERTRALINE ... (ndc-...)  ...                   |
|                                     [Cancel] / [Retry]      |
+-------------------------------------------------------------+
  hidden aria-live region: "Looking up benchmark", "Answer ready"
```

## State (Zustand)

```
conversation: Turn[]      // question, steps[], answer, citations, status, error
activeTurnId: string | null
status per turn: streaming | done | cancelled | error | dropped
```

Actions: `ask`, `cancel`, `retry`, `applyEvent`. Selectors: active turn, is running, pending step (drives the
skeleton), citations for a turn, tool-call count. The AbortController lives outside the store: it is not
state, and it is not serialisable.

## Failure handling

| Case | Behaviour |
|---|---|
| Cancel | aborts the fetch; the server sees the disconnect and stops calling the model |
| Dropped stream | status `dropped`, message "The connection dropped", Retry re-asks the same question |
| `error` event | shows the message; Retry only when the server says it may help |
| No model configured | 503 before streaming; the panel says the assistant is not set up |
| Too many runs | 429; the panel says to wait |

## Security and cost

- Token with scope `agent:run`, checked like the pricing API checks its own scopes.
- Tools run in read-only transactions with a 3 s statement timeout; arguments are validated before use.
- Tool output is data, never instructions; the system prompt says so, and nothing the model says can
  reach a write path because there is none.
- Per-user rate limit, at most 6 steps and 700 tokens per model call, and a daily spend cap.

## Accessibility

- The question box has a visible label; suggestions are buttons.
- One polite live region announces step changes and the final answer; the trace itself is not live, so a
  screen reader is not flooded with JSON.
- Skeletons are `aria-hidden`; the turn has `aria-busy` while it streams.
- Tool details use `<details>`/`<summary>`, so they work with keyboard and screen readers as built.
- axe at zero WCAG 2.2 AA violations, idle and after an answer, desktop and phone.

## Testing

- Server: the loop with a scripted model and fake tools; the endpoint (auth, scope, limit, SSE framing);
  the real LiteLLM Router run offline with mock replies.
- Recorded stream: the public demo and Playwright replay a stream recorded from the server's own encoder,
  and a test fails if the server's format drifts from the recording.
- Browser: Playwright against the recording, including cancel, a truncated (dropped) stream and retry.

## Where the build differs from this design

| Design | Build | Why |
|---|---|---|
| `thinking` is the model's own words | Also a fixed line ("Looking up the data.") when the model calls a tool without saying anything | Some models return tool calls with empty text; an empty step looked broken |
| Citations come from the answer text | Items the answer names by NDC; failing that, by description; failing that, every item the tools returned | Models often describe a drug without repeating its NDC, and one description covers many NDCs |
| The public demo has no assistant | It replays a recorded run, labelled as recorded | The demo should show the feature; replay keeps it free and honest |
| Recording from a real model | The committed recording uses a scripted model over the real demo data | Recording costs money and needs a key; `record_agent_run.py --live` re-records from a real model |
