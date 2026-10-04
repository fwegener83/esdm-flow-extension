# ESDM Flow Extension — Specification v0 (draft)

> **Status:** Draft for discussion. Nothing here is stable. Rule IDs, field
> names and the `apiVersion` may change without notice until v1.
>
> **Normative language:** MUST, MUST NOT, SHOULD and MAY are used as in
> RFC 2119.

---

## 1. Motivation

[ESDM](https://www.esdm.io/) describes an event-sourced domain model in two
layers:

- the **core**: the static structure, such as bounded contexts, aggregates,
  commands, events, read models and policies, together with their references;
- **Given-When-Then features**: behavioral examples, each about exactly **one**
  consistency unit.

What ESDM does not have is the **story across units**. ESDM cannot say that a
customer places an order, a policy then creates an invoice in another bounded
context, the customer looks at their orders, and a clerk ships one of them.
Event Modeling puts exactly this narrative at its center. There the narrative
lives on a whiteboard, and whether it holds together, meaning whether every
piece of information shown at the end actually entered the system somewhere
earlier, is checked by eye.

This extension adds the story as a **document type that references the core**,
and makes it machine-checkable on two levels:

1. **Narrative conformance** (Part A): the story is told with the core's own
   vocabulary, and every step in it is structurally possible according to the
   core model.
2. **Provenance** (Part B): every value shown in the story can be traced back
   along the story to a declared point where it entered the system. Nothing is
   invented out of thin air.

## 2. Terminology

| Term | Meaning |
|---|---|
| **Flow** | A document that tells one story as an ordered list of slices. |
| **Slice** | One step of the story: one cause and its effect, centered on exactly one consistency unit. |
| **Artifact** | An ESDM core artifact, such as a command, an event or a read model. It declares fields, but holds no values. |
| **Occurrence** | An artifact as it appears in one slice, **with concrete values**. |
| **Instance** | The identity of one concrete aggregate, for example order `o-1`, as opposed to the aggregate artifact `order`. |
| **Persona** | An optional name for one concrete actor, for example `alice`, as opposed to the actor artifact `customer`. |
| **Given** | Facts assumed to have happened before the story starts. |
| **Entry point** | A declared place where new information legitimately enters the system. |
| **Provenance** | The source of a value: an entry point, or a value visible earlier in the story. |
| **Visible set** | The values an occurrence may legitimately take its own values from. |

### 2.1 Artifact vs. occurrence

The difference between an artifact and an occurrence is the difference between a
class and an object:

| | ESDM core (artifact) | Flow (occurrence) |
|---|---|---|
| Example | event `placed` with fields `orderId: string`, `total: number` | one `placed` with `orderId: "o-1"`, `total: 25` |
| Holds | field declarations (JSON Schema) | values that MUST conform to those declarations |
| Identity | the artifact's name | the slice it occurs in, and for aggregates also the instance |

The same artifact typically occurs many times in one flow, for example two
`placed` events for two different orders. What happens later in the story
depends on *which* occurrence a value came from. Part B is built on this
distinction.

## 3. Relationship to ESDM

### 3.1 References only

A flow **references** core artifacts by name. It never declares, extends or
implies them. A flow that mentions a command the core does not contain is
invalid. It does not create that command. The core model stays the single
source of truth.

### 3.2 Layered validity

A flow is valid if and only if:

1. the flow document is valid against `schema/flow/v0.yaml`, **and**
2. the core model it refers to lints without errors (`esdm lint`), **and**
3. the flow rules of Part A (and of Part B, at conformance level 2) hold,
   evaluated against that core model.

If (2) fails, a flow linter MUST report `flow/model/core-model-invalid` and
SHOULD NOT evaluate further rules. Flow findings against a broken model are
noise.

### 3.3 Relationship to Given-When-Then

Flows do not replace GWT features. They sit one level above them. A GWT scenario
tests one consistency unit in isolation. A flow adds **order** and **stitches
units together at their events**. Every slice of a flow corresponds to a GWT
scenario (see §8). The data shapes are deliberately the same: `command` and
`data` in `when`, `event` and `data` in `then.events`, `rejection.invariant`,
`query` and `parameters`, `result`.

### 3.4 File convention and identity

- `apiVersion`: `github.com/fwegener83/esdm-flow-extension/flow/v0`. This
  follows the core schema's convention for third-party extensions, where
  `$id = "https://" + apiVersion`.
- `kind`: `flow`.
- File suffix: **`.flow.yaml`**, not `.esdm.yaml`.

The suffix differs on purpose. According to its documentation, ESDM extensions
are maintained by the ESDM team and are not user-extensible. `esdm lint` reports
every document with an unknown `apiVersion` in a `.esdm.yaml` file as an error.
With a separate suffix, flows can live next to a core model without breaking
`esdm lint`. If the extension is ever adopted upstream, the suffix becomes
`.esdm.yaml` and the `apiVersion` moves under `schema.esdm.io`.

## 4. Document format

### 4.1 Overview

```yaml
apiVersion: github.com/fwegener83/esdm-flow-extension/flow/v0
kind: flow
name: two-orders                 # kebab-case, like every ESDM name
description: Two customers order; one order is shipped, the other canceled.
scope:
  domain: shop
given: [ ... ]                   # optional: facts before the story (§4.6)
slices: [ ... ]                  # at least one, in narrative order
```

The order of `slices` **is** the order of the story. There is no separate
`order` field.

### 4.2 Command slice

A command slice shows one command against one aggregate instance and its
outcome.

```yaml
- name: alice-places-order       # unique within the flow
  type: command
  trigger:                       # optional, at most one trigger
    actor: customer              # bare name, resolved in the aggregate's bounded context
    persona: alice               # optional
  aggregate:
    boundedContext: ordering
    aggregate: order
    instance: o-1                # identity of this order
    provenance: generated        # the instance is created here (§7.7)
  when:
    command: place               # bare name; MUST belong to the aggregate above
    data: { customerId: c-alice, product: book, quantity: 2, unitPrice: 12.5 }
    provenance:
      customerId: input
      product: input
      quantity: input
      unitPrice: input
  then:
    events:                      # either `events` …
      - event: placed            # bare name; MUST be in the command's `publishes`
        data: { orderId: o-1, customerId: c-alice, product: book, quantity: 2, total: 25 }
        provenance:
          total:
            derived:
              from:
                - { command: place, field: quantity }
                - { command: place, field: unitPrice }
              rule: quantity × unitPrice
    # rejection:                 # … or a rejection
    #   invariant: shipped-orders-cannot-be-canceled
```

**Cardinalities.** These are enforced by the schema, because every role is a
single field and not a list:

| Role | min | max |
|---|---|---|
| trigger | 0 | 1 |
| aggregate (the consistency unit) | 1 | 1 |
| command | 1 | 1 |
| outcome | 1 | 1, either `events` (1..n) or `rejection` |

A second command is a second slice, even if it is the same command artifact. The
same command can occur in many slices. Within one slice, each event artifact
occurs at most once (see open question Q1).

### 4.3 Read-model slice

A read-model slice shows what a read model contains at this point in the story,
optionally through a query.

```yaml
- name: bob-views-orders
  type: read-model
  trigger: { actor: customer, persona: bob }   # optional; only `actor` is allowed
  readModel:
    boundedContext: ordering
    readModel: my-orders
  when:                          # optional; present ⇔ `then.result`
    query: get-my-orders         # bare name; MUST serve the read model above
    parameters: { customerId: c-bob }
    provenance: { customerId: input }
  then:
    result:                      # either `result` (requires `when`) …
      - { orderId: o-2, total: 40, status: placed }
    # readModel: [ ... ]         # … or the read model's content, without a query
    provenance:
      0.status:
        derived:
          from: [ { slice: bob-places-order, event: placed } ]
          rule: A row is `placed` after `placed` and before `shipped` or `canceled`.
```

Events are **never** listed in a read-model slice. Which earlier events feed the
read model follows from the core's `projections` together with the story (§6.3,
§7.3).

