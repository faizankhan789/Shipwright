# Architecture: {title}

<!-- Only the decisions that keep separately built slices consistent. Short beats complete.
     Every significant choice also gets an ADR (`shipwright.py adr "<title>"`). -->

Council: FILL: the council folder whose decision this architecture implements (e.g. 01-billing-architecture)

## Shape

Components, their boundaries, and who owns which data. A small diagram if it helps.

## Decisions

| Decision | Choice | Prevents (what goes wrong without it) | Version (verified, date) | ADR |
|---|---|---|---|---|
| Stack | | | | |
| Data store | | | | |
| Auth | | | | |

## Data model

Entities, key fields, relationships, invariants.

## Contracts

APIs, events, file formats between components: names, shapes, error conventions.

## Cross-cutting rules

Errors, logging, config and secrets, testing levels, performance budgets, accessibility floor.

## Slices

<!-- Ordered vertical slices; each is one size-M work item, independently shippable and testable.
     Slice 1 is a walking skeleton: thinnest end-to-end path.
     Record as: N. title -- after: ids -- covers: R1, R3 (every brief requirement covered by some slice) -->

1. 
