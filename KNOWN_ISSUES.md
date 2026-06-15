# Moyun Studio Known Issues

These issues do not block the current `v0.2.0` developer preview release, but they should remain visible for T9 planning and future maintenance.

## Release Status

- Target version: `v0.2.0`
- Positioning: Writing Quality Loop Developer Preview
- Release type: internal developer preview, not a commercial production release

## P2

1. Full E2E currently has 93 skipped tests.
   - Most skipped tests are guarded real backend / real LLM / phase smoke scenarios.
   - T9.2 should classify which tests should be restored, rewritten, or kept as manual smoke.

2. Validator is limited for narrative / terminal hook judgment.
   - The beat validator is useful for explicit required / forbidden facts.
   - It is less reliable for subtle narrative quality, implicit emotion, and ending-hook judgment.

3. TOCTOU / atomic write hardening remains future work.
   - FILE_CONFLICT, hash, and mtime checks are active.
   - Fully atomic candidate/file writes still need future hardening.

4. Real LLM latency depends on model service.
   - Slow responses depend on local model, hosted endpoint, network, and provider behavior.
   - The UI now shows clearer long-wait and error states, but latency itself is not solved by the product.

## P3

1. MCP Unicode transport issue remains.
   - This affects some external MCP/helper paths, not the core backend product flow.

2. Polish may still produce awkward phrases.
   - Conservative polish rules reduce continuity drift and over-editing.
   - Some awkward phrasing may remain and should be handled through candidate review or feedback revision.

3. Mock helpers have duplication.
   - E2E mock setup can be consolidated during T9.2.

4. `waitForTimeout` hard sleeps remain in tests.
   - T9.2 should replace fragile sleeps with condition-based waits where practical.

5. Candidate file writes are not fully atomic.
   - This is related to future filesystem hardening and does not block the developer preview.

## Non-blocking Release Note

The issues above do not block the current developer preview release because the core safety contract is intact:

- AI output enters candidate drafts first.
- Official scene text changes only after explicit adopt.
- Delete/discard does not modify official text.
- FILE_CONFLICT/hash/mtime safety remains in force for formal writes.