### 4.4 Triggers

| Form | Allowed in | Meaning |
|---|---|---|
| `{ actor: <name>, persona?: <string> }` | command and read-model slices | A person or system acts. The actor is resolved in the bounded context of the slice's consistency unit. |
| `{ policy: <name>, reactsTo: { slice: <name>, event: <name> } }` | command slices | A policy reacts to one concrete earlier event occurrence. |
| *(absent)* | both | The cause is not part of the story. |

`persona` names one concrete actor. Two slices with the same actor and different
personas are told from the perspective of two different people. This matters for
visibility (§7.3): Alice cannot use what only Bob has seen.

### 4.5 Aggregate instances

`aggregate.instance` names the concrete instance the command acts on. It is a
string compared by value.

- If the core aggregate has `identifiedBy.source: static`, `instance` MAY be
  omitted. If present, it MUST equal `identifiedBy.value`.
- Otherwise `instance` is REQUIRED (`flow/model/instance-missing`).

Two slices act on the same instance if and only if they name the same bounded
context, aggregate and instance value.

### 4.6 Given

A story often starts in the middle of a domain's life: the order already exists
when the story begins. `given` lists such earlier facts as events:

```yaml
given:
  - name: order-exists           # shares the namespace of slice names
    boundedContext: ordering
    aggregate: order
    instance: o-9
    event: placed
    data: { orderId: o-9, customerId: c-carol, product: desk, quantity: 1, total: 300 }
```

