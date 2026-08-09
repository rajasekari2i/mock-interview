**MockInterview**

**AI Interview Simulation Platform — Product Requirements Document**

*v1.0 draft \| Owner: Arun (CTO) \| Built on Anticlock (dogfood project)
\| Confidential — Ideas2IT internal*

|                        |                                                                                            |
|------------------------|--------------------------------------------------------------------------------------------|
| **Field**              | **Value**                                                                                  |
| Status                 | Draft for review                                                                           |
| v1 scope               | Both use cases: Client-JD mock (UC1) and Bench assessment (UC2)                            |
| Interviewer modality   | Animated avatar + real-time voice + shared code editor                                     |
| Deployment posture     | Internal now; architected to productize later (single-tenant v1, tenancy-ready data model) |
| Primary build goal \#2 | Stress-test Anticlock on a real multi-service, real-time product                           |

# 1. Problem statement

The Interview-Readiness Program depends on high-quality mock interviews,
and mock interviews are exactly where we are weakest. Three specific
failures:

- **Mentor scarcity.** We do not have enough senior engineers with
  client-panel experience to conduct weekly mocks for 50 people (scaling
  to 200), and the ones we have cost 15–20% of their delivery time.

<!-- -->

- **Inconsistency and opacity.** Each mentor asks different questions,
  holds a different bar, and leaves no record of what was asked or how
  it was judged. We built calibration machinery (workshops, paired
  scoring, drift monitoring) to compensate — a platform can make
  consistency structural instead of procedural.

- **No scale, no speed.** When a client JD arrives, we need a targeted
  mock within 24–48 hours for each shortlisted candidate. Human
  scheduling cannot deliver that reliably, and cannot run 20 mocks in
  parallel.

Meanwhile the assessment IP already exists and is calibrated: a 4-stack
Skill Depth Matrix (60 items/stack, band expectations), a 126-question
band-exclusive Question Bank with probe ladders, a full Answer Key with
model answers and known wrong-answer traps, a 6-dimension rubric, and
Tier 1/2/3 classification logic. MockInterview operationalizes this IP
through an AI interviewer instead of scarce humans.

# 2. Goals and non-goals

## Goals (v1)

- G1 — Conduct a complete, realistic technical mock interview (45–75
  min) with an animated AI interviewer over live audio/video, with zero
  human interviewer required.

- G2 — UC1: given a client JD + candidate profile, generate and run a
  JD-targeted interview plan within minutes, and produce a
  client-readiness report.

- G3 — UC2: run band-calibrated primary-skill assessments for bench
  engineers, producing rubric scorecards and a Tier 1/2/3 recommendation
  consistent with the existing program.

- G4 — Score every interview on the published rubric (depth,
  communication, articulation, project exposure) with evidence excerpts,
  an L1/L2/L3 depth-reached record per topic, and an integrity score
  from proctoring.

- G5 — Keep a human in the loop: AI drafts the scorecard; a mentor
  reviews the recording highlights and signs off in ≤15 minutes (vs 75+
  minutes to conduct).

- G6 — Every interview fully recorded, transcribed, and auditable: what
  was asked, what was answered, why it was scored that way.

## Non-goals (v1)

- Not a hiring/ATS product; no external candidates; no multi-tenant
  admin, billing, or white-labeling (data model must not preclude them).

- Not a replacement for the certification gate — gate mocks may use the
  platform, but the two-different-interviewers rule then means two
  humans reviewing/signing distinct AI-conducted sessions.

- No behavioral/HR interview simulation in v1 (D6 project narration is
  in scope; culture-fit interviews are not).

# 3. Users and personas

|                            |                                                                                     |                                                                     |
|----------------------------|-------------------------------------------------------------------------------------|---------------------------------------------------------------------|
| **Persona**                | **Role in product**                                                                 | **Success looks like**                                              |
| Candidate (bench engineer) | Takes interviews; views own scorecard and improvement plan                          | Feels like a real, fair client interview; knows exactly what to fix |
| Mentor / Reviewer          | Reviews AI-drafted scorecards, watches flagged moments, signs off; can observe live | 15-minute review instead of 75-minute session; trusts the draft     |
| Program owner (Arun/ops)   | Configures cohorts, monitors dashboard, exports tracker data                        | One view of all sessions, scores, integrity flags, evaluator load   |
| Staffing/Sales coordinator | UC1 trigger: uploads client JD, picks candidates, schedules pre-client mocks        | JD in → readiness reports out within 48 h                           |
| Question-bank curator      | Maintains questions, answer keys, JD-mapping tags                                   | Bank updates flow to interviews without engineering work            |

