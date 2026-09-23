# Changelog

All notable changes to the AffiliateGuard project are documented in this file in accordance with [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