A given entry behaves like a slice that comes before every real slice and
contains exactly this one event. Its values are **axioms**: they are not traced
any further (Part B). Like every value, they MUST conform to the core schema,
and they take part in visibility and freshness. For an aggregate that is not
static, `instance` is REQUIRED (`flow/model/instance-missing`).

### 4.7 Provenance annotations

Every occurrence that carries values (`when.data`, `then.events[].data`,
`when.parameters`, `then.result`, `then.readModel`, `given[].data`) MAY carry a
sibling `provenance` map. Keys are **field paths**, values are **sources**. The
aggregate's `instance` has a single `provenance` value instead of a map.

**Field paths** are dot-separated. Numeric segments index into arrays:
`customerId`, `0.status`, `items.2.sku`. The **key** of a path is its last
non-numeric segment (`0.status` → `status`, `items.2` → `items`).

**Sources:**

| Source | Meaning |
|---|---|
| `input` | The triggering actor provides this value (§7.2). |
| `generated` | The system creates a new, unique value, such as an ID. |
| `clock` | The current time. |
| `constant` | A fixed value that the business logic decides on, such as a status literal or a configured limit. |
| `{ from: <ref> }` | Taken unchanged from exactly this earlier value. |
| `{ derived: { from: [<ref>, …], rule: <string> } }` | Computed from these values. The rule is prose and is not evaluated. |

Fields without an annotation are traced **implicitly** (§7.4). Annotations are
needed only where implicit tracing cannot work: entry points, renames and
derivations.

**References** (`<ref>`) point at one occurrence, and optionally at one field in
it:

```yaml
{ slice: <name>, event: <name>, field: <path> }    # an event in a slice or given entry
{ slice: <name>, command: <name>, field: <path> }  # the command of a slice
{ slice: <name>, query: <name>, field: <path> }    # the result of a query
{ slice: <name>, readModel: <name>, field: <path> }  # the read-model content of a slice
```

`slice` defaults to the current slice. `field` is REQUIRED in `from` and
OPTIONAL in `derived`. A `derived` reference without `field` means "the fact
that this occurrence happened", as in a status derived from which event
occurred.

## 5. Validation model

### 5.1 Conformance levels

| Level | Checks | Meaning |
|---|---|---|
| **L1: narrative** | schema, Part A | The story is told correctly and is structurally possible. |
| **L2: provenance** | L1 + Part B | The story is also *coherent*: no value comes from nowhere. |

A tool claiming support for this extension MUST implement L1 and SHOULD
implement L2. Part B is evaluated **only if Part A reports no errors**.
Provenance through a broken reference has no meaning, and follow-up findings
would hide the actual cause. A flow SHOULD state which level it aims for; the default is L2.
L2 requires annotations (entry points, renames, derivations). L1 lets teams
start without them.

### 5.2 Findings