# 4. Use cases and end-to-end flows

## UC1 — Client-JD pre-interview mock

Trigger: a client proposal includes technical interviews. Flow:

- 1\. Coordinator uploads the client JD / tech-requirements document and
  selects shortlisted candidate(s).

- 2\. JD Skill Mapper (LLM) extracts required skills, seniority signals,
  and domain context; maps them to matrix item IDs and rubric
  dimensions; flags JD skills with no bank coverage (curator alert +
  on-the-fly generated questions marked as UNCALIBRATED).

- 3\. Interview Plan generated: 60–75 min composition weighted by the JD
  (e.g., Kafka-heavy JD → messaging items get double weight), drawing
  questions from the bank filtered by the candidate's stack and band,
  plus 2–3 questions anchored on the candidate's own resume/profile
  claims.

- 4\. Candidate receives an invite; takes the interview with the AI
  avatar (Section 6); proctoring active.

- 5\. Scoring engine drafts the scorecard; mentor reviews and signs off;
  coordinator receives the Client-Readiness Report: go /
  go-with-coaching / not-ready, with the specific gaps against THIS JD
  and a 24–48 h targeted refresh plan.

## UC2 — Bench primary-skill assessment

- 1\. Program owner schedules an assessment wave (individual or cohort)
  for a stack + band.

- 2\. Interview plan derives from the Skill Depth Matrix: mandatory
  probing of every item the candidate self-rated 3–4, plus band-expected
  coverage across all six dimensions.

- 3\. Same interview experience and scoring pipeline; output feeds the
  existing program: per-dimension rubric scores → Readiness Tracker
  baseline columns; assessed levels → Matrix Assessed column; Tier 1/2/3
  recommendation using the published thresholds (avg gap, criticals,
  gaps, overrated count).

- 4\. Weekly-mock mode: shorter 40-min sessions reusing the same engine
  for the intensive phase, with rotation logic so no candidate sees a
  question twice.

Shared principle: one engine, two entry points. UC1 and UC2 differ only
in how the interview plan is composed (JD-weighted vs
matrix/band-weighted) and which report template renders.

# 5. Functional requirements

## FR-1 User Authenticate and Authorization.

- The three roles — Candidate, Admin, Manager

- Google OAuth (Gmail) login for all users

- Candidate flow: on login, sees only allocated interviews (no other
  pages visible)

- Admin: manages the overall application, full access to reports

- Manager: uploads JDs and allocates interviews to candidates

## FR-2 JD ingestion and skill mapping (UC1)

- Accept PDF/DOCX/text JDs and free-form client emails; extract:
  required skills, nice-to-haves, seniority, domain, and any stated
  interview format.

- Map extracted skills to matrix item IDs (deterministic tag table + LLM
  fallback); produce a coverage report: % of JD skills backed by
  calibrated questions.

- Uncovered skills: generate questions on the fly via LLM using the
  Answer-Key template (pass-contains / depth / traps / anchors), marked
  UNCALIBRATED in scoring, and queued for curator review into the bank.

## FR-3 Candidate profile

- Profile = resume upload + structured claims (projects, tech, role) +
  Skill Depth Matrix self-ratings (imported from the existing Excel or
  entered in-app).

- Resume claims become probe targets: the plan generator creates
  project-anchored questions (“you wrote that you built X — what broke
  in production?”) mirroring the D6/why-ladder method.

## FR-4 Interview session engine (the core)

- Live session: WebRTC room with animated avatar interviewer (lip-synced
  TTS), candidate audio+video, and a shared code editor pane (syntax
  highlighting for Java/Python/C#/JS-TS; run-code optional in v1,
  stretch).

- Conversation engine (LLM: Claude): follows the interview plan but
  adapts — the probe ladder is a state machine per topic: main question
  → L2 probe → L3 probe; advance on substantive answers, drop after two
  failed probes and record depth reached; keyword-triggered drill-downs
  when the candidate name-drops a technology (any claimed term is fair
  game).

- Interviewer behaviors: natural interruptions on rambling (\>2.5 min
  monologue), one clarification per question max, hostile-followup mode
  for AT band (design defense), constraint-twist injection on D5
  questions, time-boxing per section with graceful transitions.

