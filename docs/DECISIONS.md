# Current engineering decisions

1. Port the original 2002 Xbox game independently, using generic tools; no BuffyNX-specific code, symbols, seeds or overrides.
2. Pin the generic XboxRecomp fork and keep runtime changes in six separate source patches. Preserve component licenses and notices.
3. Accept only the identified XBE/MAP hashes. Derive game addresses from the supplied inputs; refuse other editions before adaptation.
4. Fix generated behavior through the generator adapter, with calling-convention evidence and tests. Preserve guest state and relevant floating-point semantics.
5. Start the player launcher at the menu, indefinitely, with a title-bound persistent profile. Direct mission boot remains a private-state diagnostic outside the release setup.
6. Generate a blank disk from generic retail geometry for first-time players. Never use the developer save as the installation seed.
7. Compress dormant partitions losslessly, restore them before execution, and retain raw data on failure. Do not shrink the geometry seen by the guest.
8. Keep original assets as the clean-install default. Offer the explicitly approved prebuilt HD add-on separately, with pinned hashes and an immutable local installation. Keep assets out of Git and the source ZIP; editable masters and model weights remain private. The MIT code license does not cover game-art rights.
9. Use a five-language launcher with persistent keyboard/controller remapping loaded before input threads; no live remapping in a game session.
10. Validate all ISO paths/extents and resources before extraction. Use staging and macOS exclusive rename; never overwrite an existing installation.
11. Install Python packages only in the local venv. Native build prerequisites remain explicit. No game download or development AI requirement.
12. Export a reviewed source-only file list. Keep private development history, generated game data, logs and binaries out of the public package.
13. Use MIT for original project code, as chosen by the owner on 8 November 2026. Third-party file licenses retain precedence.
14. Describe the actual validation stage. One Mac, real menu/save/load evidence and existing user gameplay are not proof of full campaign, audio stability or cross-machine support.

13. Name the project and repository btvs-recomp. Keep save identifiers, the source-folder location and internal runtime filenames compatible. Include only the explicitly requested title-inspired wordmark and original README navigation graphics in source; their narrow allowlist does not admit gameplay assets. The HD v1 bytes are unchanged, with a renamed attachment and updated checksum filename entry.

14. Include the explicitly requested original-style moon as a separate branding layer behind the unchanged wordmark. Permit only docs/branding/moon.png in addition to the existing graphics allowlist. The self-contained presentation SVG has a 6 MiB limit to accommodate its two embedded PNGs; other source/member limits remain unchanged.