Findings follow the shape of `esdm lint`: rule ID, severity (`error` or
`warning`), message and location. Rule IDs have the form
`flow/<category>/<name>`, with the categories `structure` (document-internal),
`model` (against the core model) and `provenance` (Part B).

## 6. Part A — Narrative rules

### 6.1 Structure (document-internal)

| Rule | Severity | Description |
|---|---|---|
| `flow/structure/schema-violation` | error | The document does not validate against `schema/flow/v0.yaml`. |
| `flow/structure/duplicate-slice-name` | error | Two slices or given entries share a name. |
| `flow/structure/duplicate-event-in-slice` | error | The same event artifact appears twice in one slice's `then.events`. |
| `flow/structure/unknown-slice-reference` | error | A `trigger.reactsTo.slice` or a reference `slice` names no slice or given entry. |
| `flow/structure/unknown-occurrence-reference` | error | A reference names an event, command, query or read model that does not occur in the referenced slice. |
| `flow/structure/unknown-field-reference` | error | A reference's `field`, or a `provenance` key, names a path that does not exist in the referenced or annotated data. |
| `flow/structure/reference-not-earlier` | error | A reference or `trigger.reactsTo` points at the current slice or a later one. Exception: inside a command slice, event provenance MAY reference the same slice's command. |

### 6.2 Model (against the core model)

| Rule | Severity | Description |
|---|---|---|
| `flow/model/core-model-invalid` | error | The core model has `esdm lint` errors (§3.2). |
| `flow/model/domain-mismatch` | error | `scope.domain` is not the domain of the core model. |
| `flow/model/unresolved-reference` | error | A referenced bounded context, aggregate, command, event, actor, policy, read model or query does not exist in the core model. |
| `flow/model/command-not-of-aggregate` | error | `when.command` is not scoped to the slice's aggregate. |
| `flow/model/event-not-published-by-command` | error | An event in `then.events` is not in the command's `publishes`. |
| `flow/model/unknown-invariant` | error | `then.rejection.invariant` is not an invariant of the slice's aggregate. |
| `flow/model/actor-not-permitted` | error | The command or query declares `actors`, and the trigger actor is not among them. |
| `flow/model/policy-does-not-handle-event` | error | The event that `trigger.reactsTo` points at is not in the policy's `handles`. |
| `flow/model/policy-does-not-emit-command` | error | The slice's command is not in the policy's `emits`. |
| `flow/model/query-not-on-read-model` | error | `when.query` does not serve the slice's read model. |
| `flow/model/instance-missing` | error | `instance` is absent although the aggregate is not `static`, or present and different from a `static` value. |
| `flow/model/data-schema-violation` | error | Values do not conform to the core schema of their artifact: `command.data`, `event.data`, `query.parameters`, `query.result`, `read-model.schema`. |
| `flow/model/read-model-without-projected-event` | warning | No event that the read model projects from occurs before this read-model slice, so the view cannot contain anything from this story. |

### 6.3 Notes

- **Causality.** Policies react only to events that have already happened in
  the story (`reference-not-earlier`). A read model shows only what was
  projected from earlier events (`read-model-without-projected-event`, and in
  Part B the visible set of §7.3).
- **No hidden truth.** A read-model slice never lists events. The connection
  between an event and a read model is a fact of the core model
  (`projections`) together with the order of the story. The author does not
  decide it.

## 7. Part B — Provenance

### 7.1 Principle

> **New information may only enter at declared entry points. Every other value
> MUST be traceable backwards through the story to an entry point or to a given.**

Provenance works on **values along fields**. A value counts as traced only if it
reaches the target through a field relationship: by the same key, by an
explicit `from`, or as an input of a `derived`. It is not enough for the value
to have occurred "somewhere" earlier. Otherwise `quantity: 2` would always be
traced by any earlier `2`.

### 7.2 Entry points

| Entry point | Allowed in | Not allowed in |
|---|---|---|
| `input` | `when.data` of command slices triggered by an actor or without a trigger; `when.parameters` | events, read models, results, instances; commands triggered by a policy |
| `generated` | `when.data`, event data, `aggregate.provenance` | parameters, results, read models |
| `clock` | `when.data`, event data, `when.parameters` | results, read models |
| `constant` | everywhere | — |

