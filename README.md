# AffiliateGuard 🛡️

AffiliateGuard is a decentralized affiliate marketing escrow platform powered by **GenLayer's Intelligent Contracts**. It automates creator verification, content requirement validation, and trustless dispute resolution directly through decentralized multi-agent AI consensus.

## 🚀 Live Links & Verification
- **Production dApp:** [https://affiliateguard.vercel.app](https://affiliateguard.vercel.app)
- **Deployed Contract Address:** `0x37F4206F9b910c06F517A258D28dCf744C0dfb3e`
- **GenLayer Studio Explorer:** [https://studio.genlayer.com/explorer/contract/0x37F4206F9b910c06F517A258D28dCf744C0dfb3e](https://studio.genlayer.com/explorer/contract/0x37F4206F9b910c06F517A258D28dCf744C0dfb3e)
- **Network:** GenLayer Studio Network (`studionet`, Chain ID: `61999` / `0xF1EF`)
- **JSON-RPC Endpoint:** `https://studio.genlayer.com/api`

---

## ⚡ Major Milestone Updates (v1.2.0)
- **On-Chain Creator Reputation Engine (`CreatorProfile`)**: Real-time persistent state tracking in GenVM (`TreeMap[str, CreatorProfile]`), maintaining creator lifetime completed campaigns, dispute rates, and consensus slashing history.
- **Dynamic Tiered Staking**: Automatically computes required collateral based on on-chain reputation:
  - 🥇 **GOLD Tier** (Score ≥ 150): **10% stake** (50% fee discount for trusted creators).
  - 🥈 **SILVER Tier** (Score 100 - 149): **20% stake** (Standard baseline).
  - 🥉 **BRONZE Tier** (Score < 100): **30% stake** (High-collateral barrier against spam/disputed creators).
- **Interactive Consensus Simulator & Forensic Sandbox**: In the live dApp, anyone can test all 4 core consensus paths (`RELEASE`, `PARTIAL`, `REFUND`, `SLASH`) with real-time multi-agent voting breakdowns.
- **Live On-Chain Reputation Registry UI**: Query any creator address directly from the GenLayer blockchain to inspect live score, tier badges, and collateral rates.
- **System Architecture & Sequence Documentation**: See [`ARCHITECTURE.md`](./ARCHITECTURE.md) for Mermaid flowcharts and GenVM lifecycle details.
- **Threat Model & Adversarial Analysis**: See [`SECURITY.md`](./SECURITY.md) for detailed invariant defenses and test verification matrices.
- **Release History**: See [`CHANGELOG.md`](./CHANGELOG.md).

---

## 🔑 How It Works

```
[Brand Creates Campaign] ──► [Creator Deposits 20% Stake] ──► [Creator Submits Evidence]
                                                                        │
                                                                        ▼
                                                          [GenLayer AI Consensus Nodes]
                                                                        │
                 ┌──────────────────────────────────────────────────────┴───────────────────────────────────────┐
                 ▼                                                      ▼                                       ▼
        [Clean Verification]                                 [Raw Web Scrape / Logo]               [Blacklist / Failure]
              RELEASE                                                PARTIAL                               REFUND
                 │                                                      │                                       │
                 ▼                                                      ▼                                       ▼
    [24h Cooling-Off Delay]                                [24h Cooling-Off Delay]                     [Escrow Refunded,
  (Undisputed -> Full Payout)                            (Undisputed -> 50/50 Split)                  Stake Safely Returned]
```

1. **Brand Escrow:** Brands deposit GEN tokens into the contract and configure required products, call-to-action (CTA), required languages, brand logo descriptor, and blacklisted keywords.
2. **Creator Acceptance & Staking:** The designated Creator deposits a mandatory 20% stake (skin-in-the-game) to accept campaign terms.
3. **Authentic Platform Evidence & Account Verification:**
   - **Canonical Hostname Matching:** Enforces official media domains (`youtube.com`, `tiktok.com`, `instagram.com`, `x.com`). Rejects substring exploits (e.g. `attacker.com/youtube.com`) and pastebins.
   - **On-Chain Creator Account Registry:** Creators register their handle on-chain (`register_creator_handle`). Evidence metadata must structurally bind to the registered handle.
   - **Transcript Provenance:** Spoken product mentions and CTAs are strictly validated from audio captions/subtitles.
   - **Non-Inference Visual Frame Rule:** Plain text scraped from an HTML webpage cannot prove visual pixels. If a Brand Logo is required, unstructured text defaults to `PARTIAL` rather than `RELEASE`, enforcing a mandatory 24-hour cooling-off inspection window.
4. **Decentralized Validator Consensus Dispute Resolution (Ownerless Slashing):**
   - **Safe Stake Protection:** Routine non-compliance safely refunds Brand escrow and returns Creator stake. Creator stakes are never blindly slashed based on mutable web scrapes.
   - **Trustless Multi-Agent Slashing:** Slashing (`SLASH`) is exclusively determined by GenLayer Multi-Agent LLM Consensus (`gl.vm.run_nondet`) on confirmed, deliberate fraud. Single-sig owners cannot seize funds.
   - **Stale Dispute Recovery:** Disputes sitting unresolved for >30 days can be recovered via automated 50/50 split and stake return (`recover_stale_dispute`).

---

## 🧪 Adversarial & Regression Test Suite
 
An exhaustive test suite is implemented across Python (`pytest`) and JavaScript (`Node.js`):
 
```bash
# Run 29 Python Adversarial, Reputation & Regression Tests
pytest tests/ -v
 
# Run 14 Node.js End-to-End Adversarial Simulations
node tests/test_adversarial.js
```

### Verified Scenarios:
1. **Under-Staking Defense**: Rejects creator stake < 20%.
2. **Early/Unauthorized Payout Defense**: Enforces 24h cooling-off and caller authorization.
3. **Anti-Timestamp Manipulation**: Validates trusted datetime execution context.
4. **Semantic Verdict Consensus**: Confirms validators match on meaning while ignoring explanation wording.
5. **Brand Self-Refund Exploit Defense**: Prevents unilateral fund seizures.
6. **Safe Stake Decoupling**: Protects creator stake from heuristic scrape false-positives.
7. **30-Day Stale Recovery**: Automatically resolves stalled disputes.
8. **Replay & Impersonation Defense**: Rejects third-party content reuse.
9. **Visual Non-Inference Rule**: Plain text without visual frames is capped at `PARTIAL`.
10. **Canonical Domain Defense**: Rejects unauthenticated pastebin and spoofed URLs.
11. **Trustless Validator Slashing**: Stakes slashed only on consensus-proven fraud.
12. **Raw Scrape Constraint**: Unsupported rendered text cannot cause `RELEASE` or `SLASH`.

---

## 🛠️ Tech Stack
- **Smart Contract:** GenLayer Intelligent Contract (`Python`, GenVM, `gl.vm.run_nondet`)
- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS / Vanilla Modern Dark Mode
- **Web3 Integration:** `genlayer-js`, `ethers v6`
- **Deployment:** Vercel Production, GenLayer Studio Network (`studionet`)