- Barge-in support: candidate can interrupt the avatar mid-sentence;
  VAD-based turn-taking with adaptive endpointing (target: no
  talking-over, \<1 s perceived response gap median).

- Session controls: pause (bio-break, max 1, flagged), reconnect-resume
  on network drop (≤2 min grace), mentor observe mode (silent join, live
  transcript, private notes).

- Every session persists: full A/V recording, diarized transcript,
  per-question timing, probe-depth trace, code editor snapshots,
  proctoring event stream.

## FR-5 Proctoring and integrity

- Baseline (always on): identity check vs profile photo at start +
  periodic liveness; browser focus/tab-switch events; copy-paste into
  editor disabled with attempt logging; second-voice and keyboard-sound
  anomaly detection from audio; response-latency and answer-fluency
  anomaly signals (reading-vs-thinking cadence).

- Gaze tracking: sustained off-camera gaze patterns flagged (not
  auto-fail) — evidence timestamped for the reviewer, following the
  friction-not-cure principle; the primary cheat resistance is the
  adaptive probe ladder itself, which scripted or copilot answers cannot
  survive.

- Integrity score 0–100 computed from weighted events; \<70 flags the
  session for mandatory human review; all flags link to the exact video
  timestamp.

- Candidate consent screen before every session: recording, monitoring,
  and AI-interviewer disclosure (also future-proofs EU AI Act Art. 50
  transparency for productization).

## FR-6 Scoring and rubric engine

- Scores 1–5 (half points) on: D1–D6 technical dimensions
  (band-calibrated pass criteria from the Answer Key) PLUS three
  delivery dimensions: Communication (clarity, structure), Articulation
  (thinking aloud, pacing, composure under interruption), Project
  Exposure (specificity, ownership, quantified impact) — nine axes
  total.

- Every score carries: 1–3 evidence quotes from the transcript with
  timestamps, the depth reached (L1/L2/L3) per topic, and matched
  trap-answers if any (from the Answer Key wrong-answer column).

- Scoring is grounded in the Answer Key: the LLM judge receives
  pass-contains, depth descriptions, traps, and score anchors per
  question — it never free-scores. A second-pass consistency check
  re-scores 20% of answers with a different prompt seed; disagreement
  \>1 point flags for human review.

- Human sign-off: mentor sees draft scorecard + flagged moments
  playlist; can adjust any score (adjustment logged with reason — this
  drift data continuously calibrates the judge); report releases only
  after sign-off.

## FR-7 Reports

- Candidate Scorecard: nine-axis radar, per-dimension evidence, depth
  map, specific improvement actions, comparison to band bar.

- Client-Readiness Report (UC1): readiness verdict, JD-skill-by-skill
  status, risk areas with coaching plan, integrity note. Export PDF.

- Tier Recommendation (UC2): computed with the published thresholds;
  per-dimension averages formatted for direct entry into the Readiness
  Tracker (API/CSV export matching Roster columns).

- Program dashboard: sessions run, average scores by cohort/stack/band,
  score distributions, integrity-flag rate, mentor review SLA,
  question-level analytics (which questions discriminate, which leak).

## FR-8 Question bank and curation

- Import the existing Question_Bank.xlsx and AnswerKey (one-time
  migration script); admin UI for CRUD with the same fields (band,
  stack, dim, items, probes, pass criteria, traps, anchors).

- Rotation and exposure control: per-candidate question history;
  per-question exposure counter; auto-retire when exposure exceeds
  threshold or discrimination drops (candidates all scoring the same =
  leaked or weak question).

## FR-9 Scheduling, notifications, access

- Slot self-scheduling within program windows; email/Slack invites and
  reminders; role-based access (candidate sees only own data; mentor
  sees assigned candidates; owner sees all).

# 6. Candidate experience requirements

- Pre-flight check (mic, camera, network, browser) with a 2-minute
  practice question that is never scored — reduces anxiety and
  calibrates audio.

- The avatar sets contract up front: “I will probe deeper on your
  answers — that is the format, not a sign you are failing.” Tone:
  professional client interviewer, firm but respectful; never sarcastic;
  matches the Participant Guide's promise of directness with dignity.

- Latency target: median avatar response gap under 1.0 s, p95 under 2.0
  s (cascade pipeline with streaming; below the 1.4–1.7 s industry
  median because interview pacing tolerates brief natural pauses — the
  avatar uses thinking acknowledgments to mask LLM latency).

