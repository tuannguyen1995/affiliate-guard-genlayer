# AffiliateGuard

AffiliateGuard is a decentralized affiliate marketing escrow platform that uses GenLayer's Intelligent Contracts to automatically verify content requirements and process payouts via AI consensus.

## Deployed Contract
- **Contract Address:** `0xdA32797FEaed009f6528366006697b6158D0e762`
- **GenLayer Explorer:** [https://genlayer-explorer.vercel.app/address/0xdA32797FEaed009f6528366006697b6158D0e762](https://genlayer-explorer.vercel.app/address/0xdA32797FEaed009f6528366006697b6158D0e762)

## Live App
- **Production URL:** [https://affiliateguard-one.vercel.app](https://affiliateguard-one.vercel.app)

## How it Works
1. **Brand Escrow:** Brands create a campaign with a designated Creator, escrow amount, product requirements, CTA, and blacklist keywords.
2. **Creator Acceptance & Staking:** The designated Creator deposits a mandatory 20% stake to accept the campaign terms (skin-in-the-game to prevent spam).
3. **Evidence Path & Authenticated Verification:** The Creator submits their authenticated video/media transcript. GenLayer's built-in AI consensus nodes fetch the content (`gl.nondet.web.render`) and verify:
   - **Campaign & Creator Binding:** The evidence explicitly embeds the unique `[Campaign: <id>]` and designated `[Creator: <address>]` to prevent replay attacks / stolen third-party content.
   - **Authenticated Transcript & Audio:** Verifies verbal product mentions, spoken CTA, language subtitles, and zero blacklist keywords.
   - **Visual & Media Compliance:** Evaluates authenticated visual media cues/timecode markers (`[Visual: <logo>]`) rather than relying on mutable web text.
4. **Auto Payout / Revision / Dispute:**
   - **RELEASE/PARTIAL:** Payout enters a mandatory 24-hour cooling-off delay (`AWAITING_PAYOUT`). The Brand can dispute the AI consensus if needed. If no dispute occurs within 24h, payout is finalized.
   - **REFUND / SLASHING:** If the video fails, the Creator gets 1 chance to revise and resubmit. If it fails twice, the Creator's stake is slashed and refunded along with the escrow to the Brand.
   - **DISPUTE RESOLUTION:** Authorized arbitrator can resolve disputes with `RELEASE`, `REFUND`, or `SPLIT`. Stale disputes (>30 days) can be recovered via automated 50/50 split and stake refund.

## Adversarial & Regression Test Suite

An exhaustive test suite is implemented in [`tests/test_adversarial.py`](./tests/test_adversarial.py) (10 tests) and [`tests/test_adversarial.js`](./tests/test_adversarial.js) (9 simulations) covering:
- **Evidence Binding & Anti-Replay Defense**: Rejects unauthenticated/unbound third-party content lacking campaign ID and creator proof.
- **Visual Compliance Authenticity**: Distinguishes authentic visual media markers from plain mutable page text (yielding `PARTIAL` rather than full `RELEASE`).
- **Under-Staking Defense**: Rejects stake amounts < 20%.
- **Early/Unauthorized Payout Defense**: Enforces 24h cooling-off and caller authorization for all parties.
- **Anti-Timestamp-Manipulation**: Validates 7-day cancellation timeout using trusted context.
- **Validator Disagreement Handling**: Verifies consensus passes on semantic equivalence and reverts on disagreement.
- **Brand Dispute Exploit Defense**: Prevents malicious self-refunds.
- **Terminal Fund Flows**: Release, Partial, Slashing, Dispute Resolution, and Stale Recovery.
