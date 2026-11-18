# IA/GRC project continuity

For work on the combined Excel and Development Scope v1 plan, read `docs/PLAN_PROGRESS.md` and `docs/AGENT_HANDOFF.md` first. They record the current priority, Notion links, accepted source amendments, verification evidence and next work. Read `docs/DEVELOPMENT.md` for implementation/security/testing rules.

The user coordinates this plan from the existing chat. Preserve its original Excel baseline and combined Notion plan. Update the progress record and relevant Notion tasks after meaningful verified milestones; do not infer completion from code presence or task creation. Do not change unrelated work, commit/push, release, deploy, or send messages unless authorized in the current session.

Parallel agents are authorized for this project when useful. Give each agent an explicit file/module boundary and API contract. Shared application files have one integration owner. Run mutating acceptance suites sequentially on a shared disposable site, or use separate sites.

Never place site credentials, OTPs, tokens, database dumps or private customer data in these records. Record exact Done executable leaves out of the 46-leaf baseline, with any later scope changes explicitly counted. Keep local implementation, local verification, UAT and production deployment separate.