- Accessibility: captions toggle, question repeat on request (logged),
  bandwidth-degraded audio-only fallback mode.

- Post-session: scorecard within 24 h (after mentor sign-off); candidate
  can replay their own recording with the evidence markers.

# 7. Recommended architecture

Cascaded real-time pipeline (industry default for tool-reliability and
observability), self-hostable, with the avatar as a rendering layer on
top:

|                     |                                                                                                                                                      |                                                                                                                                                                            |
|---------------------|------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Layer**           | **Recommendation**                                                                                                                                   | **Rationale / alternatives**                                                                                                                                               |
| Real-time transport | LiveKit (self-hosted or LiveKit Cloud) + LiveKit Agents. Use python sdk                                                                              | Video is first-class (needed for proctoring); scales concurrency; self-host path for productization. Alt: Pipecat (tighter voice pipeline, weaker multi-participant rooms) |
| STT                 | Deepgram streaming (or equivalent) with diarization                                                                                                  | 2026 production default; word timestamps feed evidence linking                                                                                                             |
| Interviewer brain   | Claude (API) with interview-plan state machine + Answer-Key grounding; MCP tools for bank lookup, editor state, timer                                | Probe-ladder control needs reliable tool use → cascade over speech-to-speech                                                                                               |
| TTS + avatar        | Streaming TTS (e.g., Cartesia-class) driving a streaming avatar API (evaluate: Simli, Tavus, HeyGen Interactive) — avatar vendor behind an interface | Avatar is the most replaceable layer; keep it swappable. Fallback: static portrait + waveform if vendor latency exceeds budget                                             |
| Proctoring service  | Separate agent consuming the same media tracks: gaze/face models client-side (MediaPipe) + server-side audio anomaly + event stream                  | Isolation mirrors the micro1 interviewer/integrity split; failure of proctoring never kills the interview                                                                  |
| Scoring service     | Async post-session pipeline: transcript + traces → LLM judge (Answer-Key-grounded) → draft scorecard; 20% consistency re-score                       | Batch, not real-time — cheap and retryable                                                                                                                                 |
| App backend         | Python fastapi + Postgres; object storage for recordings; queue for pipelines                                                                        | Anticlock decides the internals — this PRD constrains contracts, not frameworks                                                                                            |
| Data model          | Tenancy-ready: org_id on every table from day 1; single org in v1                                                                                    | Productize-later without a migration rewrite                                                                                                                               |
| App Frontend        | Typescript + React js                                                                                                                                |                                                                                                                                                                            |
| Database            | Postgressql                                                                                                                                          |                                                                                                                                                                            |
| Integration         | Python                                                                                                                                               |                                                                                                                                                                            |

*Build-vs-buy note: managed voice platforms (Vapi/Retell) reach a demo
fastest, but proctoring needs raw media access and productization needs
self-hosting — LiveKit Agents from day one avoids a guaranteed
re-platform.*

# 8. Non-functional requirements

|                    |                                                                                                                                                                                           |
|--------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Area**           | **Requirement**                                                                                                                                                                           |
| Concurrency        | v1: 10 simultaneous interviews; architecture headroom to 50 (cohort waves)                                                                                                                |
| Latency            | Median voice-gap \<1.0 s, p95 \<2.0 s; avatar lip-sync drift \<120 ms; editor keystroke sync \<200 ms                                                                                     |
| Availability       | 99% during business hours IST; mid-session recovery: reconnect-resume ≤2 min, session state checkpointed every 30 s                                                                       |
| Cost               | Target ≤ \$6 per 60-min interview all-in (STT+LLM+TTS+avatar+infra) at v1 volume; per-session cost visible on the dashboard from day one                                                  |
| Security & privacy | Recordings encrypted at rest; retention 12 months then purge (configurable); India DPDP-aligned consent and access; candidate right to view own data; scores visible only per role matrix |
| Auditability       | Every scorecard reconstructible: question asked → answer transcript → rubric anchor applied → score. No black-box scores                                                                  |
| Model governance   | Judge prompts and Answer-Key versions are versioned; a scorecard records which versions produced it                                                                                       |

# 9. Success metrics

- Adoption: 100% of pre-client mocks (UC1) run through the platform
  within 60 days of launch; ≥ 80% of weekly program mocks (UC2) by day
  90.

