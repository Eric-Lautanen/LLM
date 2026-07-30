# Coding Guru Models — English Foundation + Domain-Specific Dataset Architecture

**Status:** v4 design doc (v3 → v4: per-category subtype enumeration §4, 4th abstraction-level axis §4, per-category difficulty rubrics §4, format-specific skeleton schemas §3.2, per-category versioning §3.5.3, foundation-first training order §1.1, structural ROI metadata §4, foundation-only merge config preset §14, per-category sizing targets §13 and §14.4, 11 new axis-1 categories §4: root_cause_analysis, codebase_comprehension, technical_estimation, testing_strategy, system_operations, web_data_acquisition, intent_recognition, dialogue_coherence, se_concept_explanation, code_generation_from_spec, quantitative_reasoning, expanded tool_use subtypes for agentic stateful chaining §4, conversational intent/dialogue categories §4, OS-agnostic cross-platform principle §0/§1.1, synthesis-readiness scaffolding §14.4 — see §3.5.3, §4 axis 4, §14.4)
**Scale roadmap:** 100M → 500M → 1B → 2B → 4B (params)
**First languages:** Rust, Python
**Goal:** Train coding *gurus*, not assistants — models that justify decisions, push back on wrong approaches, ask clarifying questions, and reason correctly about tradeoffs, while remaining fully standalone (no dependency on other models to function).

---

## 0. Guiding Principles (Non-Negotiable)

- **Fully synthetic. No scraped internet data, ever.** All English and code data is generated, then mechanically and/or model-verified before it enters training. This is the primary "no slop" defense — verification gates (§6) and the slop filter (§7) are how this principle is enforced in practice, not just a stated intention.
- **Reasoning lives once, in English.** Anything true regardless of language belongs in the foundation skeleton. Anything requiring a specific language's semantics is a slot. See §1 for the full rule.
- **Agent-ready reasoning.** The foundation model must be loadable into any agent harness and produce correct tool calls, shell commands, file operations, and web requests across Windows, macOS, and Linux without per-platform retraining. All tool-use categories (§4) are trained as cross-platform patterns, not OS-specific recipes.
- **Guru, not assistant.** Justified pushback, clarifying questions, and correct disagreement are trained behaviors, not fallback behaviors — see `guru_pushback` and `security_posture` in §4.
- **Every domain model is standalone.** No runtime dependency on another model. See §5.
- **Instrumentation over perfection on v1.** Every gate should emit a number, even if that number isn't gated on yet. See §8.
- **Compute context:** target hardware is multiple consumer-grade GPUs, mid-to-high end. Iteration cadence target is multiple training runs per week once the generation pipeline is stable — this is a real constraint on gate cost (see §6.2, §8) and on why mix/weight changes are a config edit, not a regeneration (§9).
- **Foundation agnosticism:** skeletons must be OS- and platform-agnostic (§1.1). The reasoning gate enforces this as a schema violation.

---

## 1. Core Philosophy

Two distinct layers of knowledge, kept structurally separate but merged at pretrain time:

1. **English foundation layer** — language-agnostic reasoning: how to debug, how to disambiguate a vague request, how to weigh tradeoffs, how to teach, how to disagree with a user constructively, how to triage intent before answering a risky-looking request. This is where "guru" behavior lives, because guru behavior (justified pushback, Socratic teaching, correct disagreement, security triage) is structurally identical across languages.
2. **Language-specific layer** — the facts and idioms that only make sense inside one language's semantics (Rust's borrow checker, Python's GIL (Global Interpreter Lock), idiomatic patterns, ecosystem knowledge, actual verified code).

The foundation layer should carry as much of the reasoning weight as possible. The rule of thumb for what goes where:

> **Anything true regardless of language → skeleton (English foundation).**
> **Anything that requires knowing a specific language's actual semantics → slot (language-specific binding).**

This is not just an organizational preference — at small parameter counts (100M–4B), the model has little spare capacity to abstract away from surface phrasing, so getting this separation right *is* the difference between a model that generalizes a reasoning move and one that memorizes a template.

### 1.1 Training order: foundation first

The first training run uses the English foundation layer only — no language-specific bindings, no code artifacts, no coverage matrix. This serves three purposes:

1. **Validate the foundation independently** — a model trained on skeletons alone must still produce coherent reasoning. If bench scores are weak, the problem is in the skeleton taxonomy or generation quality, not in the binding layer.
2. **Establish baseline scores per cell** — every axis-1 × axis-2 × axis-3 cell gets a foundation-only score as the comparison point when bindings are added later.
3. **Keep language addition a linear cost** — adding a new language (Go, JS, C++, etc.) requires only generating bindings for the existing, bench-validated skeleton set; the foundation does not need regeneration.

**Foundation agnosticism requirement:** skeleton text must never reference OS-specific paths, package managers, shell commands, command-line tools (e.g. `grep`, `find`, `dir`), or platform conventions. Slot descriptions document what kind of content is expected without prescribing an OS convention — `PATH_SEPARATOR` rather than `"/"` or `"\\"`, `DEPENDENCY_COMMAND` rather than `"apt install"` or `"cargo install"`, `FILE_LISTING_COMMAND` rather than `"ls"` or `"dir"`, `TEXT_SEARCH_PATTERN` rather than `"grep"` or `"findstr"`. All tool-call skeletons must use the abstract tool schema (§3.2) with OS-neutral slot names; the binding layer fills in OS-specific command strings. The reasoning gate (§6.3) flags OS-specific skeletons (commands, paths, tool names baked into slot text) as a schema violation, not a style preference.

---

## 2. Directory / Project Structure

```
project_root/
├── ENGLISH/                          # foundation layer
│   ├── schema/                       # taxonomy definitions, versioned (see §3.5, §14.4)
│   │   ├── v1.md                     # global schema definitions (axis enums, manifest field shapes)
│   │   ├── v2.md                     # security_posture additions (harm_class, false_positive_flag)
│   │   ├── v3.md                     # interface_legibility, ecosystem_interactions, package_ref
│   │   ├── v4.md                     # per-category versioning, abstraction axis, format-specific schemas
│   │   ├── ... (one per global schema version)
│   │   └── <category>/               # per-category schema files (one dir per axis-1 category)
│   │       ├── subtypes.md           # enumerated subtype list for this category
│   │       ├── difficulty.md         # category-specific difficulty rubric
│   │       ├── category.json         # structural metadata (ROI, binding, valid formats)
│   │       ├── topics.json           # topic registry — concrete scenario seeds per subtype (see §14.5)
│   │       └── VERSION.md            # version history for this category (§3.5.3)
│   ├── data/
│   │   ├── requirement_disambiguation/
│   │   │   ├── missing_context/
│   │   │   ├── ambiguous_wording/
│   │   │   ├── contradictory_goals/
│   │   │   ├── implicit_assumptions/
│   │   │   ├── underspecified_boundary/
│   │   │   └── unstated_constraint/
│   │   ├── debugging_methodology/
│   │   │   ├── symptom_to_root_cause/
│   │   │   ├── binary_reduction/
│   │   │   ├── hypothesis_testing/
│   │   │   ├── environmental_vs_logical/
│   │   │   ├── heisenbug_diagnosis/
│   │   │   ├── regression_triage/
│   │   │   ├── non_determinism_debugging/
│   │   │   ├── production_debugging/
│   │   │   └── performance_debugging/
│   │   ├── algorithm_selection/
│   │   ├── guru_pushback/
│   │   │   ├── wrong_assumption/
│   │   │   ├── unsafe_shortcut/
│   │   │   ├── premature_optimization/
│   │   │   ├── overgeneralization/
│   │   │   ├── misapplied_pattern/
│   │   │   └── stale_knowledge_correction/
│   │   ├── security_posture/
│   │   │   ├── credential_harvesting/
│   │   │   ├── injection/
│   │   │   ├── sandbox_evasion/
│   │   │   ├── network_exfiltration/
│   │   │   ├── privilege_escalation/
│   │   │   ├── malware_construction/
│   │   │   └── reconnaissance_misuse/
│   │   ├── ... (all 31 axis-1 categories with their subtype directories, see §4)
│   ├── manifest.jsonl                # every concept_id + metadata
│   └── bench/                        # per-category, per-subtype, per-abstraction-level bench results
├── RUST/
│   ├── ENGLISH/                      # Rust-specialized English, mirrors foundation categories
│   │   ├── data/
│   │   │   ├── requirement_disambiguation/
│   │   │   ├── security_posture/
│   │   │   └── ...
│   │   └── manifest.jsonl            # each entry binds back to a foundation concept_id
│   ├── EXAMPLES/                     # verified Rust code
│   ├── bench/
│   └── merge_configs/                # per-target-scale mix recipes
└── PYTHON/
    ├── ENGLISH/
    ├── EXAMPLES/
    ├── bench/
    └── merge_configs/

Each category folder mirrors its subtype structure (defined in `subtypes.md`) so updates scoped to a single subtype don't require touching the rest of the category.
```

Category folder names mirror across languages for human navigation. The actual linking mechanism is the `concept_id`, not the folder structure (see §3).

---

## 3. The Interlocking Mechanism ("Interlocking Fingers")

Two distinct linking mechanisms, not one:

### 3.1 Concept ID — structural link (coordinate hash, not content hash)

Every foundation example gets a stable `concept_id`, derived from **category coordinates**, not from the text content:

```
concept_id = sha256(task_type + ":" + subtype + ":" + difficulty + ":" + abstraction_level + ":" + scenario_seed)
```

Where `scenario_seed` is a short concrete scenario description drawn from the **topic registry** — a per-category JSON file (`schema/<category>/topics.json`) listing every concrete scenario each subtype exercises (see §14.5 for the full schema). The scenario_seed is part of the coordinate just like `subtype` and `difficulty`, so changing the seed text (e.g. correcting a typo) would change the concept_id — but in practice seeds are never edited after their topic is created; they are retired via the topic_id lifecycle instead.

The `subtype` field is a per-category enumerated value identifying the specific sub-skill within an axis-1 category. Each axis-1 category defines its own enumerated list of valid subtypes in `schema/<category>/subtypes.md` (see §4 for the full hierarchy). Examples:

- `requirement_disambiguation`: `missing_context`, `ambiguous_wording`, `contradictory_goals`, `implicit_assumptions`, `underspecified_boundary`, `unstated_constraint`
- `debugging_methodology`: `symptom_to_root_cause`, `binary_reduction`, `hypothesis_testing`, `environmental_vs_logical`, `heisenbug_diagnosis`, `regression_triage`, `non_determinism_debugging`, `production_debugging`, `performance_debugging`
- `guru_pushback`: `wrong_assumption`, `unsafe_shortcut`, `premature_optimization`, `overgeneralization`, `misapplied_pattern`, `stale_knowledge_correction`
- `security_posture`: `credential_harvesting`, `injection`, `sandbox_evasion`, `network_exfiltration`, `privilege_escalation`, `malware_construction`, `reconnaissance_misuse`

The `abstraction_level` field identifies what kind of cognitive content the skeleton represents, independent of difficulty — see §4 for the full axis definition and per-category enumeration.

The `difficulty` field uses per-category difficulty rubrics rather than a one-size-fits-all scale — see §4 axis 3.

Content hashing is explicitly avoided: regenerating or improving an example must not orphan its downstream links. Coordinate-hashing keeps the ID stable across regeneration, which is what makes the "bench → patch → rebuild" loop viable. Because `subtype` and `abstraction_level` are enumerated and versioned per category (§3.5.3), adding a new subtype to a category produces new concept_ids from the new coordinates without invalidating any existing ones.

### 3.2 Template slots — the actual interlocking

Foundation examples are not flat prose — they are conversations with explicit fill points where language-specific content plugs in.

**Foundation skeleton (ENGLISH/data/debugging_methodology/...):**
```json
{
  "concept_id": "sha256(debugging_methodology:symptom_to_root_cause:expert:metacognitive:race_condition_report)",
  "category_version": "1",
  "abstraction_level": "metacognitive",
  "foundation_roi": "high",
  "prerequisites": [],
  "interaction_format": "multi_turn",
  "body": {
    "turns": [
      {"role": "user", "content": "{{SYMPTOM_DESCRIPTION}}"},
      {"role": "assistant", "content": "Before jumping to a fix, let's separate {{FAILURE_CLASS}} from {{ADJACENT_FAILURE_CLASS}}. The key diagnostic question is: {{DIAGNOSTIC_QUESTION}}..."}
    ]
  },
  "slots": ["SYMPTOM_DESCRIPTION", "FAILURE_CLASS", "ADJACENT_FAILURE_CLASS", "DIAGNOSTIC_QUESTION"],
  "requires_language_binding": true
}
```

**Extended skeleton fields:**

- `category_version` — the version of this specific category's subtype enumeration and slot conventions (§3.5.3). Independent of the global `schema_version`. Lets different categories evolve at different paces.
- `abstraction_level` — what kind of cognitive content this skeleton represents (§4 axis 4). Used by the merge config to control the ratio of meta-reasoning to procedural content independent of category weight.
- `foundation_roi` — estimated return on investment for this concept within the foundation layer (one of `high`, `medium`, `low`). A structural field, not a comment — the merge config can optionally filter or boost by ROI tier.
- `prerequisites` — array of `concept_id`s that this concept logically depends on. An empty array means the concept has no foundation-layer prerequisites. Reserved for future use in v1 — all prerequisites are empty until the category dependency graph is defined.
- `interaction_format` — which axis-2 format this skeleton uses. Determines the expected structure of the `body` field (see format-specific schemas below).
- `body` — the format-specific structure of the skeleton. Shape depends on `interaction_format`; the common fields (`concept_id`, `slots`, etc.) stay at the top level.

**Format-specific `body` schemas per axis-2 interaction format:**

Each axis-2 format has a defined skeleton body structure. The common fields (`concept_id`, `slots`, `verification`, etc.) are shared at the top level; only the `body` field's structure differs:

- **Single-turn Q&A**: `{"format": "single_turn", "user": "...{{SLOT}}...", "assistant": "...{{SLOT}}..."}`
- **Multi-turn dialogue**: `{"format": "multi_turn", "turns": [{"role": "user"/"assistant", "content": "..."}], "correction_markers": [{"turn_index": 2, "type": "user_correction", "replaces_assumption": "..."}]}`
- **Lecture / exposition**: `{"format": "lecture", "sections": [{"heading": "...", "content": "...{{SLOT}}..."}]}`
- **Code review dialogue**: `{"format": "code_review", "author_artifact": "...{{SLOT}}...", "reviewer_comments": [{"line_ref": "...", "severity": "correctness"|"security"|"performance"|"style", "comment": "...{{SLOT}}..."}], "author_response": "..."}`
- **Rubber duck**: `{"format": "rubber_duck", "user_stream": ["..."], "interjection_points": [{"at_turn": 2, "content": "...{{SLOT}}..."}]}`
- **Adversarial**: `{"format": "adversarial", "turns": [{"role": "user"/"assistant", "content": "..."}], "error_markers": [{"turn_index": 1, "error_type": "wrong_assumption"|"factual_error"|"unsafe_shortcut", "correct_content": "...{{SLOT}}..."}]}`
- **Tool-call transcript**: `{"format": "tool_call", "turns": [{"request": "...{{SLOT}}...", "tool_calls": [{"name": "...", "args": {...}, "result": "..."}], "reasoning": "...", "answer": "..."}]}`

