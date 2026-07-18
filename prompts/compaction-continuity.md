## Compaction continuity

When the active compaction prompt requests a summary, follow its requested format and enrich it with a concise, operational continuation state. Preserve the global picture, reasoning trajectory, and exact next actions so the task can resume directly from the summary.

Include the following when relevant:

- Current objective: the latest user goal and request, expected deliverable, scope, constraints, approvals, corrections, and decisions.
- Work state: completed actions; materials, sources, records, data, files, conversations, applications, environments, or interfaces examined; methods and tools used; changes or state transitions made; artifacts created; key evidence; and precise locations or identifiers needed to continue.
- Reasoning state: the approach taken, questions pursued, decision criteria, working model, hypotheses tested, alternatives ruled in or out, and why the current conclusions follow.
- Exploration map: the important sources, areas, hypotheses, and routes already explored; why each mattered; the key anchors or facts found; current coverage; remaining gaps; and the relationships or paths to follow next.
- Conclusion state: confirmed conclusions with supporting evidence, and provisional conclusions that require further exploration with their partial evidence, uncertainty, missing links, significance, and next direction.
- Unresolved leads: every lead that could materially affect the outcome, interpretation, decision, risk, deliverable, or next action, together with its current evidence and next check.
- Open-conclusion state: when the conclusion remains open, preserve the accumulated map, including negative evidence, patterns, contradictions, unsuccessful approaches, ruled-out hypotheses, partial synthesis, the current working model, missing links, and the strongest next direction. This allows the next phase to build directly on the existing global view.
- Remaining work: the exact status of plans and TODO items, pending deliverables, unchecked material, unverified assumptions, open questions, blockers, risks, dependencies, and next concrete actions.
- Communication and delivery state: what the user has already been told, what has been delivered, whether a final response has been sent, and any user confirmation or authority needed.
- Completion gate: record the exact conditions that must be satisfied before a final response is appropriate, and why the task cannot yet end. If any condition remains unmet, list it and mark the task as in progress or blocked. Mark the task as completed or ready for final response only after every requested item, deliverable, and required verification is finished. The task status must remain consistent with the remaining work and completion gate.

Favor concise operational detail and give unresolved work the same visibility as confirmed findings, especially after broad reading, observation, research, experimentation, tool use, or partial progress.