The reasoning behind the table:

- Only actors type things in. Events record what happened. They cannot receive
  input that the command did not carry.
- Read models only reflect events. They cannot generate or time-stamp anything
  of their own.

`flow/provenance/entry-point-not-allowed` reports violations.

### 7.3 Visible sets

The visible set `V(o)` of an occurrence `o` in slice `s` is what `o`'s values may
be taken from. "Earlier" means given entries and slices that come before `s`.

| Target `o` | `V(o)` |
|---|---|
| `when.data` of a command slice, trigger **actor** | the results and read-model content of earlier read-model slices with the **same actor**, and also the **same persona** if `s` has one |
| `when.data` of a command slice, trigger **policy** | the data of the event occurrence named by `trigger.reactsTo` |
| `when.data` of a command slice, **no trigger** | the results and read-model content of all earlier read-model slices |
| `then.events[].data` | the `when.data` of `s`; the instance value of `s`; the **instance state**, meaning the data of all earlier event occurrences (including givens) on the **same instance** |
| `when.parameters` | as for `when.data` with the same trigger |
| `then.result` / `then.readModel` | the data of all earlier event occurrences (including givens) whose artifact is in the read model's `projections`; the `when.parameters` of `s` |

The instance state is what makes the two-orders story checkable. When order
`o-2` is shipped, `customerId` in `shipped` must come from an earlier event *of
`o-2`*. Bob's customer ID is fine. Alice's is not.

### 7.4 Implicit tracing

A value without an annotation at path `p` with key `k` is **traced** if `V(o)`
contains a value with the same key `k` that is deeply equal to it. The
aggregate's instance value is a candidate whose key matches any key, so
`orderId: o-1` in an event on instance `o-1` is traced.

Tracing goes top-down. If an object or array is traced as a whole, everything
inside it is traced. Otherwise each child is checked separately. In the end,
every scalar leaf must be traced. `null` values are ignored, because absent
information is not information.

### 7.5 Explicit sources

`{ from: <ref> }` is needed when a value changes its name along the way (for
example `total` in ordering becomes `amount` in billing). The reference MUST
point into `V(o)` (`flow/provenance/source-not-visible`), and the referenced
value MUST be deeply equal to the annotated value
(`flow/provenance/source-value-mismatch`).

`{ derived: … }` lists the inputs of a computation. Every input MUST point into
`V(o)` or at a sibling field of the same occurrence. The computation itself is
prose and is not checked. A derived value can be wrong, but it cannot come from
nowhere.

### 7.6 Givens

Given values are axioms and are not traced. They are the story's honest way of
saying "this was already the case". A story with many givens tells less, but
it does not lie.

### 7.7 Identity and freshness

- **Generated values are fresh.** A value marked `generated` MUST NOT appear
  anywhere earlier in the story: not in any occurrence, given or instance
  (`flow/provenance/generated-value-not-fresh`). An order that is "created"
  twice as `o-1` is a finding.
- **Instances are created or addressed.** In every command slice whose
  aggregate is not `static`, the instance MUST be either
  - marked `provenance: generated`, meaning the slice creates it, which is only
    allowed if the aggregate has `identifiedBy.source: generated`; or
  - present as a value in the slice's `when.data`, meaning the command says
    which instance it means. That value is traced like any other.

  Neither: `flow/provenance/instance-not-addressed`. A `generated` mark on an
  aggregate that is not `generated`: `flow/provenance/entry-point-not-allowed`.
  A `generated` mark on an instance that already appeared earlier is a
  freshness violation (see above). Creating the same order twice is therefore
  reported exactly once, as `generated-value-not-fresh`.

  A command against an instance that never appeared before is not an error in
  itself, for example when an actor types in an unknown order number. It
  usually shows up as soon as an event needs that instance's state.

### 7.8 Reporting backwards

A linter SHOULD explain each finding as a backwards chain from the value to
where the trail breaks:

