# Implementer dispatch (fallback when the plugin agents are unavailable)

With the plugin installed, dispatch `shipwright:sw-implementer` instead. It already contains
these rules. Without it, send a general-purpose subagent this prompt, with the paths filled in:

```text
Read <skill folder>/disciplines/implementation.md completely and follow it.

Plan: <absolute path to .shipwright/work/<item>/plan.md>
Skill folder: <absolute path to the shipwright skill>
```

**Model:** use a fast model for mechanical plans, and a stronger model for plans that span
many files or need judgment. From the third loopback onward, dispatch a **fresh** implementer
on the strongest model (see `phases/review.md`).

**Patches:** keep the implementer addressable. Review patches go back to it with: "Fix each
with the smallest change; run only the covering tests; reply with what you changed."
