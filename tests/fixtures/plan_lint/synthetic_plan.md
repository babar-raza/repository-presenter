# Synthetic plan fixture (tests/test_plan_lint.py)

Invented cards that exercise every lint rule. It is not a plan: nothing here is a real card,
requirement or work item, and it grants no authority.

```yaml
plan_id: PLAN-SYNTHETIC
serialised_paths: []
```

## 3. Requirements (stable IDs)

REQ-AAA-01 first requirement · REQ-BBB-01 second requirement · REQ-CCC-01…02 two requirements as a range

## 8. Taskcards

```yaml
- id: TC-AAA-01
  title: First card
  reqs: [REQ-AAA-01]
  item: G7-W90
  lane: L-one
  depends: []
  governed: false
  paths: {write: [docs/synthetic/one/], forbidden: [docs/synthetic/other/]}
  outcome: something observable
  accept: ["a check"]
  children:
    - id: TC-AAA-01-01
      title: First child
      steps:
        - "inspect | docs/synthetic/one/a.md | notes recorded"
        - "create | docs/synthetic/one/b.md | file exists"
    - id: TC-AAA-01-02
      title: Second child
      steps:
        - "run | python -V | version printed"

- id: TC-BBB-01
  title: Second card
  reqs: [REQ-BBB-01]
  item: G7-W90
  lane: L-two
  depends: [TC-AAA-01]
  governed: false
  paths: {write: [docs/synthetic/two/]}
  outcome: another observable
  accept: ["a check"]
  children:
    - id: TC-BBB-01-01
      title: Only child
      steps:
        - "edit | docs/synthetic/two/x.md | text changed"
        - "validate | pytest tests/test_plan_lint.py -q | passes"

- id: TC-CCC-01
  title: Third card, parallel with the second
  reqs: [REQ-CCC-01, REQ-CCC-02]
  item: G7-W91
  lane: L-three
  depends: [TC-AAA-01-02]
  governed: true
  ground: "factual-accuracy plus owner approval D-OWN-2"
  paths: {write: [src/repository_presenter/components/readme/review/, docs/synthetic/three/]}
  outcome: a governed observable
  accept: ["a check"]
  children:
    - id: TC-CCC-01-01
      title: Map the code (investigation)
      kind: investigation
      produces: [TC-CCC-02]
      steps:
        - "inspect | the reviewer fold | demotion paths listed"
    - id: TC-CCC-01-02
      title: Record the decision
      steps:
        - "decide-owner | go or no-go | decision recorded"
        - "record | decisions/x.md | file hashed"
```