```text
error flow/provenance/unsourced-value
  at slice clerk-ships-order-2 › then.events[shipped].data.customerId = "c-alice"
  ✗ not in when.data of clerk-ships-order-2
  ✗ not in the instance state of ordering/order o-2
      (known: orderId=o-2, customerId=c-bob, product=lamp, quantity=1, total=40)
  hint: "c-alice" is customerId of instance o-1 — did you ship the wrong order?
```

On request (for example `--explain <slice>.<path>`), a linter SHOULD also print
the full chain of a value that *is* traced:

```text
then.result.0.total = 40   (bob-views-orders)
  ← placed.total            (bob-places-order)   derived: quantity × unitPrice
    ← place.quantity = 1    (bob-places-order)   input by customer/bob
    ← place.unitPrice = 40  (bob-places-order)   input by customer/bob
```

### 7.9 Rules

| Rule | Severity | Description |
|---|---|---|
| `flow/provenance/unsourced-value` | error | A value has no annotation, and implicit tracing finds no source in `V(o)`. |
| `flow/provenance/entry-point-not-allowed` | error | An entry point is used where §7.2 does not allow it, or `generated` marks an instance whose aggregate is not `generated`. |
| `flow/provenance/source-not-visible` | error | A `from` or `derived` reference points outside `V(o)`. |
| `flow/provenance/source-value-mismatch` | error | A `from` reference points at a value that is not equal to the annotated value. |
| `flow/provenance/generated-value-not-fresh` | error | A `generated` value already appeared earlier in the story. |
| `flow/provenance/instance-not-addressed` | error | An instance is used without being created or addressed as required by §7.7. |
| `flow/provenance/input-could-be-traced` | warning | A value is marked `input`, but `V(o)` contains an equal value under the same key. The actor probably did not type it in but took it from what they saw. |

## 8. Projection to Given-When-Then (informative)

Every slice can be turned mechanically into a GWT scenario of the ESDM extension:

| Slice | GWT feature | given | when | then |
|---|---|---|---|---|
| command slice on instance `i` | `aggregate` feature of the slice's aggregate | all earlier events on instance `i` (bare names + data) | `command`, `data`, `actor` | `events` or `rejection` |
| read-model slice | `read-model` feature | all earlier events the read model projects from (scoped references + data) | `query`, `parameters` | `result` or `readModel` |

This means a flow can **generate** GWT features. Later, a tool could also check
that the flow is consistent with the core's existing features (Q8).

Note: `given` contains only what the story tells. A flow is a narrative
excerpt, not an event store.

## 9. Open questions

| # | Question | Current position |
|---|---|---|
| Q1 | May one slice produce the same event artifact twice, as in bulk operations (two `item-added`)? | No (`duplicate-event-in-slice`), until there is a convincing case. |
| Q2 | Dynamic consistency boundaries as the center of a command slice. | Not in v0. The `when`/`then` shape would stay the same; `aggregate` would become a choice between aggregate and DCB with multi-part identity. |
| Q3 | Process managers as trigger and as center, with per-instance state and timers. | Not in v0. Needs instance identity via `correlatedBy`. |
| Q4 | Event handlers and external systems (translation slices, inbound data from third parties as an entry point `external`). | Not in v0. |
| Q5 | Should personas be declared up front, with an actor each, rather than being free strings? | Free strings in v0. |
| Q6 | Implicit tracing by key is a heuristic. Does it hold up for deeply nested data? | Explicit `from` is always possible. Collect real cases. |
| Q7 | Should screens be modeled? In Event Modeling, wireframes are the source of command input. Here, earlier read-model slices take that role. | Read-model slices in v0. |
| Q8 | Generate GWT features from flows, or check flows against existing features? | Generating is informative (§8); checking is open. |
| Q9 | `input` is an escape hatch: any value can be declared as typed in. | Accepted. It is visible in review, and `input-could-be-traced` catches the obvious cases. |
| Q10 | Hosting of the `apiVersion` and of the schema, and the path upstream. | Repository URL for now; propose upstream after first feedback. |
| Q11 | Query semantics: a result row from another customer's order is traceable, because it comes from a projected event, but it is still wrong. | Not checked. Filtering and selection are prose rules in the core, like projections. |
