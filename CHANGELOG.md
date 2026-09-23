# Changelog

All notable changes to the AffiliateGuard project are documented in this file in accordance with [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-09-23 - Major Feature Milestone: On-Chain Creator Reputation & Dynamic Tiered Staking

### Added
- **Persistent On-Chain Creator Reputation Engine (`CreatorProfile`)**:
  - Implemented `@allow_storage @dataclass class CreatorProfile` stored in GenVM `TreeMap[str, CreatorProfile]`.
  - Tracks creator lifetime stats: `reputation_score`, `completed_campaigns`, `disputed_campaigns`, `slashed_campaigns`, and `tier`.
  - Automated state transitions: +15 points awarded on successful clean release; +5 points on partial payout; -25 points on valid brand dispute; -50 points on consensus-confirmed fraud slashing.
- **Dynamic Tiered Staking Mechanism**:
  - **GOLD Tier** (Score ≥ 150): Requires only **10% collateral stake** (50% fee discount for proven creators).
  - **SILVER Tier** (Score 100 - 149): Standard baseline requiring **20% stake**.
  - **BRONZE Tier** (Score < 100): High-risk tier requiring **30% stake** to deter non-compliance and sybil spam.
- **New Public Smart Contract Methods**:
  - `get_creator_profile(creator: str) -> str`: Returns comprehensive on-chain reputation profile and current tier metadata.
  - `get_required_stake(campaign_id: str, creator: str) -> str`: Dynamically calculates the required stake in wei based on the creator's reputation tier.
- **Interactive On-Chain Reputation & Tier Registry (Frontend UI)**:
  - New dedicated dashboard tab **"⭐ Creator Reputation & Tiers"** allowing users and judges to inspect any creator wallet live on GenLayer.
  - Dynamic collateral calculation in the Creator Dashboard when reviewing and accepting campaign offers.
- **Dedicated Test Suite (`tests/test_reputation.py`)**:
  - 5 comprehensive unit tests verifying Gold tier qualification, Bronze tier penalties, dynamic stake calculation, and automatic reputation scoring upon payout/slashing.

- **Live Studionet Deployment**:
  - Successfully deployed to GenLayer Studio Network (`studionet`, Chain ID `61999`) at address `0x37F4206F9b910c06F517A258D28dCf744C0dfb3e`.
  - Verified on GenLayer Studio Explorer with full ABI and state inspectability.

### Improved
- Expanded test suite from 24 to 29 passing unit tests (100% pass rate in 0.27s).
- Line 1 pragma in `contracts/contract.py` unified to official `{ "Depends": "py-genlayer:..." }` magic comment for seamless GenLayer Studio compilation.

---

## [1.1.0] - 2026-09-23 - Milestone 1: UX Overhaul, Interactive Evidence Simulator & Security Architecture Suite

### Added
- **Interactive Consensus Simulator & Forensic Sandbox**:
  - Live interactive sandbox in the dApp allowing reviewers, judges, and users to test and visualize all 4 consensus execution paths (`Clean Release`, `Non-Inference Partial`, `Blacklist Refund`, `Trustless Fraud Slashing`) without needing testnet GEN or waiting for block mining.
  - Interactive Evidence Inspector displaying the distinction between Structured Authenticated Evidence (`author_metadata`, `captions`, `visual_proof`) vs Raw Unauthenticated Scraped Text.
  - Multi-Agent Consensus Voting Visualizer demonstrating how GenVM leader and validator nodes agree on subjective meaning while ignoring cosmetic wording discrepancies.
- **Creator Trust Profile & Reputation Metrics**:
  - Creator trust score calculation and badge indicators (`Verified Handle`, `Zero-Dispute Escrow Partner`, `Skin-in-the-game Staker`).
- **Live On-Chain Network & Explorer Widget**:
  - Real-time network telemetry showing Chain ID `61999` (`studionet`), RPC health, and one-click deep links to GenLayer Studio Explorer for the live contract `0x4c79bC7e88642625f677AFDc6d593048875065C5`.
- **Comprehensive Developer & Security Documentation Suite**:
  - `ARCHITECTURE.md`: Complete system architecture, Mermaid sequence and state machine diagrams, and GenVM equivalence principle implementation details.
  - `SECURITY.md`: Detailed adversary threat model, 5 core invariant defenses, and 24-test verification matrix.
  - `CHANGELOG.md`: Standardized release documentation.

### Improved
- **User Interface & Navigation**:
  - Added dedicated navigation tabs (`Consensus Simulator ⚡`, `Explore KOLs`, `Open Campaigns`, `Brand Dashboard`, `Creator Studio`).
  - Polished responsive layouts, status badges, toast feedback, and cooling-off countdown explanations.
  - Strengthened RPC retry mechanisms with exponential backoff to ensure smooth interaction during peak network load.

### Verified
- 100% test pass rate across 24 pytest adversarial regression tests and 14 Node.js simulation tests.
- Live deployment verified on Vercel production and connected to GenLayer Studio contract `0x4c79bC7e88642625f677AFDc6d593048875065C5`.

---

## [1.0.0] - 2026-09-16 - Initial Release
- Core Intelligent Contract with `gl.vm.run_nondet` equivalence principle consensus.
- Canonical Hostname verification and On-Chain Handle Registry.
- Non-Inference Rule for visual frame proofs.
- Safe Stake Decoupling and Ownerless Multi-Agent Dispute Slashing.
- 30-Day Stale Dispute Recovery protocol.
- Full frontend dApp deployed to Vercel and GenLayer Studio Network.
