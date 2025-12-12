# Hardening Task: Improve Judge Scoring (Task 3.2)

**Goal**: Enhance `src/anvil/steps/judge.py` to use per-track verification artifacts.

**Current State**:

- `Judge.run` (lines 30-134) currently calculates scores based heavily on "confidence" (self-reported) and "Patch existence".
- It has comments acknowledging Task 3.2: "Run verification per-worktree OR use per-track metrics".

**Requirements**:

1.  Read `src/anvil/steps/judge.py`.
2.  Update the scoring logic to check for the existence of `VERIFY.md` in the track's latest iteration folder (`tracks/{name}/{iter}/VERIFY.md`).
3.  If `VERIFY.md` exists _and_ contains "PASS" (or similar signal, or just exists as proof of verification run), add significantly to the score (e.g., +40 points).
4.  If `VERIFY.md` exists but indicates failure (e.g. contains "FAIL"), deduct points.
5.  Generate a patch to implement this logic.

**Context**:
Anvil tracks may run their own verification steps. The Judge should prioritize tracks that have actually run verification over those that just produced a patch with high confidence.
