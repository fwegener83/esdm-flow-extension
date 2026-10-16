# Fixtures

This is the conformance suite for flow linters. Any implementation of the spec
must produce exactly the findings listed here.

## Layout

```text
fixtures/
├── model/                 # shared ESDM core model (lints clean with `esdm lint`)
├── valid/<case>/          # flows without findings
└── invalid/<case>/        # flows with exactly the listed findings
    ├── flow.flow.yaml
    └── expected.yaml
```

## `expected.yaml`

```yaml
model: ../../model         # core model directory, relative to the case
findings:
  - rule: flow/provenance/unsourced-value
    severity: error
    slice: clerk-ships-order-2
    path: then.events[shipped].data.customerId
```

An implementation conforms on a case if the multiset of `(rule, severity,
slice)` it reports equals the listed one. `path` is informative: it shows where
the finding belongs, but its exact syntax is not normative yet. Events in a
slice are addressed by name (`then.events[shipped]`).

`invalid/` also holds cases that only produce warnings. Each case isolates
exactly one cause, so that a finding can be attributed unambiguously.

## The shop model

`ordering` holds an `order` aggregate (`place`, `ship`, `cancel`), the read
model `my-orders` and the actors `customer` and `warehouse-clerk`. `billing`
holds an `invoice` aggregate. The policy `create-invoice-on-order-placed` links
the two.
