# Sightline Architecture — Draft, Not Submitted

```mermaid
flowchart LR
    A["Bounded baseline PNG"] --> C["OpenCV 5 perception"]
    B["Bounded candidate PNG"] --> C
    C --> D["Typed visual findings"]
    D --> E["Deterministic policy"]
    E --> F{"Material risk?"}
    F -->|"No"| G["Accept no material change"]
    F -->|"Yes"| H["Request human approval"]
    D --> I["SHA-256 evidence trace"]
    H --> J["No execution authority"]
    I --> J
    K["Lambda-compatible handler"] --> C
    L["Deterministic source artifact"] --> M["Inert AWS plan"]
    M --> N["Prepare only; no credentials or deployment"]
```

A self-contained companion rendering is stored in `ARCHITECTURE.draft.svg`. It contains no external fonts, scripts, images, links, or network references.

## Trust Boundaries

- Image inputs are bounded and decoded locally.
- OpenCV findings are data, not execution authority.
- The decision engine has no mutation or deployment tool.
- The AWS plan is metadata only and cannot execute.
- Credential, deployment, and spend authority must remain false.
- Judge-facing materials exclude secrets, customer data, and private operational details.

## Demonstration extension

The recorded local journey adds a separate fixture controller. OpenCV evidence changes the approval request; an unapproved action is rejected; a scripted one-use, candidate-bound demo event permits only restoration of the injected DOM visibility; a fresh screenshot is measured again. This does not add a production mutation tool to the planner. A real human approval was not observed. The revised delivery diagram shows this loop and places the unverified AWS runtime in a separately labeled boundary.