- Quality — the metric that decides everything: correlation between
  platform verdicts and real client-interview outcomes. Target:
  candidates rated “go” clear client interviews at ≥2× the historical
  rate; every miss triggers a calibration review.

- Human agreement: mentor adjusts ≤1 dimension per scorecard on average
  by day 60 (judge calibration converging); systematic adjustment
  patterns feed prompt fixes.

- Efficiency: mentor time per assessed candidate drops from ~75 min to
  ≤15 min; JD-to-readiness-report turnaround ≤48 h.

- Experience: candidate post-session rating ≥4/5 on fairness (“the
  interview tested real skills fairly”); dropout/abandon rate \<5%.

- Integrity: flag rate tracked (expect 5–10%); zero certified/“go”
  verdicts released with unresolved integrity flags.

# 10. Delivery phasing (Anticlock build plan)

|                          |                                                                                                                                                |                                                                                            |
|--------------------------|------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------|
| **Phase**                | **Scope**                                                                                                                                      | **Exit criterion**                                                                         |
| P0 — Spike (2 wks)       | LiveKit room + cascade voice loop + one avatar vendor + probe-ladder state machine on 5 bank questions; no scoring                             | A 15-min conversation that feels like an interview; latency measured                       |
| P1 — UC2 core (4–6 wks)  | Full session engine, editor, bank import, baseline proctoring (focus/paste/identity), scoring pipeline + mentor review UI, candidate scorecard | 10 real bench engineers complete assessments; mentors sign off; scores land in the Tracker |
| P2 — UC1 (3–4 wks)       | JD mapper, plan weighting, client-readiness report, scheduling for coordinator flow                                                            | One real client JD → mock → report cycle in ≤48 h                                          |
| P3 — Hardening (ongoing) | Gaze/audio-anomaly proctoring, question analytics + rotation, dashboard, cohort waves, cost tuning                                             | 50-person cohort wave runs without ops heroics                                             |

Parallel validation gate (critical): during P1, every AI-conducted
interview is shadow-reviewed by a human evaluator against the same
rubric until AI-vs-human score agreement is within 0.5 per dimension on
20 consecutive sessions. The platform does not replace human mocks until
it passes the same calibration bar we impose on human evaluators.

# 11. Risks and mitigations

|                                            |                                                                                                                                                                                            |
|--------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Risk**                                   | **Mitigation**                                                                                                                                                                             |
| Avatar/voice latency breaks immersion      | Streaming everywhere; thinking-acknowledgment fillers; avatar vendor behind an interface with audio-only fallback; latency budget tracked per release                                      |
| LLM judge scores drift from the human bar  | Answer-Key grounding, consistency re-scoring, shadow-review gate in P1, mentor-adjustment telemetry feeding prompt calibration — the same drift-monitoring philosophy as the human program |
| Candidates use AI copilots in the mock     | Adaptive probe ladder (copilots fail L2/L3 follow-ups and project-anchored questions), plus layered proctoring; integrity score with human review — friction + design, not detection alone |
| Question bank leaks across the cohort      | Exposure counters, rotation, discrimination analytics, project-anchored variants that cannot be shared                                                                                     |
| Candidate anxiety / rejection of AI format | Practice question, transparent contract, replayable recordings, human sign-off on every score, fairness NPS tracked                                                                        |
| Over-trust: AI verdict treated as truth    | Human sign-off mandatory; verdicts framed as recommendations; client-facing decisions always carry mentor names                                                                            |
| Anticlock dogfood slows product delivery   | P0 spike is deliberately Anticlock-native to surface tooling gaps early; keep an escape hatch to conventional build for the real-time media layer                                          |

# 12. Open questions for the build team

- Avatar vendor shortlist and latency bake-off (Simli vs Tavus vs HeyGen
  Interactive vs audio-only+portrait) — P0 deliverable.

- Code execution in-editor for v1, or read/discuss-only? (Recommend
  discuss-only in v1; execution in P3.)

- Self-host LiveKit from day one vs LiveKit Cloud for v1 with a
  migration plan?

- Where do gate-certification mocks stand legally in the program: does
  an AI-conducted session + human sign-off count as one of the two
  required interviewers? (Recommend: yes, with the signing mentor as the
  interviewer of record; policy call for the program owner.)

- Hindi/Tamil accent robustness of chosen STT — test with our own
  engineers in P0, not vendor benchmarks.
