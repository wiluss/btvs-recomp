# Project instructions

- Target Buffy the Vampire Slayer (2002, original Xbox), not Chaos Bleeds.
- Keep the project independent. Do not import BuffyNX-specific code, symbols, seeds or overrides. Prior research consulted it; do not claim otherwise.
- Read README.md, docs/DECISIONS.md and relevant component instructions before editing.
- Verify the supplied XBE against config/title.json before address-dependent adaptations.
- Permanent fixes belong in a versioned generator adapter or reviewed override, not in generated C. Document the calling convention, evidence and regression.
- Define a reproducible case before optimizing. Preserve guest registers, flags, stack, memory effects and relevant floating-point semantics.
- Keep generic runtime changes in separate reviewed patches. Do not silently change the dependency revision or reset existing work.
- Never publish an ISO, XBE, MAP, save, disk image, model weight, generated game source, recompiled game binary or secret. Keep assets out of Git and the source ZIP. The user explicitly authorized the selected prebuilt HD add-on as a separate release attachment; use only tools/hd_pack.py's reviewed allowlist. Keep editable masters private. Keep long traces local under artifacts/.
- Distinguish host checks, compilation, menu, gameplay and long-session validation. Do not use a mock game screen as launch evidence.
- After relevant changes run make test; for native code also run make host-probe. Update the roadmap with the actual validation scope.
- Optional local-AI developer proposals need review. An AI model is not required for setup, tests or gameplay. Do not execute a model's suggested commands automatically.
- Use the explicit release file list and audit the resulting archive. Preserve third-party headers, notices and license scopes.
- The user explicitly requested the title-inspired btvs-recomp wordmark and visual README. Only the selected logo and passive SVG buttons/status strip under docs/branding are allowed in Git and the source kit. This does not authorize other game images or HD data in source.