The format-specific shape is validated at manifest-assembly time (stage 5). A skeleton whose `body` does not match its declared `interaction_format` schema is rejected before it reaches the manifest.

**Language binding (RUST/ENGLISH/data/debugging_methodology/...):**
```json
{
  "concept_id": "<same hash — this IS the link>",
  "binds_slots": {
    "SYMPTOM_DESCRIPTION": "program hangs intermittently under load, no panic",
    "FAILURE_CLASS": "data race masked by lock ordering",
    "ADJACENT_FAILURE_CLASS": "deadlock",
    "DIAGNOSTIC_QUESTION": "is this reproducible consistently, or does it vanish under a debugger (Heisenbug signature)?"
  },
  "language_specific_continuation": "...here's where Rust's ownership model rules out a whole category up front: if this compiled without unsafe, data races on memory are already off the table, so we're looking at..."
}
```

**Payoff:** the generic reasoning skeleton lives once. Every language's entry is a *bind*, not a rewrite. Improving the skeleton improves every language's model on next rebuild — no need to regenerate every language's dataset independently.

### 3.3 Paraphrase variants (memorization defense)

Each `concept_id` needs **4–8 paraphrased skeleton renderings**, not one canonical wording, randomly sampled at merge time (ideally re-rolled per epoch). Without this, small models at this scale will memorize the skeleton's surface phrasing instead of learning the underlying reasoning move.

### 3.4 Held-out paraphrase split (leakage defense)

A subset of paraphrase variants per `concept_id` must be generated but **never merged into training** — reserved for benchmarking only. Otherwise a model can appear to reason correctly while actually just completing a memorized skeleton seen in a different language's bind. Build this into the manifest schema from day one.

For `security_posture` specifically, this is extended with a **second, distinct held-out slice** — see §6.3 and schema v2.

### 3.5 Schema versioning

The `ENGLISH/schema/` directory holds versioned taxonomy definitions (axis-1/2/3/4 enums, slot-naming conventions, manifest field definitions). When a taxonomy change is needed (new task_type, new difficulty tier, renamed slot convention):

- Bump `schema_version` in a new file under `schema/` (e.g. `v1.md` → `v2.md`); never edit a shipped version in place.
- Existing `concept_id`s are never recomputed retroactively — a taxonomy change affects new generation only, not existing IDs. This keeps old bench results comparable across schema versions.
- Every manifest entry carries a `schema_version` field so old and new entries can coexist during a taxonomy transition without breaking the coverage matrix (§11.2).

#### 3.5.1 Schema v2 — `security_posture`

Supersedes v1 for new generation only; existing v1 concept_ids are not recomputed or invalidated. v1 and v2 entries coexist in the manifest, distinguished by `schema_version`.

1. **New axis-1 category: `security_posture`** — sits alongside `guru_pushback` in the taxonomy grid (§4). Structurally a specialized case of guru pushback: the user's surface request implies an intent or mental model that must be triaged — request → authorization/target diagnostic → harm-class classification → legitimate-adjacent-use check → safe alternative — before answering literally.

2. **New manifest field: `harm_class`** — required on every entry where `task_type == "security_posture"`, null elsewhere. Enumerated values (extend as needed; do not rename existing values once shipped — same non-retroactive rule as concept_id): `credential_harvesting`, `injection` (command / SQL / template / deserialization), `sandbox_evasion`, `network_exfiltration`, `privilege_escalation`, `malware_construction` (droppers, obfuscation, persistence), `reconnaissance_misuse` (scanning/enumeration framed for unauthorized use). Purpose: lets the coverage matrix (§11.2) and bench reports (§11.3) be filtered by harm class independently of language.

3. **New verification-block sub-field: `reasoning_gate.false_positive_flag`** (boolean, default `false`). Set `true` when the LLM judge determines the assistant turn over-refused a legitimate-adjacent-use request. Logged, not gated, in v1 — same posture as the existing disagreement-rate log (§6.3). Tracked as a distinct rate from the ordinary reasoning-gate disagreement rate, since the two fail in different directions.

4. **Hard schema constraint (enforced at manifest-assembly, stage 5, not just prompt instruction):** for any `security_posture` entry, `verification.code_gate` and `verification.test_gate` may only be non-null for the `SAFE_ALTERNATIVE_OFFERED` slot's bound artifact. Any artifact describing the harmful pattern itself must stay schematic (a labeled description) and is structurally disallowed from carrying a code_gate/test_gate block at all — an entry with a harmful-pattern artifact that also has a passing code gate is a manifest-assembly validation failure, rejected before it reaches the manifest.

5. **New bench split for this category only: `reframing_held_out`** — same `harm_class`, wrapped in a legitimacy-claiming frame ("for a CTF," "I'm the sysadmin," "for a class assignment"). Tests a different generalization axis than surface-wording paraphrase robustness and is scored separately.

6. **`category_weights` floor:** `security_posture` is not phased in at a later scale (unlike `ecosystem_deep_dives`) — non-zero weight starting at the 100M preset.

#### 3.5.2 Schema v3 — `interface_legibility`, `ecosystem_interactions`, freshness fields

Supersedes v2 for new generation only. v1, v2, and v3 entries coexist, distinguished by `schema_version`. This version formalizes the domain-specific category system for ongoing updates and retraining (§16/§17/§9) — the mechanism that lets a crate's breaking change, a CVE, or a new package version resolve to exactly the affected manifest rows and get regenerated without touching anything else, including the foundation skeleton.

