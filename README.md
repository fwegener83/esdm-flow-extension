# ESDM Flow Extension

Stories across consistency units for [ESDM](https://www.esdm.io/), the format
for event-sourced domain models. They are machine-checkable, both for whether
the story is told correctly and for whether it holds together.

ESDM describes the static structure of a domain and Given-When-Then examples for
one consistency unit at a time. This extension adds the missing level: the
**flow**, an ordered story of **slices** across aggregates, read models,
policies and bounded contexts, told with concrete values.

A flow linter answers two questions:

1. **Is the story possible?** Every slice uses the core model's own artifacts in
   ways the model allows, and in causal order.
2. **Does the story hold together?** Every value shown, up to the last read
   model, can be traced back through the story to a declared point where it
   entered the system. Nothing is invented.

> **Status:** early draft (v0). This repository holds a specification, not yet a
> tool.

## Contents

| Path | What |
|---|---|
| [`spec.md`](spec.md) | The specification: terms, format, rules (Part A: narrative, Part B: provenance), open questions. |
| [`schema/flow/v0.yaml`](schema/flow/v0.yaml) | JSON Schema for flow documents. |
| [`fixtures/`](fixtures/) | Conformance suite: one core model and valid/invalid flows with the findings each must produce. |
| [`scripts/check-fixtures.py`](scripts/check-fixtures.py) | Checks that all fixtures match the schema. |

## A taste

```yaml
- name: clerk-ships-order
  type: command
  trigger: { actor: warehouse-clerk }
  aggregate: { boundedContext: ordering, aggregate: order, instance: o-1 }
  when:
    command: ship
    data: { orderId: o-1 }
    provenance: { orderId: input }
  then:
    events:
      - event: shipped
        data: { orderId: o-1, customerId: c-alice, shippedAt: "2026-10-05T14:30:00Z" }
        provenance: { shippedAt: clock }
```

`customerId` needs no annotation, because it comes from the state of order
`o-1`, which an earlier slice in the story established. If the event carried
Bob's customer ID instead, the linter would report it. Both orders are of the
same kind, but only the state of this instance counts. The full story is in
[`fixtures/valid/two-orders`](fixtures/valid/two-orders/flow.flow.yaml).

## Checking the fixtures

```sh
pip install pyyaml jsonschema
python3 scripts/check-fixtures.py
```

The shared core model in `fixtures/model/` lints clean with `esdm lint`.
