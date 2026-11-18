# Individual Contribution Record — Member 4: Pipeline Validation, Reproducibility and Deployment

> **Complete the placeholders and remove any statement that does not match the work you personally performed.** This record describes the agreed Member 4 workstream; it must be checked against the actual branch diff before submission.

## Contributor details

| Field | Entry |
|---|---|
| Contributor | `[Full name]` |
| GitHub username | `[GitHub username]` |
| Student ID / SRN | `[Include only if required by the course or event]` |
| Assigned branch | `feat/member-4-pipeline` |
| Contribution period | `[Start date – end date]` |
| Pull request | `[PR URL]` |
| Main contribution commits | `[Commit hashes / links]` |

## Contribution summary

Member 4's allocated responsibility was to make the PathSnap pipeline easier to run, validate, reproduce and demonstrate. This workstream covers automated tests, prepared-data and pipeline checks, dependency/setup instructions, task tracking and deployment verification.

The contribution should distinguish tests that were actually run locally from tests or deployment steps that remain planned. Do not describe a two-computer/LAN demonstration as verified unless the requests were genuinely made from a separate machine and the backend logs or equivalent evidence confirm it.

## Work personally performed

| Work area | What I personally did | Evidence / files |
|---|---|---|
| Pipeline tests | `[Describe test cases you wrote or materially changed and the failures they guard against.]` | `[Exact path / commit]` |
| Prepared-data validation | `[Describe checks for array shapes, IDs, labels, missing files or other invariants.]` | `[Exact path / commit]` |
| Reproducibility | `[Describe setup, deterministic settings, commands and repeatability checks.]` | `[Exact path / commit]` |
| Project instructions | `[Describe README/setup/troubleshooting changes.]` | `[Exact path / commit]` |
| Dependency / repository hygiene | `[Describe requirements, ignore rules or attributes changed and why.]` | `[Exact path / commit]` |
| Deployment validation | `[Describe API/UI, CORS, LAN, firewall and cross-machine checks actually performed.]` | `[Logs / screenshots / commit]` |

## Files owned or materially changed

The agreed branch allocation identified these likely files. Keep only files that appear in your actual contribution and describe your changes precisely.

| File | Role in the workstream | My actual change |
|---|---|---|
| `tests/test_pipeline.py` | Pipeline and regression tests | `[List the tests you added or changed and their assertions.]` |
| `README.md` | Installation, usage and project documentation | `[Describe the sections you wrote or updated.]` |
| `TASKS.md` | Task and implementation status tracking | `[Describe the status changes and evidence used.]` |
| `requirements.txt` | Python dependency specification | `[List the dependency changes and compatibility checks.]` |
| `.gitignore` | Exclude generated data, caches and local artefacts | `[Describe the ignore rules and reason.]` |
| `.gitattributes` | Consistent Git handling of selected files | `[Describe the attributes you added and why.]` |
| `deployment/verify_prepared.py` | Prepared-data verification utility | `[Confirm whether this file exists and describe your contribution.]` |
| Other: `[path]` | `[Purpose]` | `[Actual change]` |

## Technical approach

Explain only the checks and deployment work you personally carried out. Relevant topics may include:

1. How tests construct inputs and verify expected pipeline behaviour.
2. How the tests detect invalid IDs, inconsistent array lengths, bad candidate references or malformed prepared outputs, if applicable.
3. How a clean environment is configured and dependencies are installed.
4. How model artefacts and data paths are configured without committing private credentials or large raw datasets.
5. How the API and UI are started and connected.
6. How HTTP responses, error cases, CORS and network reachability are checked.
7. What evidence proves a two-device deployment, if one was completed.

**My implementation / validation explanation:**

`[Write your explanation here, including commands, expected outcomes, assumptions and failure handling.]`

## Verification and results

| Check | Command / method | Actual result | Evidence |
|---|---|---|---|
| Unit / pipeline tests | `[Exact command]` | `[Pass/fail count and date]` | `[Test output / CI run]` |
| Prepared-data validation | `[Exact command]` | `[Observed result]` | `[Log / output]` |
| API smoke test | `[Exact request or command]` | `[HTTP status and response checks]` | `[Log / screenshot]` |
| UI smoke test | `[Browser / procedure]` | `[Observed result]` | `[Screenshot]` |
| Cross-device test | `[Source machine, destination machine and request]` | `[State verified or not verified; include evidence]` | `[Backend log / screenshot]` |
| Clean setup / reproducibility | `[Exact commands]` | `[Observed result]` | `[Log / commit]` |

Do not report a test as passing solely because a script exists. Include the command and actual result. Distinguish a same-machine localhost test from a cross-machine network test.

## Collaboration and handoff

`[Explain what test results, setup instructions, deployment requirements and unresolved defects you communicated to the other members.]`

## Tools and AI assistance

- Languages / libraries / tools used: `[List only those actually used.]`
- AI assistance: `[State whether AI tools helped write tests, inspect errors or draft documentation, and what you personally ran, reviewed or corrected. If none, say none.]`
- External material: `[List relevant API, library or deployment documentation, if applicable.]`

## Limitations and follow-up

`[List tests not yet run, unsupported environments, deployment evidence still missing and known defects. Be explicit about whether official-evaluator and two-device checks were completed.]`

## Contributor confirmation

I confirm that this record describes my own contribution accurately, distinguishes my work from the work of other members and AI tools, and is consistent with the cited branch changes and evidence.

**Name:** `[Full name]`  
**Date:** `[Date]`