1. **New axis-1 category: `interface_legibility`** — thin foundation skeleton only (§4). Slots:
   - `ARTIFACT_TYPE` — what kind of thing was produced (a module, a markup document, a struct crossing an FFI boundary, a schema, etc.)
   - `IMPLICIT_CONTRACT` — what a producer implicitly promises by how they structured the artifact (naming, comments, hook points)
   - `WHAT_A_CONSUMER_WOULD_ASSUME` — what a downstream reader (human or model) would reasonably infer without being told explicitly

   Two postures fill these slots differently per language binding: `producer_posture` (how to leave your own output legible) and `consumer_posture` (how to correctly read someone else's artifact) — a normal skeleton/binding pair, not a special case. **Explicitly not covered by the foundation skeleton:** any specific pairing (a Rust service consumed by a JS frontend, a Rust struct crossing into C via FFI, a MySQL schema consumed by an ORM) — those belong to `ecosystem_interactions` (below), never the foundation layer, to avoid the same combinatorial explosion cross-language-pair binding would cause.

2. **New language-specific-only bucket: `ecosystem_interactions.<package>`** — same status as `ecosystem_deep_dives` (§9): no `concept_id`, no cross-language binding, lives entirely inside one language's own `ENGLISH/data/` or `EXAMPLES/` tree. One sub-bucket per external package/tool a language commonly touches (e.g. `ecosystem_interactions.mysql`, `ecosystem_interactions.egui`) — this is the bucket a ~1,100-category Rust `std`-level list belongs in.

3. **New manifest field: `package_ref`** — required on every entry under `ecosystem_interactions.*` or `ecosystem_deep_dives`; optional elsewhere (an entry in an unrelated category that merely illustrates something using a given package should still carry this field so it's discoverable during a wipe):
   ```json
   "package_ref": {
     "name": "egui",
     "version_range": ">=0.29,<0.31"
   }
   ```
   Purpose: turns "a crate had a breaking change" into a manifest query (`delete where package_ref.name == "egui"`) instead of a directory-guessing exercise. This is the field the §16 change-detection watcher and wipe-and-regen loop depend on.

4. **New manifest field: `contributor_id`** — optional; present on entries generated through the crowdsourced flow (§18). Not for policing — same rationale as `schema_version`: if a category's bench score looks off later, tracing an entry back to which generation pass (person, prompt version, schema version) produced it is what makes it patchable rather than a mystery.

5. **Hard constraint carried over from the wipe-and-regen mechanism (§16.3):** a `package_ref`-driven delete may only ever target language-specific-only entries (`ecosystem_interactions.*`, `ecosystem_deep_dives`) or the language-binding half of a foundation concept — never the foundation skeleton itself. Manifest-assembly validation should reject any wipe request that would remove a row from `ENGLISH/manifest.jsonl` (as opposed to `RUST/ENGLISH/manifest.jsonl` / `PYTHON/ENGLISH/manifest.jsonl`) as a result of a `package_ref` match — skeletons don't carry package refs in the first place, but this is worth enforcing structurally rather than assuming it can't happen.

6. **Manifest verification block: no change in shape.** `interface_legibility` and `ecosystem_interactions` entries use the same `verification` block shape as any other category (§6.5) — code gate/test gate apply only where there's a compilable artifact.

**Why v2 and v3 stay separate versions rather than one combined bump:** they solve different problems — v2 is about recognizing intent before answering, v3 is about keeping language-specific content current without regenerating anything upstream of it. Versioning them separately keeps each diff reviewable on its own and keeps the non-retroactive rule honest: a v2-only entry and a v3-only entry can coexist indefinitely without either needing to backfill the other's fields.

#### 3.5.3 Per-category versioning (`category_version`)

In addition to the global `schema_version`, every manifest entry carries a `category_version` field — an integer, starting at `1`, scoped to the entry's own axis-1 category and subtype. This field is independent of the global schema version: a `requirement_disambiguation` entry might be at `category_version: 3` while a `guru_pushback` entry is still at `1`, even though both were generated under the same global `schema_version: 3`.

A category's version bumps when any of the following change:

1. **Subtype enumeration** — a new subtype is added, an existing one is deprecated (but never removed — same non-retroactive rule as `concept_id` and `harm_class`).
2. **Slot conventions** — an existing slot is renamed, a new required slot is introduced for this category.
3. **Difficulty rubric** — the per-category difficulty definitions change (new levels, redefined level criteria).
4. **Dependency graph** — the prerequisite structure within the category is updated. *(Reserved for future use — v1 categories have no defined dependency graph; this field is a placeholder for when intra-category prerequisites are formalized.)*

Each category's version history is tracked in `ENGLISH/schema/<category>/VERSION.md`, listing what changed at each bump and which concept_ids were generated under which version. This makes the impact of a taxonomy change traceable to individual manifest rows without bumping every category's version.

The `category_version` field is used by:

- **Merge configs (§9)** — a config can pin minimum/maximum category versions: `category_version_pin: {debugging_methodology: ">=2"}` to exclude concepts generated under an obsolete sub-type definition.
- **Coverage matrix (§11.2)** — the matrix can be filtered by category version to distinguish "we're weak in this category overall" from "we're weak only on the concepts generated under the old version."

---

## 4. Category Taxonomy — 4-Axis Grid

Rather than a flat list of thousands of categories, use a 4-axis grid. Each cell is one granular, independently benchable unit — this is what makes "in-house bench, then patch what's weak" actually tractable.

**Axis 1 — Cognitive task type** (with subtype enumeration)

Each category below lists its defined subtypes. The subtype list for each category lives in `ENGLISH/schema/<category>/subtypes.md` and is versioned independently (§3.5.3). New subtypes can be added to any category without affecting other categories or invalidating existing concept_ids.

- **Requirement disambiguation** — subtypes: `missing_context`, `ambiguous_wording`, `contradictory_goals`, `implicit_assumptions`, `underspecified_boundary`, `unstated_constraint`. Foundation ROI: high — generalizes almost entirely across languages.
- **Algorithm selection & justification** — subtypes: `complexity_analysis`, `correctness_vs_performance`, `space_time_tradeoff`, `approximation_vs_exact`, `algorithm_family_selection`, `input_characteristics_matching`. Foundation ROI: medium — some language-specific nuance in standard library availability.
- **Debugging methodology** — subtypes: `symptom_to_root_cause`, `binary_reduction`, `hypothesis_testing`, `environmental_vs_logical`, `heisenbug_diagnosis`, `regression_triage`, `non_determinism_debugging`, `production_debugging`, `performance_debugging`. Foundation ROI: high — the diagnostic structure is language-agnostic; only tool-specific steps differ.
- **Code review / critique** — subtypes: `correctness_review`, `security_review`, `performance_review`, `style_review`, `api_design_review`, `conformance_review`, `review_prioritization`. Foundation ROI: medium — prioritization hierarchy (correctness > security > performance > style) is foundation; specific anti-pattern catalogs are language-specific.
- **Refactoring rationale** — subtypes: `complexity_reduction`, `duplication_elimination`, `interface_extraction`, `paradigm_migration_path`, `safe_refactoring_boundaries`, `dependency_decoupling`, `legacy_modernization`. Foundation ROI: medium — principles of safe refactoring are language-agnostic; tooling support differs.
- **Tradeoff analysis** — subtypes: `time_vs_space`, `readability_vs_performance`, `flexibility_vs_simplicity`, `abstraction_overhead`, `library_vs_handrolled`, `consistency_vs_optimization`. Foundation ROI: high — tradeoff structure is purely conceptual.
- **Explaining code to different skill levels** — subtypes: `novice_explanation`, `peer_explanation`, `stakeholder_summary`, `deep_dive_analysis`. Foundation ROI: medium — audience calibration is foundational; specific code examples are slots.
- **Code generation from spec / implementation reasoning** — subtypes: `function_implementation` (given signature + behavioral description, write the body), `component_construction` (given module/class requirements, design and implement), `endpoint_implementation` (given API contract, implement the handler), `data_logic_implementation` (given transformation rules, implement processing), `behavioral_change_implementation` (given existing code + change request, produce the modified code), `scaffolding_generation` (given project structure requirements, generate setup/boilerplate). Foundation ROI: high — the reasoning about decomposing a spec into implementation steps, handling edge cases in the spec, and structuring output is identical regardless of language. The actual code output is a slot filled per language.
- **API / interface design reasoning** — subtypes: `naming_convention_design`, `parameter_ordering`, `error_surface_design`, `extensibility_vs_simplicity`, `backward_compatibility`, `discoverability`, `versioning_strategy`. Foundation ROI: high — API design principles transfer across all languages.
- **Test case design & edge-case enumeration** — subtypes: `boundary_analysis`, `equivalence_partitioning`, `state_space_coverage`, `error_path_testing`, `property_based_thinking`, `regression_prevention`, `integration_test_design`, `mocking_strategy`. Foundation ROI: high — test design methodology is entirely language-agnostic.
- **Error message interpretation** — subtypes: `compiler_error_decoding`, `runtime_crash_analysis`, `log_triage`, `stack_trace_navigation`, `error_code_lookup_strategy`. Foundation ROI: medium — the meta-skill of reading errors is foundational; specific error formats are language-specific.
- **Performance reasoning** — subtypes: `bottleneck_identification`, `complexity_classification`, `io_vs_compute`, `caching_strategy`, `lazy_vs_eager`, `parallelism_opportunity`, `database_query_performance`, `profiling_approach`. Foundation ROI: high — performance reasoning patterns are purely conceptual.
- **Quantitative reasoning for SE** — subtypes: `complexity_estimation` (big-O analysis, recurrence relations, comparing algorithm costs), `back_of_envelope_calculation` (estimating storage, bandwidth, latency, costs at scale), `probability_for_testing` (flaky test probability, sampling theory, false positive/negative rates), `statistical_reasoning` (benchmark variance, A/B comparison, confidence intervals), `boolean_and_logic` (truth tables, De Morgan's laws, logical equivalence, condition simplification), `geometric_spatial_reasoning` (coordinate systems, grids, spatial indexing, collision detection). Foundation ROI: high — the math needed for SE reasoning is entirely language-agnostic. This is the primary category for "how much storage for 1M users," "which is faster O(n log n) or O(n²)," and similar quantitive SE questions at the foundation layer.
- **Architecture / system decomposition** — subtypes: `module_boundary_definition`, `dependency_injection`, `layer_separation`, `interface_contract_design`, `configuration_strategy`, `error_boundary_design`. Foundation ROI: high — architectural patterns are language-agnostic.
- **Documentation generation** — subtypes: `doc_comment_writing`, `readme_composition`, `architecture_decision_record`, `change_log_writing`, `tutorial_structure`. Foundation ROI: medium — documentation structure is foundational; language-specific doc tooling differs.
- **Paradigm translation** — subtypes: `imperative_to_functional`, `oop_to_data_oriented`, `synchronous_to_async`, `blocking_to_reactive`, `procedural_to_declarative`. Foundation ROI: high — paradigm mapping is purely conceptual; only syntax changes per language.
- **Instruction-following under ambiguity** — subtypes: `partial_spec_execution`, `conflicting_instruction_resolution`, `implicit_constraint_inference`, `scope_negotiation`. Foundation ROI: high — ambiguity resolution is the core of the guru behavior.
- **Multi-turn correction** — subtypes: `assumption_reversal`, `scope_correction`, `mid_answer_correction`, `partial_retraction`, `clarification_seeking`, `correction_acknowledgement`, `self_correction` (model recognizes and corrects its own error mid-turn or in a follow-up turn, explaining what was wrong and why the correction is right). Foundation ROI: high — correction handling is foundational guru behavior.
- **Guru pushback / justified disagreement** — subtypes: `wrong_assumption`, `unsafe_shortcut`, `premature_optimization`, `overgeneralization`, `misapplied_pattern`, `stale_knowledge_correction`. Foundation ROI: high — near-100% foundation; the structure of justified pushback is identical across all domains.
- **Security posture / intent triage** — subtypes (same as `harm_class` enum): `credential_harvesting`, `injection`, `sandbox_evasion`, `network_exfiltration`, `privilege_escalation`, `malware_construction`, `reconnaissance_misuse`. Foundation ROI: high — ~90% foundation (triage shape is language-agnostic); only idiom-specific pattern recognition is language-specific.
- **Interface legibility** — subtypes: `producer_posture`, `consumer_posture`. Foundation ROI: medium — deliberately thin; only the generic producer/consumer reasoning lives here. Language-specific pairings live in ecosystem_interactions.
- **Spec writing** — subtypes: `behavioral_spec`, `contract_spec`, `acceptance_criteria`, `error_spec`. Foundation ROI: high — spec structure is independent of language.
- **Socratic teaching** — subtypes: `guided_discovery`, `counterexample_leading`, `analogy_based`, `scaffolded_questioning`. Foundation ROI: high — Socratic structure is purely pedagogical, language-agnostic.
- **Tool use / agentic task execution** — subtypes: `tool_selection`, `call_construction`, `result_interpretation`, `error_recovery`, `multi_tool_sequencing`, `tool_chain_planning`, `confidence_estimation`, `stateful_multi_step_planning`, `tool_output_integration`. Foundation ROI: high — the pattern of tool use (when to call, how to interpret, when to retry, when not to use a tool at all, how to chain dependent calls where later steps consume earlier results) transfers across all tool ecosystems.
- **Research methodology** — subtypes: `query_formulation`, `source_evaluation`, `claim_verification`, `confidence_calibration`, `negative_result_interpretation`, `knowledge_gap_identification`. Foundation ROI: high — research skills are entirely language-agnostic.
- **SE concept explanation** — subtypes: `definition_query` (explain what a concept is), `mechanism_explanation` (explain how something works under the hood), `comparison_query` (compare/contrast two concepts), `why_explanation` (explain rationale or design motivation), `application_query` (explain when and why to use a given concept). Foundation ROI: high — factual SE knowledge queries, no language binding needed. This is the primary category for simple "what is X" / "how does X work" Q&A at the foundation layer.
- **Intent recognition & user request parsing** — subtypes: `question_type_classification` (factual, procedural, explanatory, comparative, hypothetical, open-ended vs closed-ended), `indirect_speech_act_recognition` (recognizing indirect requests, suggestions, and commands phrased as questions or statements), `multi_part_request_decomposition` (splitting compound requests into constituent intents), `negation_and_qualification_handling` (understanding what is being excluded, conditionalized, or scoped), `user_expertise_and_urgency_signaling` (inferring the user's familiarity level and priority from word choice and phrasing), `implicit_intent_inference` (recognizing unstated goals the user likely has but didn't express). Foundation ROI: high — intent parsing is purely about natural language understanding, independent of any domain or language.
- **Dialogue coherence & meta-communication** — subtypes: `discourse_context_maintenance` (tracking what has been established across turns and referring back to it), `topic_shift_management` (initiating and responding to topic changes gracefully), `anaphora_and_reference_resolution` (resolving pronouns, definite descriptions, and ellipsis to their antecedents in the conversation), `clarification_request_formulation` (knowing when and how to ask the user for more information vs. inferring from context), `uncertainty_expression` (communicating confidence levels and knowledge boundaries to the user), `conversation_summarization` (condensing prior turns to re-establish common ground after a long or complex exchange). Foundation ROI: high — dialogue mechanics are the infrastructure all other conversational skills depend on; they are independent of topic, domain, or language.
- **Root cause & incident analysis** — subtypes: `postmortem_writing`, `system_failure_analysis`, `contributing_factor_identification`, `prevention_planning`, `timeline_reconstruction`. Foundation ROI: high — incident analysis methodology is independent of technology stack; only remediation tooling differs.
- **Codebase comprehension** — subtypes: `execution_trace_reading`, `codebase_structure_mapping`, `dependency_graph_analysis`, `unfamiliar_pattern_decoding`, `entry_point_identification`. Foundation ROI: high — the skill of reading unfamiliar code without running it is purely conceptual, language-agnostic.
- **Technical estimation & planning** — subtypes: `effort_estimation`, `task_decomposition`, `dependency_sequencing`, `risk_assessment`, `confidence_ranging`. Foundation ROI: high — estimation reasoning patterns (decomposition, historical analogy, uncertainty communication) transfer across all domains.
- **Testing strategy** — subtypes: `unit_vs_integration`, `coverage_prioritization`, `test_architecture_design`, `mock_vs_real`, `regression_strategy`. Foundation ROI: high — strategy-level testing decisions are independent of test framework or language.
- **System operations** — subtypes: `file_path_navigation` (navigating directory trees, absolute vs relative paths, cross-platform path conventions), `file_content_operations` (reading, writing, appending, encoding detection), `process_lifecycle` (starting, monitoring, signaling, terminating processes — conceptually), `environment_configuration` (environment variables, config files, permission models), `cross_platform_boundary` (identifying when a command or path is OS-specific and how to generalize or flag). Foundation ROI: high — filesystems and processes are conceptual structures with different surface forms per OS; the reasoning patterns (find → check → read → parse → decide) are identical regardless of platform.
- **Web data acquisition** — subtypes: `request_formulation` (HTTP methods, headers, query parameters, body construction), `response_interpretation` (status codes, content negotiation, error responses, streaming), `authentication_integration` (API keys, tokens, basic auth — as patterns, not specific implementations), `rate_limit_navigation` (backoff strategies, retry logic, throttling, caching), `web_content_extraction` (parsing structured responses, extracting information from semi-structured content, handling pagination). Foundation ROI: high — HTTP is a universal protocol; the reasoning patterns (request → response → parse → validate → use) are identical across all languages and platforms.

The `foundation_roi` field listed for each category above is structural metadata, stored in the category's `subtypes.md` and usable in merge configs to filter or boost entire ROI tiers independently of individual category weights.

**Axis 2 — Interaction format**
- Single-turn Q&A
- Multi-turn dialogue with correction/pushback
- Lecture / exposition (monologue teaching)
- Code review dialogue (two personas)
- "Rubber duck" — user thinks aloud, model guides
- Adversarial — user is wrong, model must correctly disagree
- Tool-call transcript (request → tool call → tool result → reasoning → answer)

**Axis 3 — Difficulty / level (per-category rubric)**

Rather than a single difficulty scale, each category defines its own difficulty rubric in `schema/<category>/difficulty.md`. The following labels are standardized across categories, but their concrete meaning is category-specific:

- `novice` — single-step reasoning, no prerequisite concepts required, conversational context fits in a single turn.
- `intermediate` — multi-step reasoning, requires applying one or two prerequisite concepts, moderate context length.
- `expert` — multi-step reasoning with branching paths, requires integrating multiple prerequisite concepts, context spans several turns.
- `frontier` — reasoning in the presence of ambiguity, conflicting signals, incomplete information, or novel situations not covered by existing patterns. The "guru-consulting-on-ambiguous-real-world-mess" tier.

Each category's `difficulty.md` defines what these labels mean specifically for that category's skill domain. For example, a `novice` algorithm_selection concept might ask "pick sort algorithm for a small already-sorted list" while a `frontier` one might ask "design a caching strategy for an unpredictable workload with memory constraints you have to discover by questioning the user."

**Axis 4 — Abstraction level** (what kind of cognitive content)

This axis is independent of difficulty — a metacognitive concept can exist at any difficulty level. The abstraction level is stored as a field on each skeleton (`abstraction_level`) and is usable in merge configs to control the ratio of high-level reasoning to procedural content independently of category weights.

- `metacognitive` — reasoning about *when* and *why* to apply a skill, not *how*. Examples: "should you debug this or redesign?", "is this worth optimizing?", "when is it safe to skip tests?"
- `procedural` — step-by-step how to execute a skill. Examples: "how to isolate a root cause using binary search," "how to write a behavioral spec from a vague requirement."
- `pattern_recognition` — identifying when a known pattern applies. Examples: "does this failure signature match a deadlock or a race condition?", "is this an edge case or the common path?"
- `declarative` — factual knowledge about a domain. Examples: "what is a race condition?", "what does ACID stand for?"

Every skeleton must declare exactly one abstraction level. This lets the merge config and bench reports (§11.3) distinguish "the model can recite the steps" from "the model knows when to apply them" — two very different failure modes that get averaged together if abstraction level isn't tracked.

Each (task_type, subtype, format, difficulty, abstraction_level) quintuple = one benchable cell. Weighting across these cells is a **merge-time config decision**, not a data-generation decision (§9).

### Priority weighting metadata

The following table captures the structural metadata for each axis-1 category. This data lives in `schema/<category>/category.json` and is consumed by the merge config (§9) and coverage matrix (§11.2):

| Category | Foundation ROI | Slots (count) | Language binding | Phase-in scale |
|---|---|---|---|---|
| requirement_disambiguation | high | 3-5 | optional | 100M |
| debugging_methodology | high | 3-6 | recommended | 100M |
| algorithm_selection | medium | 2-4 | recommended | 100M |
| code_review_critique | medium | 3-5 | required | 100M |
| refactoring_rationale | medium | 2-4 | recommended | 100M |
| tradeoff_analysis | high | 2-4 | optional | 100M |
| explaining_code | medium | 2-3 | required | 100M |
| api_design_reasoning | high | 2-4 | recommended | 100M |
| test_case_design | high | 2-4 | optional | 100M |
| error_message_interpretation | medium | 2-4 | required | 100M |
| performance_reasoning | high | 2-4 | optional | 100M |
| quantitative_reasoning | high | 2-4 | optional | 100M |
| architecture_decomposition | high | 2-5 | optional | 100M |
| documentation_generation | medium | 2-3 | required | 500M |
| paradigm_translation | high | 2-3 | recommended | 100M |
| instruction_following_ambiguity | high | 2-4 | optional | 100M |
| multi_turn_correction | high | 2-4 | optional | 100M |
| guru_pushback | high | 2-4 | optional | 100M |
| security_posture | high | 4-6 | recommended | 100M |
| interface_legibility | medium | 3 | required | 100M |
| spec_writing | high | 2-4 | optional | 100M |
| socratic_teaching | high | 2-3 | optional | 100M |
| tool_use | high | 3-5 | required | 100M |
| research_methodology | high | 2-4 | optional | 100M |
| se_concept_explanation | high | 2-4 | optional | 100M |
| root_cause_analysis | high | 3-5 | optional | 100M |
| codebase_comprehension | high | 2-4 | optional | 100M |
| code_generation_from_spec | high | 3-5 | required | 100M |
| technical_estimation | high | 2-4 | optional | 100M |
| testing_strategy | high | 2-4 | optional | 100M |
| system_operations | high | 3-5 | optional | 100M |
| web_data_acquisition | high | 3-5 | optional | 100M |
| intent_recognition | high | 2-5 | optional | 100M |
| dialogue_coherence | high | 2-4 | optional | 100M |

Categories with `foundation_roi: high` should receive proportionally more concept_ids in the v1 generation run and higher baseline weights in the default merge config. Categories with `Language binding: required` are fully valid in the foundation-first training run (they get generic slot fills instead of language-specific ones — see §11.1 stage 1 substep) — the binding requirement only matters once language-specific training begins. Categories at `Phase-in scale: 500M` are excluded from the 100M foundation run.

---

## 5. Standalone Model Requirement

Each domain-specific model (Rust, Python, future languages) must be **fully standalone** — no runtime dependency on any other model to function. Implications for dataset design:

- Every model gets its own complete copy of the merged foundation + language-specific data at train time (pretrain-merge, not runtime routing/MoE-to-another-model).
- "Knowledge to research if need be" means the model needs **tool-use, research-methodology, and conversational-intent training data** baked into its own foundation slice (web search, doc lookup, running a compiler/REPL) — not an assumption that a router or bigger model handles that for it. The `intent_recognition` and `dialogue_coherence` categories (§4) ensure the model can parse user requests in free-form natural language without depending on an upstream orchestration model to reformat them.
- Likewise, security triage is baked into the model's own weights via `security_posture`, not deferred to an external moderation layer or RLHF pass applied after training. This is the main practical motivation for the category: a small, fast-iterating domain model can absorb this behavior at pretrain time and get re-benched/re-weighted in the same weekly loop as everything else (§9), rather than needing a separate alignment pass per model per language.
- No shared inference-time scaffolding across language models. Portability of the *skeleton* happens at data-build time; at inference time each model is self-contained.

---

## 6. Verification Gates (Code + Reasoning)

Compiles-and-lints is a real floor, but it only verifies the **code**, not the **English explaining the code**, and it doesn't fully rule out logically-wrong-but-compiling code. Three gates in total — the code gate and test gate apply only to entries with a compilable code artifact; the reasoning gate applies to every entry, code-bearing or not:

### 6.1 Code gate (mechanical, cheap, automatable)
- Rust: `cargo check`, `clippy`, `fmt`, MSRV (Minimum Supported Rust Version) check
- Python: `mypy`/`ruff` (or equivalent static checks), plus runtime test pass — no compiler equivalent, so this gate leans more heavily on the test gate

### 6.2 Test gate
- Spec-first generation: write the **behavioral spec in English independently**, before either code or test. Generate code and tests independently *from the spec*, not from each other. This breaks the circularity failure mode where a model's wrong mental model produces both a wrong implementation and a test that happens to confirm it.
- Example-based tests for v1 (cheap, catches the worst offenders).
- Deferred to v2+: property-based tests (proptest), differential testing against a reference implementation, mutation testing (cargo-mutants or equivalent) as a sampled QA check on test *meaningfulness*, not a per-example gate (too expensive to run on everything at this iteration cadence).

### 6.3 Reasoning gate
- LLM-judge pass that fact-checks English claims about the code against the verified code itself (e.g., does the stated complexity claim match reality, does the stated reason the borrow checker rejects something match reality).
- v1: **log disagreement rate per category, don't gate on it yet** — establish the baseline before setting a threshold.
- **`security_posture` addition:** the judge tracks a second, distinct rate — `false_positive_flag` — for over-refusal (e.g. refusing a standard port-scanner exercise or a textbook SQL-injection explanation). Over-refusal is a different failure mode from under-refusal and must be logged separately, not averaged into the same disagreement number, or it becomes invisible.
- **`security_posture` bench split:** in addition to the standard held-out paraphrase split (§3.4), a `reframing_held_out` slice is reserved — same harm class, wrapped in a legitimacy-claiming frame ("for a CTF," "I'm the sysadmin," "for a class"). Paraphrase-robustness and reframing-robustness are different generalization axes and are scored independently.

### 6.4 Hard constraint for `security_posture` entries specifically
For any entry in this category, an artifact describing the harmful pattern itself must stay **schematic** (a labeled description of the shape, e.g. "reads the cookie store, POSTs it to a remote host") and must never be a compilable/runnable artifact. Only the `SAFE_ALTERNATIVE_OFFERED` slot's bound content may carry a `code_gate`/`test_gate` block. This is enforced at manifest-assembly time (stage 5, §11.1) as a structural validation, not left as a generation-prompt instruction — an entry that pairs a harmful-pattern artifact with a passing code gate is rejected outright, the same as a failed compile.

### 6.5 Manifest verification block (schema shape)
```json
{
  "verification": {
    "code_gate": {"check": "pass", "clippy": "pass", "fmt": "pass", "msrv": "1.74"},
    "test_gate": {"test": "pass", "method": "example_based", "mutation_score": null},
    "reasoning_gate": {"method": "llm_judge_v1", "status": "logged", "flagged_claims": [], "false_positive_flag": false}
  }
}
```
Generic shape, language-specific tool list plugged in per language (Rust vs. Python tool sets differ; schema stays the same). `false_positive_flag` is new in schema v2 and is required (defaulting to `false`) on every entry, most relevant for `security_posture`.

---

## 7. Slop Filter (v1 gate, rule-based)

Explicit, checkable filter stage — not left as editorial instinct:
- Hedging padding ("It's important to note that...") — strip
- Restating the question before answering — strip
- Generic filler praise in multi-turn ("Great question!") — strip
- "What without why" answers — reject/regenerate, not strip (this is the core value of the foundation layer)
- Redundant caveats repeated across turns — strip after first occurrence

Track rejection rate per category. A category with abnormally high rejection rate indicates a bad generation prompt template for that category — this is diagnostic signal to feed back into the pipeline.

---

## 8. v1 Gate Stack (What Ships Now vs. Logged vs. Deferred)

**Ship in v1 (gate on this):**
- cargo check / clippy / fmt / MSRV (Rust); mypy/ruff (Python)
- Example-based tests from independently-written spec
- Rule-based slop filter
- `security_posture` structural constraint (§6.4 — harmful-pattern artifacts may never carry a code/test gate)

**Log, don't gate on yet (establish baseline):**
- Reasoning-gate LLM judge disagreement rate, per category
- `security_posture` false-positive (over-refusal) rate, per category
- Mutation score, sampled subset per category

**Explicitly deferred (known gap, written down, not silently skipped):**
- Property-based / differential testing at scale
- Full mutation-testing coverage

This is intentional: v1's job is not to be perfect, it's to produce **instrumented data** — every gate emitting a number — so "improve over time" is a measured loop against real per-category numbers, not a guess.

---

## 9. Merge-Time Config (Scale-Invariant Schema, Scale-Specific Presets)

The taxonomy, concept_id scheme, and manifest schema stay fixed across the entire 100M → 4B roadmap. What changes per scale is the **merge recipe**: mix ratios, category inclusion, paraphrase sampling. This avoids maintaining parallel datasets per model size — one dataset, multiple merge recipes.

```yaml
target_scale: 100M
mix:
  foundation_weight: 0.40
  language_specific_weight: 0.60
  paraphrase_sampling: random_per_epoch
  category_weights:
    requirement_disambiguation: 1.2
    guru_pushback: 1.3
    security_posture: 1.3          # non-zero from the smallest scale, not phased in
    interface_legibility: 1.1      # thin foundation category, non-zero from the start
    debugging_methodology: 1.0
    syntax_reference: 0.5          # cheap to learn, low reasoning value — undersample
    ecosystem_deep_dives: 0.0      # not viable at this scale yet — excluded
    ecosystem_interactions.egui: 0.0     # per-package bucket, phased in like ecosystem_deep_dives
    ecosystem_interactions.mysql: 0.0
  bench_gate: rust_bench_v1
---
target_scale: 4B
mix:
  foundation_weight: 0.25
  language_specific_weight: 0.75
  paraphrase_sampling: random_per_epoch
  category_weights:
    requirement_disambiguation: 1.1
    guru_pushback: 1.2
    security_posture: 1.2
    interface_legibility: 1.1
    debugging_methodology: 1.0
    syntax_reference: 0.6
    ecosystem_deep_dives: 1.0      # now included
    ecosystem_interactions.egui: 0.8    # now included — one weight per tracked package
    ecosystem_interactions.mysql: 0.8
  bench_gate: rust_bench_v3
```

**Note on category names above:** `requirement_disambiguation`, `guru_pushback`, `security_posture`, `interface_legibility`, and `debugging_methodology` are foundation axis-1 categories (§4) with a `concept_id` and cross-language binding. `syntax_reference`, `ecosystem_deep_dives`, and the new **`ecosystem_interactions.<package>`** family are **language-specific-only categories** — they live entirely inside `RUST/ENGLISH/` or `RUST/EXAMPLES/` with no foundation-layer skeleton, no `concept_id`, and no cross-language binding, since a Rust syntax reference (or a Rust+MySQL interaction pattern) has no meaningful Python equivalent to bind to. `category_weights` can freely mix both kinds; only the foundation ones appear in the coverage matrix (§11.2), since there's nothing to check coverage of for a category that was never meant to exist in more than one language.

Unlike `ecosystem_deep_dives`, `security_posture` and `interface_legibility` are **not** phased in at a later scale — both carry a non-zero floor starting at 100M, on the same footing as `guru_pushback`.

**`ecosystem_interactions` is where per-crate/per-package granularity lives** (a 1,100-category Rust `std`-level list is a realistic starting size for this bucket alone). Every entry here — not just the folder, the manifest row itself — carries a `package_ref: {name, version_range}` field so a version-bump or breaking-change event can be resolved to a manifest query (`delete where package_ref.name == "egui"`) instead of a directory-guessing exercise, and so an entry that merely *illustrates* something using a given package (e.g. an error-handling example that happens to use egui) is still discoverable and wipeable even outside its own dedicated folder. This is the mechanism §16 relies on for keeping crate/package examples current without touching the interlocking skeleton.

Weekly iteration loop becomes: bench → identify weak `concept_id`s or categories → adjust `category_weights` or patch specific foundation/binding entries → re-merge → retrain. No pipeline regeneration needed for a ratio tweak.

---

## 10. Model Capabilities Roadmap (Architecture-Agnostic Requirements)

Architecture itself is not fixed — but every scale in the roadmap needs training data that supports:

- **Variable reasoning depth** — short direct answers for simple queries, extended chain-of-thought style reasoning for ambiguous/complex ones. Needs its own axis-2 format variants (terse vs. extended-reasoning versions of the same concept_id) so the model learns *when* to reason at length, not just *how*.
- **Tool calling** — structured tool-call transcript format (request → tool call → tool result → reasoning → answer) as a first-class axis-2 interaction format, present in the foundation layer so the *pattern* of tool use (when to call, how to interpret results, when to retry) transfers across languages. Language-specific tool bindings (cargo, clippy, rustc, mypy, pytest, pip) live in the language layer.
- **Research methodology** — since models must be standalone and only need "knowledge to research if need be," the foundation layer needs an explicit category teaching *how* to research (formulating a search query, evaluating source reliability, verifying a claim against a primary source, knowing when confidence is too low to answer without checking) rather than assuming a bigger orchestrating model handles this.
- **Multi-turn state tracking** — correction, clarification, and disagreement across turns, consistent with the guru-not-assistant goal.
- **Conversational intent parsing** — the model must understand user requests expressed in any natural language form, not just structured or template-based inputs. The `intent_recognition` and `dialogue_coherence` categories provide this foundation, independent of any coding-specific knowledge.

None of this requires committing to a specific architecture now — it requires the *dataset* to contain these interaction shapes so whatever architecture is chosen at each scale has the right training signal to develop the capability.

---

## 11. Training Pipeline (Stubbed — Architecture-Agnostic)

End-to-end flow from empty repo to a trained checkpoint. Each stage below is a stub — the concrete tooling (which generation model, which trainer) is an implementation choice, not a design constraint, but the *stages and their order* are load-bearing.

### 11.1 Pipeline stages

1. **Skeleton generation** (ENGLISH foundation) — the generation runner (§14.8) reads the sweep ledger and topic registries, plans a work queue (`ENGLISH/sweep/queue.jsonl`), and dispatches cells to provider workers. Each cell produces N paraphrase variants per `concept_id` per the taxonomy grid (§4), across the held-out/train split (§3.4). For `security_posture`, also generate the `reframing_held_out` slice (§6.3). Output: raw skeleton candidates with `{{SLOT}}` placeholders, format-specific body structure per §3.2, and all required metadata fields (`abstraction_level`, `foundation_roi`, `prerequisites`, `category_version`, `interaction_format`).

   **Foundation-only slot fill substep (§14.9):** after generation, replace `{{SLOT}}` markers with generic, semantically-neutral filler text from the slot-fill dictionary (`schema/slot_fills.json`). Each slot name has 5 hand-written filler options; the filler selects one at random per variant for diversity. Unknown slot names log a warning and use a default string. The binding stage (§11.1 stage 3) replaces this mechanism with language-specific fills when coding-language bindings are active — the architecture is identical (dictionary lookup → text replacement), only the dictionary source changes. This prevents the model from training on literal template syntax while keeping the skeleton's structure intact.

   **Within-cell fingerprint dedup substep:** generate M candidate variants (M > target_count, e.g. M=12 for target_count=6). Compute a 5-gram or 8-gram fingerprint of each candidate's slot content and conversation structure. Build pairwise Jaccard similarity and cluster, keeping only the most diverse set of size target_count. Discarded candidates are logged for diagnostics; if the diverse set is below target_count, regenerate replacements. This runs before the slop filter to avoid wasting gate compute on near-duplicates.
2. **Skeleton slop filter + reasoning gate** (§14.4) — rule-based filter (§7) runs first. Then the foundation-only reasoning gate checks language-agnosticism, internal consistency, slot sufficiency, and reasoning quality. No code exists yet, so the code and test gates are skipped in this pass. Failing entries are rejected and re-queued for regeneration.
3. **Slot binding generation** (per language, foundation-only pass uses generic fills instead) — for each foundation `concept_id` flagged `requires_language_binding`, generate the language-specific slot fills + continuation. For code-bearing concepts, this stage also produces: the independent behavioral spec, the code, and the test (generated independently from the spec, per §6.2 — not from each other). For `security_posture` concepts, the harmful-pattern description stays schematic and only the safe-alternative artifact gets a real, gate-eligible implementation (§6.4). **In the foundation-only training run (§1.1), this stage is replaced by the generic slot fill substep (§11.1 stage 1) — skeletons with `requires_language_binding: true` get generic English fills instead of empty/unbound slots, so the model never trains on literal `{{SLOT}}` markers.**
4. **Verification gate run** (§6) — code gate (compiler/linter), test gate (test execution, sampled mutation score), reasoning gate (LLM judge, logged not gated in v1; false-positive rate logged separately for `security_posture`). Failing entries are rejected and re-queued for regeneration, not silently dropped — rejection reasons get logged per category (feeds §7's diagnostic loop). **Foundation-only pass: reasoning gate only (criteria per §14.4); code and test gates are N/A.**
5. **Manifest assembly** — every surviving entry (skeleton + binding + verification block + schema_version, plus `harm_class` where applicable) is written to the appropriate `manifest.jsonl`. The §6.4 structural constraint is enforced here: an entry pairing a harmful-pattern artifact with a code/test gate is rejected at this stage, not merely flagged. This is the canonical source of truth; raw generation artifacts are not.
6. **Coverage check** — build the concept_id × language coverage matrix (§11.2) before merging. Gaps are surfaced, not silently carried forward.

   **Cross-cell similarity audit (periodic, every 5th run):** sample N concept_ids per subtype, compute pairwise n-gram fingerprint similarity across different concept_ids within the same subtype. Flag any pair above threshold (e.g. Jaccard > 0.7) for manual review. Report diversity stats per subtype — mean/median pairwise similarity, count of near-duplicate pairs. This is an audit only; flagged pairs are not automatically rejected, but sustained high similarity in a subtype signals that the topic registry needs more diverse scenario_seeds.
7. **Merge** — apply the target-scale merge config (§9): sample paraphrase variants, apply category weights, concatenate skeleton + binding into final training records, tokenize.
8. **Train** — run on target hardware (multi consumer-GPU). Checkpoint per target_scale.
9. **Bench** — run held-out paraphrase split + held-out concept_ids never seen at any layer, plus `reframing_held_out` for `security_posture`, per §11.3.
10. **Feedback loop** — bench results identify weak `concept_id`s/categories → either (a) adjust `category_weights` and re-merge (cheap, no regeneration) or (b) flag specific manifest entries for regeneration (goes back to stage 1 or 3, scoped to just those entries).

### 11.2 Coverage matrix

A simple derived artifact, rebuilt at stage 6 of every pipeline run: rows are foundation `concept_id`s, columns are languages, cells are pass/fail/missing. This is what makes "is this a foundation bug or a Rust-only bug" answerable — if a bench failure's `concept_id` fails in every language column, the defect is in the skeleton; if it fails in only one, the defect is in that language's binding. For `security_posture` rows, the matrix can additionally be filtered by `harm_class`, independent of language, to answer "are we weak on injection-class recognition specifically."

### 11.3 Bench design

- Held-out concept_ids: a slice of the taxonomy grid (§4) reserved and never bound into any language's training manifest — pure generalization test.
- Held-out paraphrases: per §3.4, reserved renderings of *trained* concept_ids, testing whether the model learned the reasoning move or memorized the skeleton's phrasing.
- Held-out reframings (`security_posture` only): same `harm_class` as a trained concept, wrapped in a legitimacy-claiming frame. Tests whether the model was actually taught the diagnostic, or just pattern-matched the trained wording.
- Per-category scoring, not just an aggregate score — this is what the weekly re-weighting loop (§9) actually reads. For `security_posture`, this includes both the disagreement rate and the false-positive (over-refusal) rate as separate numbers.

---

## 12. Worked End-to-End Example (One Concept, All Layers)

Tracing a single `concept_id` through the full system, for concreteness:

**Concept:** `debugging_methodology:symptom_to_root_cause:expert:metacognitive:race_condition_report`

1. **Skeleton (stage 1, ENGLISH/data/debugging_methodology/symptom_to_root_cause/):** 6 paraphrased renderings generated, each with the same 4 slots (`SYMPTOM_DESCRIPTION`, `FAILURE_CLASS`, `ADJACENT_FAILURE_CLASS`, `DIAGNOSTIC_QUESTION`), abstraction level `metacognitive`, interaction format `multi_turn`. 4 go to the train pool, 2 are reserved held-out (§3.4).
2. **Rust binding (stage 3, RUST/ENGLISH/data/debugging_methodology/symptom_to_root_cause/):** slots filled with Rust-relevant content (as shown in §3.2), plus a Rust-specific continuation invoking the borrow checker.
3. **Python binding (stage 3, PYTHON/ENGLISH/data/debugging_methodology/symptom_to_root_cause/):** same `concept_id`, different slot fills — e.g. `FAILURE_CLASS: "GIL contention masking as a race"`, continuation invoking `threading` vs. `multiprocessing` semantics instead of ownership.
4. **Verification (stage 4):** this particular concept has no code artifact (it's pure dialogue, no compilable example attached) — code gate and test gate are marked `n/a` in the manifest; reasoning gate still runs (does the diagnostic question actually make sense given the symptom?).
5. **Manifest entry (stage 5):** one row in `RUST/ENGLISH/manifest.jsonl`, one row in `PYTHON/ENGLISH/manifest.jsonl`, both carrying the same `concept_id`, each with their own `binds_slots` and `verification` block.
6. **Coverage matrix (stage 6):** this `concept_id` shows `pass` in both the Rust and Python columns — full coverage.
7. **Merge (stage 7):** at 100M target scale, `debugging_methodology` has `category_weight: 1.0` — this concept_id's 4 train-pool paraphrase variants are sampled at standard frequency into both the Rust and Python merged training sets.
8. **Bench (stage 9):** the 2 held-out paraphrase variants are used to test whether the trained Rust and Python models can still perform the diagnostic move when the skeleton is worded differently than anything they trained on.

This is the pattern every foundation concept follows — the specifics (slot names, gate applicability) vary per category, but skeleton → binding → verify → manifest → merge → bench is fixed. A second worked example for `security_posture:credential_harvesting:expert:pattern_recognition:suspicious_login_prompt` follows the identical pattern, with two differences: the binding stage produces a schematic harm description plus a *separate*, gate-eligible safe-alternative artifact (§6.4), and the bench stage additionally draws on the `reframing_held_out` slice (§6.3).

---

## 13. Data Volume & Sizing Guidance (Directional, Not Final)

No hard numbers exist yet — these are starting targets to size the first generation run, meant to be corrected once real data exists (see §8, §11.3):

### 13.1 Per-concept-unit targets

- **Paraphrase variants per concept_id:** 4–8 (§3.3), with roughly 30% held out for bench (§3.4) — e.g. 6 generated → 4 train / 2 held-out.
- **Subtypes per category:** 4–7 as a starting range. Fewer than 3 subtypes in a category likely means the category is too coarse and should be merged or split. More than 10 suggests the taxonomy boundary needs re-examination — some subtypes may belong in a sibling category.
- **Interaction formats per (category, subtype):** all 7 axis-2 formats where applicable; formats that don't apply to a given subtype are documented in that category's `interaction_formats.md` (e.g. "rubber duck" may not apply to `algorithm_selection`, while "tool-call transcript" may not apply to `socratic_teaching`).
- **Difficulty levels per (category, subtype):** aim for all 4 difficulty tiers per subtype. If a subtype has no meaningful `frontier` variant, document the gap rather than generating a forced one.
- **Abstraction levels per (category, subtype):** aim for all 4 abstraction levels per subtype where the category supports them. `declarative` concepts are lower priority for the foundation layer (they're easy for small models to memorize and provide the least transfer value) — the merge config can undersample them without losing signal.

### 13.2 Per-category concept_id targets (v1 foundation layer)

Starting targets per category, sized for `foundation_roi` weight and subtype count. Categories with more subtypes or higher ROI get proportionally more concept_ids:

| Foundation ROI | Subtypes | Target concept_ids per subtype | Total per category |
|---|---|---|---|
| high | 5-7 | 16-24 | 80-168 |
| medium | 4-6 | 8-16 | 32-96 |

With 34 categories at these ranges, the total v1 foundation layer sits at roughly 2,000–5,400 concept_ids — within the "low thousands" target range. The 4 mid-cycle v4 categories (`root_cause_analysis`, `codebase_comprehension`, `technical_estimation`, `testing_strategy`) plus `se_concept_explanation`, `code_generation_from_spec`, and `quantitative_reasoning` add approximately 450–1,000 concept_ids combined at high ROI density. Categories that miss their target by more than 30% are flagged in the coverage matrix as underpopulated rather than silently carried.

### 13.3 Per-cell minimum signal threshold

A (category, subtype, format, difficulty, abstraction_level) cell with fewer than ~2 concept_ids cannot produce a stable bench score and should be flagged low-confidence in bench reports. Cells with 0 concept_ids are coverage gaps. The coverage matrix tracks this per quintuple, not just per category.

### 13.4 Scaling with model size

Category *count* grows going up the roadmap (100M → 4B) per §9's `category_weights: 0.0` → `1.0` pattern, not just per-category example density. Bigger models get more categories, not just more examples per category. The per-abstraction-level and per-difficulty ratios are also scale-dependent: larger models benefit proportionally more from `metacognitive` content (they have more capacity to internalize meta-rules), so the `metacognitive` sampling weight increases with target scale.

These numbers are placeholders — the first bench cycle should be used to sanity-check and revise this section specifically.

---

## 14. First-Train Priorities (Immediate Next Steps)

The first training run (§1.1) is **foundation-only** — no language bindings, no code, no cross-language coverage matrix. All priorities below are scoped to that first run unless otherwise noted.

### 14.1 Decisions to lock now (expensive to change after data generation begins)

1. **Manifest schema** — concept_id derivation (now including `abstraction_level`), slots, verification block shape, `harm_class` field, `category_version`, `interaction_format`, `foundation_roi`, `prerequisites`.
2. **Subtype enumeration per category** — the initial subtype list for each axis-1 category (§4). Subtypes can be added later, but the initial division defines the concept_id space; merging subtypes later would orphan existing IDs.
3. **Abstraction level axis definition** — the 4-level scale (§4 axis 4). The labels (`metacognitive`, `procedural`, `pattern_recognition`, `declarative`) and the rule that every skeleton must declare exactly one level.
4. **Per-category difficulty rubrics** — what each difficulty tier means for each category (§4 axis 3). Locked to maintain consistent bench comparisons across regeneration cycles.
5. **Format-specific skeleton schemas** — the 7 body shapes per axis-2 format (§3.2). Changing a schema shape later requires regenerating all skeletons using that format.
6. **v1 gate stack vs. logged-only vs. deferred** (§8), including the `security_posture` structural constraint (§6.4). The reasoning gate and false-positive logging apply to skeleton-only entries even without code artifacts.
7. **Merge config format** (§9) — even a single foundation-only preset needs the shape defined now, including `abstraction_level` mixing ratios, `foundation_roi` tier boosts, and `category_version` pinning.

### 14.2 Foundation-only merge config (v1 baseline)

```yaml
target_scale: 100M
scope: foundation_only
mix:
  abstraction_level_weights:
    metacognitive: 1.3
    procedural: 1.2
    pattern_recognition: 1.1
    declarative: 0.6
  foundation_roi_boost:
    high: 1.3
    medium: 1.0
    low: 0.7
  category_weights:
    requirement_disambiguation: 1.2
    guru_pushback: 1.3
    security_posture: 1.2
    debugging_methodology: 1.1
    tradeoff_analysis: 1.1
    architecture_decomposition: 1.0
    # ... remaining categories default to 1.0
  paraphrase_sampling: random_per_epoch
  category_version_pin: {}  # no pins for v1 — all versions accepted
bench_gate: foundation_bench_v1
```

### 14.3 Left intentionally loose (tuned by bench loop once real data exists)

- Slop filter thresholds
- Exact category_weights values
- Abstraction level mixing ratios
- Paraphrase variant count per concept_id
- Sizing targets in §13

### 14.4 Synthesis readiness — prerequisites to start English data generation

Before stage 1 (§11.1) can run, the following files must exist per axis-1 category. These are the "schema scaffolding" that the generation pipeline reads to produce valid skeletons:

**Required per-category files (create before generation begins):**

| File | Purpose | Example content |
|---|---|---|
| `ENGLISH/schema/<category>/subtypes.md` | Enumerated subtype list, one per line | `symptom_to_root_cause`, `binary_reduction`, ... |
| `ENGLISH/schema/<category>/difficulty.md` | Category-specific difficulty rubric | What `novice` means for this category specifically |
| `ENGLISH/schema/<category>/category.json` | Structural metadata: `foundation_roi`, `slot_count_range`, `requires_binding`, `phase_in_scale`, `valid_abstraction_levels`, `valid_formats` | See §4 priority table |
| `ENGLISH/schema/<category>/VERSION.md` | Version history, starting at `1` | Initial subtype list, slot conventions defined |

**Required global schema files:**

| File | Purpose |
|---|---|
| `ENGLISH/schema/v4.md` | Current schema version definition: all axis enums, manifest field definitions, format-specific body schemas |
| `ENGLISH/schema/skeleton_prompts/` | Directory of generation prompt templates, one per (category, interaction_format) combination — instructs the generation model what JSON shape to emit |

**Foundation-only reasoning gate criteria:**

Since the first generation run produces skeletons with no code artifacts, the reasoning gate (§6.3) evaluates:
1. **Internal consistency** — do the slot names match their usage in the conversation text?
2. **Language-agnosticism** — does the skeleton reference OS-specific paths, package managers, or platform conventions? (schema violation)
3. **Slot sufficiency** — can a reader infer what kind of content each slot expects from the skeleton alone?
4. **Reasoning quality** — does the assistant turn demonstrate the claimed reasoning move, or just describe it?

The gate logs a pass/fail per criterion and rejects entries with any violation. Category-level rejection rates are fed back to the generation prompt templates (a high rejection rate means the prompt template for that category needs adjustment).

**First generation pass order:**

1. **First smoke-test batch (5 categories):** `requirement_disambiguation`, `guru_pushback`, `debugging_methodology`, `dialogue_coherence`, `intent_recognition` — these cover the core reasoning pipeline plus the two most critical categories for basic conversational competence. Validate skeleton quality manually, adjust prompt templates.
2. **Remaining high-ROI categories:** includes `multi_turn_correction`, `instruction_following_ambiguity`, `tradeoff_analysis`, `api_design_reasoning`, `test_case_design`, `performance_reasoning`, `quantitative_reasoning`, `architecture_decomposition`, `paradigm_translation`, `security_posture`, `spec_writing`, `socratic_teaching`, `tool_use`, `research_methodology`, `se_concept_explanation`, `root_cause_analysis`, `codebase_comprehension`, `code_generation_from_spec`, `technical_estimation`, `testing_strategy`, `system_operations`, `web_data_acquisition`. Also includes `explaining_code` (medium ROI but core to chattability — generated alongside high-ROI categories, not deferred).
3. **Remaining medium-ROI categories last:** `algorithm_selection`, `code_review_critique`, `refactoring_rationale`, `error_message_interpretation`, `interface_legibility`, `documentation_generation` (phase-in at 500M).

This order ensures the generation pipeline is validated against the highest-value content before committing token budget to lower-ROI generation.

### 14.5 Topic registry — mapping taxonomy to concrete scenarios

The taxonomy (§4) defines *what kind of reasoning* but not *what subject matter*. The topic registry fills that gap: a per-category JSON file listing concrete scenario seeds for each subtype. The generation pipeline reads these seeds to produce actual skeletons with `{{SLOT}}` placeholders.

**File location:** `ENGLISH/schema/<category>/topics.jsonl`

**Format:** JSONL (JSON Lines). Each entry is one line. Two line types:

- **Metadata line** (first line): `{"type": "meta", "category": "<name>", "category_version": <int>}` — identifies the file.
- **Topic lines** (remaining lines): flat JSON objects with `type: "topic"` and `subtype` as top-level fields alongside the topic fields.

**Example:**

```jsonl
{"type":"meta","category":"debugging_methodology","category_version":1}
{"type":"topic","subtype":"symptom_to_root_cause","topic_id":"src_001","title":"intermittent_502_under_load","scenario_seed":"web server returning intermittent 502 errors under high concurrent load, no obvious error in logs","applicable_difficulties":["intermediate","expert","frontier"],"applicable_abstraction_levels":["metacognitive","procedural","pattern_recognition"],"tags":["domain:web_app","domain:networking","domain:concurrency"],"target_concept_count":6,"prerequisite_topic_ids":[]}
{"type":"topic","subtype":"symptom_to_root_cause","topic_id":"src_002","title":"memory_growth_background_worker","scenario_seed":"background worker process showing steady memory growth until OOM-killed after hours of operation","applicable_difficulties":["expert","frontier"],"applicable_abstraction_levels":["metacognitive","procedural","pattern_recognition"],"tags":["domain:memory","domain:background_jobs","domain:resource_leak"],"target_concept_count":4,"prerequisite_topic_ids":[]}
```

**Field descriptions:**

| Field | Purpose |
|---|---|
| `topic_id` | Stable identifier within this subtype, scoped to the category (e.g. `src_001` for `symptom_to_root_cause`'s first topic). Never changes once shipped; retired topics are deprecated but not removed. |
| `title` | Short machine-readable name, used in logs and coverage reports |
| `scenario_seed` | The concrete scenario description that feeds into the `concept_id` hash (as `scenario_seed`) and into the generation prompt template. Written as a short, concrete situation — not a question, not a conversation, just the scenario. |
| `applicable_difficulties` | Which difficulty tiers this topic can reasonably exercise. A topic about "variable name typo" might only work at `novice`/`intermediate`; "intermittent production deadlock" works at `expert`/`frontier`. |
| `applicable_abstraction_levels` | Which abstraction levels this topic supports. A concrete scenario can be examined metacognitively ("should I debug or redesign?"), procedurally ("step-by-step isolation"), or as pattern recognition ("does this match a known failure class?"). Not every topic supports every level. |
| `tags` | Free-form tags for filtering, sampling diversity, and coverage analysis |
| `target_concept_count` | How many concept_ids to generate for this (subtype, topic, difficulty, abstraction_level) cell. Default is inferred from §13.2 per-category targets divided across topics; override here if a specific topic needs more or fewer. |
| `prerequisite_topic_ids` | Topic IDs in the same category that should be generated first (for curriculum ordering). Empty unless the category has defined dependencies. |

**How the pipeline uses the topic registry** (§11.1 stage 1):

For each (category, subtype, topic_id, difficulty, abstraction_level) quintuple:
1. Read the `scenario_seed` from the topic registry
2. Compute `concept_id = sha256(category + ":" + subtype + ":" + difficulty + ":" + abstraction_level + ":" + scenario_seed)`
3. Render the generation prompt template with the scenario_seed to produce N paraphrase variants (per `target_concept_count`)
4. Proceed through the standard pipeline (slop filter → reasoning gate → manifest)

**Coverage checking against the topic registry** (§11.2):

The coverage matrix is extended to report per-topic_id rows, not just per-category. This answers questions like:
- "Do we have any `frontier`-difficulty skeletons about `memory_growth_background_worker`?"
- "Are we missing `metacognitive` variants for all topics in this subtype?"
- "Which topics have zero generated concept_ids?" (coverage gap, surfaced before the merge stage)

**First-pass topic creation:**

Start with 8–15 topics per high-ROI subtype, 4–8 per medium-ROI subtype. Topics should be diverse across tags and difficulty ranges. The first bench cycle reveals which topics produce weak bench scores — those get refined or replaced. Adding topics later never invalidates existing concept_ids (the `scenario_seed` is a coordinate, not a content hash; see §3.1).

### 14.6 Domain inventory — what subject matter have we actually covered?

The topic registry (§14.5) tracks what *reasoning moves* exist, but says nothing about what *subject matter* the examples exercise. Without an orthogonal domain vocabulary, it's possible to generate 200 debugging examples all about web servers and zero about filesystems — and never notice the gap.

**Location:** `ENGLISH/schema/domains.json`

**Purpose:** Seed domain vocabulary for the first generation pass. This is a *planning aid*, not a gate — during generation the model can mint new domain tags freely (see below). This file seeds the initial alias table and gives the coverage summary something to group against.

**Schema (seed entries only — not exhaustive):**

```json
{
  "domain_version": 1,
  "description": "Seed domains for first generation pass. New domains emerge organically from model-generated tags during generation (§14.6). Update this file to canonicalize new clusters, never to restrict what the model can tag.",
  "seed_domains": [
    { "domain_id": "cli_tool", "category": "app", "parent": null, "desc": "CLI tools, REPLs" },
    { "domain_id": "web_app", "category": "app", "parent": null, "desc": "Web apps, HTTP servers, browser UIs" },
    { "domain_id": "calculator", "category": "app", "parent": null, "desc": "Any form of calculator" },
    { "domain_id": "todo_app", "category": "app", "parent": null, "desc": "Task management, todo lists" },
    { "domain_id": "video_editor", "category": "app", "parent": null, "desc": "Video editing, encoding" },
    { "domain_id": "filesystem_io", "category": "tech", "parent": null, "desc": "File I/O, path handling" },
    { "domain_id": "networking", "category": "tech", "parent": null, "desc": "TCP/UDP, HTTP, DNS, sockets" },
    { "domain_id": "concurrency", "category": "tech", "parent": null, "desc": "Threads, async, locks, races" }
  ],
  "aliases": {}
}
```

**Key insight: pre-enumerating all possible domains is impossible.** There are infinitely many (calculator, todo app, video editor, e-commerce, Kubernetes operator, audio plugin, ETL pipeline, navigation system...). Instead of a fixed list checked at generation time:

**How domains enter the system:**

1. **Seed list (~20 items) for planning.** Just enough to describe what the first generation pass should cover. Not a schema — a planning aid.

2. **During generation, the model tags each concept_id with free-form domain keywords.** The generation prompt includes: *"tag this concept_id with the subject-matter domains it exercises (application areas and technical areas). Use short lowercase IDs (e.g. `calculator`, `filesystem_io`, `concurrency`)."* No validation — the model can mint any tag it wants.

3. **Post-generation aggregation.** After each generation run, aggregate all domain tags across the ledger. Cluster synonyms (`todo_app` / `task_manager` / `todo_list`) by hand or by a simple dedup step. The canonical tag for each cluster goes into an evolving `ENGLISH/schema/domain_aliases.json` so the coverage summary can normalize across synonyms.

4. **Gaps are found by reading the distribution, not by checking a list.** Run `ENGLISH/sweep/domain_summary.json` after every pipeline run — it ranks all domains by concept_id count. Any domain at 0 or very low count is a visible gap. No schema update needed to spot it.

5. **Fill gaps by adding new topics** to topic registries, tagged with the desired domain. The `tags` field uses `domain:<id>` prefix:

```json
{
  "topic_id": "src_001",
  "title": "intermittent_502_under_load",
  "tags": ["domain:web_app", "domain:api_service", "domain:networking", "domain:concurrency"]
}
```

**The seed list for the first generation pass (~20 domains to aim for):**

Application areas: `calculator`, `todo_app`, `chat_app`, `video_editor`, `e_commerce`, `cli_tool`, `web_app`, `api_service`, `background_worker`, `data_pipeline`, `devtool`, `game`

Technical areas: `filesystem_io`, `networking`, `concurrency`, `memory_management`, `authentication`, `serialization`, `database_query`, `error_handling`, `testing`, `caching`, `logging`, `performance_optimization`, `security`, `state_machine`

These are *targets* for the first pass — make sure ~half the topics in each first-pass category touch at least one of these. The model can mint additional tags freely; the seed list just prevents the first pass from producing 100 web-server examples and nothing else.

**Domain coverage summary (derived view, regenerated each pipeline run):**

| Domain ID | Total concept_ids | Categories hit | Categories missed |
|---|---|---|---|
| `calculator` | 12 | debugging_methodology, requirement_disambiguation | guru_pushback |
| `todo_app` | 0 | — | all |
| `video_editor` | 3 | debugging_methodology | all except debugging |

This summary is regenerated at each pipeline run (stage 6, §11.1). Thresholds for "low coverage" alerts are in the merge config (§14.2). No domain list changes required to see a new domain appear here.

### 14.7 Generation ledger — tracking what's actually been generated

The topic registry (§14.5) defines *intent* — what we plan to generate. The generation ledger tracks *status* per cell so we know what's been done, what passed gate, and what needs redo.

**Location:** `ENGLISH/sweep/<category>.json`

**Schema:**

```json
{
  "category": "debugging_methodology",
  "ledger_version": 2,
  "cells": [
    {
      "topic_id": "src_001",
      "subtype": "symptom_to_root_cause",
      "difficulty": "intermediate",
      "abstraction_level": "metacognitive",
      "status": "gated_pass",
      "target_count": 6,
      "generated_count": 6,
      "gated_pass": 5,
      "gated_fail": 1,
      "revision_round": 1,
      "generation_run": "v1_pass_1",
      "provider": "nvidia_nim",
      "model": "mixtral-8x22b",
      "accepted_count": 6,
      "rejected_count": 4,
      "repair_attempts": 1,
      "total_tokens": 4850,
      "cost_usd": 0.0029,
      "last_run": "2026-07-30T14:22:03Z",
      "notes": "one rejected by reasoning gate — insufficient metacognitive framing, redo in round 2"
    },
    {
      "topic_id": "src_001",
      "subtype": "symptom_to_root_cause",
      "difficulty": "intermediate",
      "abstraction_level": "procedural",
      "status": "pending",
      "target_count": 6,
      "generated_count": 0,
      "gated_pass": 0,
      "gated_fail": 0,
      "revision_round": 0,
      "last_run": null,
      "notes": ""
    }
  ]
}
```

**Status values:**

| Status | Meaning |
|---|---|
| `pending` | Not yet generated |
| `generating` | Generation in progress (lock acquired) |
| `generated` | Concept_ids produced, waiting on reasoning gate |
| `gated_pass` | All cells in this (topic, difficulty, abstraction_level) passed the reasoning gate |
| `gated_fail` | Some or all concept_ids failed the gate — needs revision |
| `revised` | Failed entries were regenerated and passed |
| `hold` | Skipped intentionally (topic doesn't fit this difficulty/abstraction combo) |

**Extended fields (added by generation runner):**

| Field | Purpose |
|---|---|
| `generation_run` | Run name from config (e.g. `v1_pass_1`) |
| `provider` | Provider that generated this cell |
| `model` | Model name used for generation |
| `accepted_count` | Variants that passed repair + validation |
| `rejected_count` | Variants that failed repair or validation |
| `repair_attempts` | Number of auto-repair iterations attempted |
| `total_tokens` | Tokens consumed for this cell |
| `cost_usd` | Estimated USD cost for this cell |
| `last_error` | Last error message (if any) |

**Domain coverage summary (derived view):**

Alongside the per-cell ledger, a derived summary aggregates domain coverage across all categories:

| Domain ID | Total concept_ids | Categories hit | Categories missed |
|---|---|---|---|
| `calculator` | 12 | debugging_methodology, requirement_disambiguation | guru_pushback |
| `todo_app` | 0 | — | all |
| `video_editor` | 3 | debugging_methodology | all except debugging |

This summary is regenerated at each pipeline run (stage 6, §11.1) and flagged if any domain has fewer than ~4 concept_ids total across the entire dataset. Thresholds are configurable in the merge config (§14.2).

**Workflow for adding new subject matter:**

1. A new benchmark reveals the model is weak at, say, `calculator`-domain reasoning
2. Search the domain coverage summary — `calculator` has 12 concept_ids, all `novice` difficulty
3. Add new topics to the topic registry tagged `domain:calculator` at `expert`/`frontier` difficulty
4. Generate → gate → re-merge → re-bench
5. The domain coverage summary shows the gap is now closed

### 14.8 Generation runner architecture

The generation runner is the first concrete tool built from this design. It reads the topic registries and sweep ledger, calls LLM APIs, validates output, and writes data files. Everything below lives in a single Python package at the repo root (e.g. `gen/`).

**14.8.1 Queue-based worker model**

The runner does not iterate categories in a hardcoded loop. Instead, a **planning step** reads the sweep ledger + topic registries and writes a `ENGLISH/sweep/queue.jsonl` — one line per generation cell. Workers consume this queue:

```jsonl
{"type":"cell","cell_id":"debugging_methodology|src_001|intermediate|procedural","category":"debugging_methodology","subtype":"symptom_to_root_cause","topic_id":"src_001","difficulty":"intermediate","abstraction_level":"procedural","target_count":6,"scenario_seed":"web server returning intermittent 502 errors under high concurrent load","format":"single_turn"}
{"type":"cell","cell_id":"debugging_methodology|src_001|intermediate|metacognitive",...}
```

Each line is self-contained — a worker can pick any available line without knowing the full queue. Locking is atomic: the worker creates `ENGLISH/sweep/locks/<cell_id>.lock` (via `mkdir` on all OSes). If the lock exists, the cell is claimed. Lock expiry: 30 minutes (configurable). Expired locks are cleaned on worker startup.

A laptop runs 2-4 async workers in a single process, each targeting a different provider or the same provider. Each worker:
1. Reads the next available queue cell
2. Acquires the lock
3. Renders the prompt template with the cell's fields
4. Calls the LLM API (with retry + backoff)
5. Repairs, sanitizes, and validates the returned text
6. Runs within-cell fingerprint dedup
7. Appends surviving variants to `data/<category>/<subtype>/<concept_id>.jsonl`
8. Updates the sweep ledger cell status
9. Releases the lock

On graceful shutdown (SIGINT/SIGTERM), the current cell is completed and the lock released. On restart, the sweep ledger shows the cell as `generated` (or `generating` with a stale lock that gets cleaned).

**14.8.2 Provider abstraction**

```python
class GenerationResult(NamedTuple):
    raw_text: str
    thinking_text: str | None    # extracted reasoning blocks
    lines: list[str]              # successfully parsed JSONL lines
    token_usage: TokenUsage
    cost_usd: float

class GeneratorProvider(ABC):
    @abstractmethod
    def generate(
        self, prompt: str, n: int,
        config: ProviderConfig
    ) -> GenerationResult: ...
```

Providers register by name in a config file. Adding a new provider = implement `generate()`, add a config block.

Provider config lives in `gen/config.json` — never hardcoded:

```json
{
  "generation_run": "v1_pass_1",
  "active_providers": ["nvidia_nim"],
  "rate_limits": {
    "nvidia_nim": { "requests_per_hour": 100, "concurrent": 2 },
    "openai":     { "tokens_per_minute": 200000, "concurrent": 4 },
    "anthropic":  { "requests_per_minute": 10, "concurrent": 1 }
  },
  "repair": { "enabled": true, "max_iterations": 3 },
  "sanitize": { "strip_emojis": true, "normalize_unicode": "NFKC" },
  "dedup": { "n_gram_size": 5, "jaccard_threshold": 0.85 }
}
```

**14.8.3 Auto-repair pipeline**

Every provider response goes through an ordered repair pipeline before any validation:

1. **Bounding box** — strip everything before the first `{` and after the last `}`
2. **Truncation recovery** — if the JSON ends mid-object, append closing braces `}` iteratively until valid
3. **Unescaped quotes** — heuristic repair of common unescaped quote patterns inside strings
4. **Trailing commas** — remove trailing commas in objects and arrays before closing brackets
5. **Thinking extraction** — strip `<think>` / `[REASONING]` / `<antThinking>` blocks and store separately
6. **Code fence removal** — strip ```json / ``` wrappers if the model returned them

After repair, attempt `json.loads()` per line. Lines that fail parsing are logged with the repair attempt count and discarded. If fewer than target_count lines survive, the shortfall is re-queued with a prompt note: "N of the M returned lines were invalid JSON; produce N replacement variants."

**14.8.4 Sanitization**

Applied after repair and before schema validation:

- Em dashes → `--`, en dashes → `-`, smart/curly quotes → ASCII straight quotes
- Emoji/emoticon stripping via Unicode category filter
- NFKC normalization
- Reject lines containing control characters (other than `\n`, `\t`)
- Strip trailing whitespace per line

Sanitization never raises — it silently fixes what it can and logs what it changed.

**14.8.5 Schema validation**

Each line must match the expected skeleton schema for its category and format:

```python
schema = {
    "type": "skeleton_variant",
    "concept_id": str,
    "category_version": int,
    "interaction_format": {"enum": ["single_turn", "multi_turn", ...]},
    "slots": dict,
    "conversation": list,
    "abstraction_level": str,
    "difficulty": str,
}
```

Missing required fields → line rejected. Wrong type for a field → line rejected. Rejected lines are logged with the specific field failure, not silently dropped. The count of rejected vs accepted is reported per cell in the sweep ledger.

**14.8.6 Streaming output**

The CLI shows a live status board:

```
[14:22:01] ◐ debugging_methodology/symptom_to_root_cause  src_001  interm/procedural  3/6  (NIM, 482 tok)
[14:22:03] ✓ debugging_methodology/symptom_to_root_cause  src_001  interm/procedural  6/6  gated
[14:22:05] ◐ debugging_methodology/symptom_to_root_cause  src_001  interm/metacog     2/6  (NIM, rate limit 30s)
[14:22:35] ◐ debugging_methodology/symptom_to_root_cause  src_001  interm/metacog     4/6  (NIM, 510 tok)
```

Active cells update in-place (carriage return). Completed cells print a permanent line. Rate limit pauses show countdown.

All output is also mirrored to `ENGLISH/sweep/run.log` with full detail (raw text, repair actions, validation failures).

**14.8.7 Data file layout**

Each concept_id gets one append-only JSONL file:

```
data/<category>/<subtype>/<concept_id>.jsonl
```

First line is metadata, subsequent lines are variant entries:

```jsonl
{"type":"meta","concept_id":"hash...","category":"debugging_methodology","subtype":"symptom_to_root_cause","category_version":1,"slot_names":["SYMPTOM_DESCRIPTION","FAILURE_CLASS","ROOT_CAUSE"]}
{"type":"variant","concept_id":"hash...","variant_index":0,"prompt_template_hash":"abc123","generation_run":"v1_pass_1","provider":"nvidia_nim","model":"mixtral-8x22b","temperature":0.7,"slots":{...},"conversation":[...],"abstraction_level":"procedural","difficulty":"intermediate"}
{"type":"variant","concept_id":"hash...","variant_index":1,...}
```

This layout is append-safe (writers append, never rewrite) and merge-ready (the merge script reads the manifest, which points to the concept_id, which maps to this file).

If a single-concept_id file exceeds 100 variants (which would mean many generation runs targeting the same cell), it is sharded: `src_001.jsonl` → `src_001_000.jsonl`, `src_001_001.jsonl`. The manifest lists the active shard.

**14.8.8 Post-generation integrity scan**

After each run (or periodically during a long run), run a lightweight verification:

1. Every cell claimed `generated` in the sweep ledger has a matching `.jsonl` file with at least target_count variants
2. Every `.jsonl` file referenced by the manifest has valid JSON on every line
3. Every concept_id in the manifest appears in at least one language's manifest (this becomes relevant later)
4. No `.jsonl` file is larger than 100MB (unlikely at this scale, but a safety check against runaway generation)

Failed checks are logged and re-queued automatically. The integrity scan takes seconds even for thousands of files.

**14.8.9 Prompt template rendering**

Templates live in `schema/skeleton_prompts/<category>_<format>.txt`. They are Jinja2 or simple `str.replace` templates:

```
Generate exactly {{target_count}} skeleton variants for the following SE scenario.

Category: {{category}}
Subtype: {{subtype}}
Difficulty: {{difficulty}} — {{difficulty_definition}}
Abstraction level: {{abstraction_level}}

Scenario: {{scenario_seed}}

Each variant must be a complete JSON object on its own line.
Required fields: type, concept_id, slots, conversation, interaction_format, difficulty, abstraction_level, category_version.

Output exactly {{target_count}} valid JSON lines.
```

Each template file includes a `# TEMPLATE_VERSION: <hash>` comment in its header. The hash is recorded in every generated variant line, so regressions can be traced to template changes. When a template is modified, its version hash changes — old data is unaffected, new data carries the new hash.

**14.8.10 Dry-run mode**

Before consuming API credits, verify the pipeline plan:

```bash
python -m gen.runner --dry-run --config gen/config.json
```

Dry-run output:
1. Reads all topic registries and sweep ledgers, enumerates every pending cell
2. Prints estimated cost break-out per category + provider using provider's cost-per-token
3. Checks that every template file referenced by the queue exists
4. Verifies all output directories exist and are writable
5. Simulates lock acquisition for the first N cells (no API calls) — confirms no deadlocks or stale lock issues
6. Exits with a summary table and total estimated cost

No files are written. No API calls are made.

**14.8.11 Journaled writes**

Python crashing mid-write must not corrupt existing data. Every `data/` write uses a journal:

1. Write new content to `data/.../<concept_id>.jsonl.tmp` (temporary file)
2. `fsync()` the temp file
3. Rename `.tmp` → `.jsonl` (atomic on NTFS/ext4/apfs)
4. If crash before rename: temp file is orphaned, original is untouched. A startup cleanup pass deletes all `.tmp` files older than 1 hour.

The sweep ledger and queue are updated similarly — write to `.tmp`, rename. This prevents partial overwrites from making half the data unreadable.

**14.8.12 Temperature / seed sweep config**

Multiple generation runs targeting the same cell must produce diverse variants. The config supports temperature sweeps:

```json
{
  "generation_run": "v1_pass_1",
  "temperature_sweep": [0.5, 0.7, 0.9],
  "seed_trials": 1,
  ...
}
```

The runner iterates temperature × provider uniformly. For each temperature, it generates `ceil(target_count / len(temperature_sweep))` variants (under-sample distribution, then the runner iterates temperature × provider uniformly. For each temperature, it generates `ceil(target_count / len(temperature_sweep))` variants, and the runner de-duplicates across all temperatures within the cell. This avoids spending API budget on near-identical outputs from two different runs.

**14.8.13 Cost forecasting**

The runner maintains a running cost ledger at `ENGLISH/sweep/cost_ledger.json`:

```json
{
  "total_spent_usd": 12.54,
  "by_provider": {
    "nvidia_nim": { "spent": 5.20, "tokens": 1040000 },
    "openai": { "spent": 7.34, "tokens": 367000 }
  },
  "by_category": {
    "debugging_methodology": { "spent": 2.10, "cells_generated": 48 },
    ...
  },
  "estimated_remaining": 48.00,
  "last_updated": "2026-07-30T14:30:00Z"
}
```

On each cell completion, the provider returns the actual token count. Cost is computed as `input_tokens * input_price + output_tokens * output_price` per provider's published rate. The remaining estimate is recalculated by comparing completed cells vs total pending cells × average cost per cell type.

The dry-run mode also prints the forecast. If actuals diverge from forecast by >20%, the runner logs a warning so the user can adjust providers or temperature settings before spending the full budget.

**14.8.14 Data shuffling and hold-out split**

After generation, each category's data must be split into train/hold-out sets before merge. This is a one-pass operation:

1. For each concept_id file, enumerate all variant lines
2. Shuffle with deterministic seed per concept_id (hash the concept_id)
3. Take the last N_variants × holdout_fraction as hold-out (default: 10%)
4. Write two directory trees: `data/<category>/.../train/` and `data/<category>/.../holdout/`
5. The manifest (§9) now references `train/` for training, `holdout/` for bench

This happens as a post-processing step (stage 1b), before the reasoning gate (stage 2). The hold-out split never sees the inside of a training epoch.

### 14.9 Slot filler — replacing `{{SLOT}}` with generic English filler

The slot filler is the bridge between skeleton generation (raw `{{SLOT}}` markers) and the foundation training merge (filled natural text). It runs as an automatic substep after generation and before the reasoning gate.

**14.9.1 Purpose**

Skeletons contain `{{SLOT}}` placeholders like `{{SYMPTOM_DESCRIPTION}}` or `{{ROOT_CAUSE}}`. The model must never train on literal template syntax. The slot filler replaces each marker with semantically-neutral English placeholder text so the foundation training sees complete, fluent sentences — even in the foundation-only pass where no language-specific bindings exist yet.

**14.9.2 Slot fill dictionary**

Location: `<LANG_ROOT>/schema/slot_fills.json` (e.g. `ENGLISH/schema/slot_fills.json`)

```json
{
  "slot_fills_version": 1,
  "description": "Generic English fillers for SLOT markers. Used during foundation-only training pass. Coding-language bindings use their own slot-fill dictionaries.",
  "entries": {
    "SYMPTOM_DESCRIPTION": [
      "the application produces intermittent failures",
      "a service becomes unresponsive periodically",
      "the system logs show transient errors",
      "a process crashes without an obvious pattern",
      "an operation succeeds sometimes and fails at other times"
    ],
    "FAILURE_CLASS": [
      "a race condition between concurrent access paths",
      "a resource leak under sustained load",
      "an unhandled edge case in the control flow",
      "a protocol mismatch between communicating components",
      "a configuration drift across deployment environments"
    ],
    "ROOT_CAUSE": [
      "improper synchronization in a shared resource",
      "insufficient isolation between independent operations",
      "a missing validation step before a state transition",
      "an assumption about ordering that is not guaranteed",
      "a capacity limit not accounted for in the design"
    ],
    "DIAGNOSTIC_QUESTION": [
      "What changed between the last working state and the first failure?",
      "Can the failure be reproduced in isolation or only under load?",
      "Does the failure pattern correlate with a specific input or condition?",
      "What is the first point in the execution where the observed state diverges from the expected state?",
      "Is the failure deterministic given the same inputs, or does it vary?"
    ],
    "ALGORITHM_NAME": [
      "a divide-and-conquer approach",
      "a hash-based lookup strategy",
      "a greedy selection heuristic",
      "a balanced tree structure",
      "a graph traversal algorithm"
    ],
    "COMPLEXITY_CLASS": [
      "linear time in the input size",
      "logarithmic time with respect to the dataset size",
      "quadratic time with respect to the number of elements",
      "exponential time in the depth of the decision tree",
      "polynomial time bounded by the product of the dimensions"
    ],
    "TRADEOFF_DESCRIPTION": [
      "a tradeoff between memory usage and execution speed",
      "a tradeoff between code simplicity and runtime performance",
      "a tradeoff between immediate solution speed and long-term maintainability",
      "a tradeoff between accuracy and computational cost",
      "a tradeoff between consistency and availability"
    ],
    "TOOL_CALL": [
      "run a diagnostic command against the running system",
      "retrieve the relevant configuration values",
      "query the monitoring system for the recent metrics",
      "inspect the state of the current execution environment",
      "fetch the latest set of known failures from the issue tracker"
    ],
    "USER_INTENT": [
      "the user wants to fix the immediate symptom without investigating the root cause",
      "the user is asking for a quick workaround rather than a proper solution",
      "the user wants a detailed explanation of the underlying mechanism",
      "the user is requesting a code review but actually needs design guidance",
      "the user is reporting a symptom that suggests a different category of problem than they believe"
    ],
    "BOUNDARY_CONDITION": [
      "when the input size exceeds the available memory",
      "when multiple clients access the resource concurrently",
      "when the system runs continuously beyond a certain duration",
      "when the input contains values near the extreme ends of the valid range",
      "when the external dependency is unavailable or slow"
    ],
    "REFACTORING_GOAL": [
      "reduce duplication between similar code paths",
      "improve the separation of concerns between layers",
      "make the control flow easier to follow",
      "align the implementation with the intended abstraction",
      "remove unused or dead code paths"
    ],
    "MATH_EXPRESSION": [
      "the sum of the first N natural numbers",
      "the probability of this event occurring at least once in N independent trials",
      "the expected number of comparisons in a randomized search",
      "the order of growth for this nested loop structure",
      "the number of distinct paths through this decision tree"
    ],
    "PROGRAM_OUTPUT": [
      "an incorrect numeric result for certain edge cases",
      "a segmentation fault when the input is empty",
      "an unexpected type error at runtime",
      "a silent data corruption that only manifests in specific conditions",
      "an off-by-one error in the boundary handling"
    ],
    "PROGRAM_INPUT": [
      "a list of records from an external data source",
      "a configuration file with parameters for the execution",
      "a stream of events generated by user interactions",
      "a set of constraints that define the valid solution space",
      "a query string with filtering and sorting parameters"
    ]
  }
}
```

**Rules for entries:**
1. Each slot name has exactly 5 filler options (enough for diversity, small enough to hand-write)
2. Filler is semantically neutral — no specific technology, framework, tool, or platform names
3. Filler reads naturally when substituted directly (grammatically compatible with surrounding text)
4. Filler is complete enough that the reasoning gate can evaluate the skeleton's quality without seeing the original slot meaning
5. New slot names discovered during generation are added manually to this file. If a generator produces a novel `{{SLOT_NAME}}` not in the dictionary, the slot filler logs a warning and uses a generic default (`"specific content for this slot"`).

**14.9.3 Filling algorithm**

```
For each skeleton variant JSON line:
  1. Scan the conversation text for {{UPPERCASE_IDENTIFIER}} patterns (regex: \{\{([A-Z][A-Z_]+)\}\})
  2. For each unique slot name found:
     a. Look up the name in the slot_fills dictionary
     b. If found, select one filler at random (uniformly from the 5 options)
     c. If not found, log WARNING: "unknown slot name {name} in {concept_id}" and use default
     d. REPLACE all occurrences of {{name}} in the conversation with the selected filler
  3. Verify no {{...}} patterns remain after substitution
  4. Write the variant with filled conversation alongside the original skeleton
     (separate field: "filled_conversation" or replace "conversation" — configurable)
```

The filler runs per-variant, not per-concept_id, so different variants of the same concept_id get different filler choices for diversity.

**14.9.4 Integration with the language-specific binding stage**

When the full pipeline runs for a coding language (Rust, Python), stage 3 replaces the generic slot filler with language-specific slot bindings. The binding stage reads the same slot names from the skeleton but fills them from a language-specific dictionary (e.g. `RUST/ENGLISH/schema/slot_fills.json`) with real code artifacts.

The foundation slot filler and the language binding stage are structurally identical — both replace `{{SLOT}}` markers with content from a dictionary. The difference is:
- Foundation filler: generic English, one dictionary shared by all categories
- Language binding: language-specific code/semantics, one dictionary per language

This is the "standard enough to work for coding languages" design: the abstraction is "replace slots with dictionary entries." The runner's pipeline dispatches to either the generic filler or a language-specific binder depending on the run config.

---

## 15. Open Items / Known Gaps (Living List)

- Differential testing against reference implementations — not in v1
- Full mutation-testing coverage — not in v1, sampled only
- Reasoning-gate LLM judge — logging only in v1, no gate threshold set yet
- Python's weaker static-verification floor (no compiler) — relies more heavily on ruff/mypy + test gate; may need a stronger test-gate weighting than Rust to compensate
- `system_operations` and `web_data_acquisition` categories are new in v4 — subtypes and concept_id counts are starting estimates; first bench cycle should validate or refine them
- §13 sizing numbers are placeholders pending first bench cycle
- Choice of generation model(s) for skeleton/binding generation not yet specified — pipeline (§11) is agnostic to this but it needs to be picked before stage 1 can run
- **Scope note on `security_posture` and RLHF:** this category is a strong replacement for a post-hoc alignment pass specifically where the harm is *taxonomizable* — malware patterns, injection classes, exfiltration shapes are enumerable axis-1/axis-3 cells, so they can be baked into pretraining, gated, and bench-scored like anything else, and the weekly re-merge loop (§9) closes a gap in days rather than an RLHF cycle's timeline. It is a weaker fit for harms that are genuinely novel or contextual/values-based rather than pattern-based, since those don't taxonomize cleanly into a grid cell ahead of time. Framed as "closes the loop for the enumerable majority," not "removes the need for RLHF" outright — first bench cycle on this category should be used to check that framing against real data.
- `security_posture`'s `harm_class` enum (schema v2) is a starting list, not exhaustive — expect to extend it once real generation surfaces categories not yet enumerated.
- **§16's stage-0 change-detection watcher (crate registries, RUSTSEC/CVE feeds) is specified in principle but not yet built** — the wipe-and-regen mechanism it feeds into already works today via the existing `concept_id`/manifest design, but nothing is watching for events yet.
- **§17's agent harness is an external, unbuilt system** — task-completion detection and model-selection logic for the harness are open questions, and explicitly out of scope for the dataset architecture itself; only `interface_legibility` (§4) is the dataset-side dependency it needs.
- **Foundation category count is now tracked per-category, not assumed fixed.** §13 now provides per-category sizing targets with ROI-tier ranges; each new category added still consumes from the v1 budget and should be weighed accordingly.

---

## 16. Freshness & Versioning Pipeline (Ongoing Maintenance, Post-v1)

The core structural advantage of staying at 100M–4B scale: retraining is measured in days, not the months/years a frontier-scale model needs. That advantage only materializes if there's an actual pipeline stage watching for staleness — it isn't automatic just because the model is small.

### 16.1 Why this only works because the models are small
This is a direct trade, not a free lunch: a 100M–4B model gave up general capability for retrain velocity. CVE-patch-within-a-week and crate-update-within-days are the payoff for that trade, not an incidental bonus. A frontier lab's model can't do this regardless of how good their pipeline is — the whole approach depends on having deliberately stayed small.

It's also a different mechanism than how SOTA models handle staleness today: most frontier labs address it via retrieval/tool-use at inference time (search the web, hit live docs), not by baking freshness into weights. The tradeoff here is the reverse — freshness lives in the weights instead of behind a tool call, which is a real advantage for offline/airgapped use or avoiding a round-trip on every syntax question, but it's not that SOTA has no answer to staleness, just a different one.

### 16.2 New pipeline stage 0: change detection
Ahead of skeleton generation (§11.1 stage 1), a watcher stage is needed: something monitoring crate registries (crates.io, RUSTSEC advisories, PyPI, CVE feeds) and mapping a detected event ("crate X published breaking version Y," "RUSTSEC-2026-NNNN filed") to the specific `ecosystem_interactions.<package>` or `ecosystem_deep_dives` manifest rows referencing the affected package. Without this stage, "remove the old, insert the new" still requires manually noticing what broke.

### 16.3 The wipe-and-regen operation
Because `concept_id` is a coordinate hash, not a content hash (§3.1), regenerating language-specific content never orphans anything — the mechanism that makes "patch this one crate's examples" a targeted regen instead of a full corpus rebuild already exists, it just needs the `package_ref` field (§9) to be queryable by the watcher in §16.2. Worked example: **egui/eframe ships a breaking change** → watcher flags it → query manifest for `package_ref.name in {"egui", "eframe"}` → wipe those rows → re-run stages 3–7 (§11.1) scoped to just that package → re-merge → retrain.

**Hard boundary to protect:** the wipe operation must only ever touch the *leaf binding* (the language-specific `ecosystem_interactions` entry), never the foundation skeleton it happened to be generated from, if any. A routine crate-version bump should never be able to delete a piece of general reasoning (e.g. a `refactoring_rationale` skeleton) just because one of its language bindings used the now-outdated crate as its illustration — the fix there is regenerating that binding's example, not touching the skeleton.

### 16.4 CVE-specific note
A security advisory should be treated as a higher-priority version of the same event — same detection → query → wipe → regen → retrain loop as §16.3, just with tighter turnaround expectations (within the week, not whenever the next scheduled pass happens) and probably its own priority queue ahead of ordinary version-bump events.

---

## 17. Agent Harness (External Consumer of These Models — Not Part of the Dataset Architecture)

This section describes a *use case* that motivates one dataset decision (`interface_legibility`, §4/§9) but is itself a separate system, built on top of the trained models rather than inside this pipeline.

### 17.1 The idea
On modest hardware, a lightweight harness (not a model, not an orchestration model — closer to a task-management script) can load a small standalone model for one part of a job, let it finish, then unload it and load a different small standalone model for the next part. Example: load the HTML/CSS model, let it build a page, then swap to the JS model to wire up interactivity against what was already built. This is a genuinely different way to make capable-feeling AI accessible on hardware that can't hold a large generalist model in memory at once — trade one big model for a sequence of small ones, paying a load/unload cost instead of a VRAM cost.

### 17.2 Why this doesn't violate the standalone requirement (§5)
§5 says each model has no runtime dependency on *another model*. The harness doesn't change that — each specialist still never needs to know another model exists; it just receives a prompt that happens to include "here's what's already been built." The harness is the new thing, sitting *above* the standalone models, not a change to how any individual model works or is trained.

### 17.3 Handoff format: raw artifacts, not a summary
Two designs were considered:
- **Summary-only handoff** (harness writes a natural-language description of what the prior model did) — cheap, but pushes handoff quality entirely onto how good that summary is, and "write a good structured handoff summary" would itself need to become a trained skill (a `context_summarization_for_handoff` category) for the *producing* model.
- **Raw-artifact handoff** (harness passes the actual generated files alongside a short human-readable log) — the receiving model just sees it as ordinary context in its prompt, no special training required on either side, and nothing is lost to a lossy paraphrase step.

**Raw-artifact handoff is the better default**, especially for the accessible/low-end-hardware goal: it's close to free (just more text in a prompt) and doesn't ask the harness to compress anything. The short summary can still exist as a human-readable log of what happened, but the actual next-model context should be the real files.

### 17.4 Where `interface_legibility` fits in
Raw-artifact handoff works better the more legible the artifacts already are — meaningful element IDs and class names instead of `div1`/`div2`, comments marking intentional hook points, naming a downstream reader can infer intent from without being told. That's exactly `interface_legibility`'s producer posture (§4), trained into each model directly rather than enforced by the harness. The harness doesn't need to demand a particular structure or reformat anything; a model trained with decent producer posture leaves behind artifacts that are already reasonably legible to whatever picks them up next, human or model, harness-orchestrated or not.

### 17.5 Open questions for a real build (harness side, separate from the dataset work)
- Task-completion detection: how the harness decides a given specialist is "done enough" to hand off, vs. needs another turn.
- Model selection: how the harness picks which specialist to load next (fixed pipeline per task type, vs. some lighter routing decision).
- This is genuinely a separate, smaller build once the underlying models exist — none of it requires changes to the dataset architecture beyond the `interface_legibility` category already covered above.

---

## 18. Crowdsourced Contribution Pipeline (Alternative to Solo Generation)

The token/compute budget in §13/§14 assumes one operator generating everything. An alternative: a lightweight website that lets contributors generate data using their own AI accounts (free-tier or otherwise), with the site handling seeding, schema, and validation so contributors never need to understand the taxonomy directly.

### 18.1 Workflow

1. Contributor picks a category + language on the site (e.g. "Rust — debugging_methodology").
2. Backend generates a uniquely-seeded prompt: a specific `(task_type, subtype, difficulty, abstraction_level, scenario_seed)` coordinate, rendered into a natural-language generation prompt, with the exact target JSONL schema (slots, `concept_id` derivation, verification block shape) embedded so the model being prompted knows exactly what shape to return.
3. Contributor copies that prompt into whatever AI tool they're using, pastes the result back into the site.
4. Backend runs the full gate stack (§6) automatically: schema validation, code gate, test gate, reasoning gate, slop filter (§7). Pass → written to manifest with `schema_version` and contributor attribution; fail → rejection reason surfaced back to the contributor so they can regenerate and resubmit.
5. Coverage matrix (§11.2) updates live, so the site can show which cells are still thin and steer contributors toward high-need categories rather than oversaturating a few popular ones.

### 18.2 What this changes in the schema

- **`contributor_id` field on manifest entries** — not for policing, just for the same reason `schema_version` exists: if a category's bench score looks off later, being able to trace it back to *which* generation pass produced it (a person, a prompt version, a schema version) is what makes the entry patchable instead of a mystery.
- **Held-out routing happens server-side, invisibly.** Since the site is the one generating the seed, it can route a chosen fraction of requests straight into the held-out pool (§3.4) or the `reframing_held_out` slice (§6.3 for `security_posture`) without the contributor needing to know or do anything differently — the paste-back flow looks identical either way.
- **Seed uniqueness needs tuning, not just randomness.** The seed has to be specific enough to pin down a stable `concept_id`, but varied enough across contributors that ten people filling the same cell don't return near-duplicate paraphrases — this is really just a server-side version of the existing paraphrase-variant generation (§3.3), moved from "one operator prompting N times" to "N contributors each prompting once."

### 18.3 Categories best suited to this flow

Most of the taxonomy (§4) works well as fully open contribution — `requirement_disambiguation`, `guru_pushback`, `debugging_methodology`, and the rest are self-contained generation tasks with clear pass/fail gates, so quality control lives entirely in the automated gate stack rather than in who's contributing.

`security_posture` is the one category worth routing through a smaller, invite-only contributor tier rather than the fully open flow — not because the gates (§6.4) can't catch a bad artifact, but because this is the category where getting the shape of the prompt itself right (schematic harm description, never a compilable payload) benefits from contributors who already understand that constraint going in, rather than learning it from a rejection message.

### 18.4 Open questions for a real build

- Whether contributors generate via their own API key (site just formats prompt/schema) or the site proxies the call itself (site owns cost, contributor just supplies effort) — changes the cost model but not the pipeline.
- How aggressively to steer contribution toward thin coverage (§11.2) vs. letting people self-select categories they find interesting — probably some blend, shown as a simple "most-needed right now" sort on the category picker.
- Whether paraphrase-variant count per concept_id (§13) should be a fixed target per cell that closes off once hit, so effort naturally redistributes across the grid instead of concentrating.

---

## 19. Glossary

- **Concept_id** — stable identifier for one taxonomy grid cell, derived from category coordinates `(task_type, subtype, difficulty, abstraction_level, scenario_seed)`, not from content. See §3.1.
- **Subtype** — a per-category enumerated value identifying a specific sub-skill within an axis-1 category (e.g. `symptom_to_root_cause` under `debugging_methodology`). Defined in `schema/<category>/subtypes.md`. See §4.
- **Abstraction level** — the 4th taxonomy axis (§4) identifying what kind of cognitive content a skeleton represents: `metacognitive`, `procedural`, `pattern_recognition`, or `declarative`. Independent of difficulty.
- **Difficulty rubric** — a per-category definition of what each difficulty tier (`novice`, `intermediate`, `expert`, `frontier`) means for that specific category's skill domain. See §4 axis 3.
- **Interaction format** — the axis-2 format of a skeleton, determining its `body` schema structure. One of: `single_turn`, `multi_turn`, `lecture`, `code_review`, `rubber_duck`, `adversarial`, `tool_call`. See §3.2.
- **Foundation_roi** — structural metadata on each axis-1 category estimating its return on investment within the foundation layer (`high`, `medium`, `low`). Used by merge configs to boost or filter categories independently of weights. See §4.
- **Category_version** — an integer, per-category version counter independent of the global `schema_version`. Bumped when a category's subtype enumeration, slot conventions, or difficulty rubric changes. Pinned by merge configs via `category_version_pin`. See §3.5.3.
- **Skeleton** — the language-agnostic English template for a concept, containing `{{SLOT}}` placeholders. Carries `category_version`, `abstraction_level`, `interaction_format`, `foundation_roi`, `prerequisites`, and a format-specific `body`. Lives in `ENGLISH/`.
- **Slot** — a placeholder in a skeleton that requires language-specific knowledge to fill.
- **Binding** — a language's filled-in version of a skeleton's slots, plus any language-specific continuation. Lives in `RUST/ENGLISH/` or `PYTHON/ENGLISH/`.
- **Bind (verb)** — the act of linking a binding to its skeleton via shared `concept_id`.
- **Gate** — an automated pass/fail (or logged) check applied to a generated entry before it's allowed into the manifest. See §6.
- **Manifest** — the canonical `jsonl` record of every entry, its concept_id, bindings, and verification results. Source of truth, not the raw generation output.
- **Merge config** — a per-target-scale recipe (weights, category inclusion, abstraction-level ratios, category version pins) that determines how manifest entries are sampled and concatenated into final training records.
- **Coverage matrix** — derived table of concept_id × language × category_version → pass/fail/missing, used to distinguish foundation-layer bugs from language-layer bugs, and to identify gaps per subtype or abstraction level.
- **Held-out split** — paraphrase variants or entire concept_ids deliberately excluded from training, reserved for bench.
- **Held-out reframing split** — (schema v2, `security_posture` only) reserved variants that wrap a trained harm class in a legitimacy-claiming frame, testing robustness to reframing rather than surface wording.
- **Harm class** — (schema v2 manifest field) the enumerated category of harm a `security_posture` request maps to (e.g. `credential_harvesting`, `injection`, `sandbox_evasion`). See §3.5.1.
- **False-positive flag** — (schema v2) a logged reasoning-gate signal for `security_posture` entries where the assistant turn over-refused a legitimate-adjacent-use request.
- **Axis (1/2/3/4)** — the four independent dimensions (cognitive task type, interaction format, difficulty, abstraction level) that together define one taxonomy grid cell. See §4.
- **Target_scale** — the parameter-count tier (100M / 500M / 1B / 2B / 4B) a given merge config is built for.
- **Schema_version** — a global version tag on the taxonomy/manifest definitions in `ENGLISH/schema/`. Bumped when the taxonomy changes; existing concept_ids and their data are never retroactively altered when it bumps. See §3.5.
- **Slop** — low-signal filler content (hedging, restating the question, generic praise, redundant caveats) that consumes training tokens without teaching reasoning. See §7.
- **MSRV** — Minimum Supported Rust Version; the oldest Rust compiler version a piece of code is guaranteed to build under.
- **GIL** — Global Interpreter Lock; CPython's mechanism restricting execution of Python bytecode to one thread at a time, relevant to concurrency-related debugging content.
- **Borrow checker** — the Rust compiler's static analysis enforcing ownership/borrowing/lifetime rules at compile time, ruling out whole classes of memory and data-race bugs before a program runs.
- **Interface legibility** — (v3 axis-1 category, §4) a thin foundation-layer category teaching producer posture (leave an artifact legible to an unknown consumer) and consumer posture (correctly infer intent/contract from an artifact you didn't write), kept generic on purpose so specific pairings live in `ecosystem_interactions` instead.
- **Ecosystem interactions** — (v3, §9) a language-specific-only category bucket, one sub-category per external package/tool a language commonly interacts with (e.g. `ecosystem_interactions.mysql`), analogous to `ecosystem_deep_dives` — no `concept_id`, no cross-language binding.
- **Package_ref** — (v3 manifest field, used on `ecosystem_interactions`/`ecosystem_deep_dives` entries) `{name, version_range}` identifying which external package/version an entry is bound to, so version-bump or CVE events can be resolved to affected manifest rows by query rather than by folder-guessing. See §16.
- **Agent harness** — (v3, §17) an external system, not part of this dataset architecture, that loads/unloads separate standalone models in sequence to complete a multi-language task (e.g. HTML/CSS model → JS model), passing raw generated artifacts between them.
- **Foundation-first training** — the initial training run using only the English foundation layer, with no language-specific bindings or code artifacts. Validates the skeleton taxonomy independently before any language work begins. See §1.1.

---#   L L M  
 