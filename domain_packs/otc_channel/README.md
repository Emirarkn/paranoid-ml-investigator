# Domain pack: OTC channel

A specialisation layer for over-the-counter (OTC) and consumer health products: it audits forecasting projects along the manufacturer → wholesaler/distributor → pharmacy/retail → consumer chain.

## Contents today (v0.1)
- **Agent skill:** `claude_config/skills/domain-otc-channel/`. Channel model, profile mapping, 9 failure families (O1–O9) and how to test them with pmi.
- **Benchmark:** `examples/make_examples.py` → `otc_channel` project. Monthly `yyyymm` periods, a product × wholesaler panel, sell-in/sell-out and a stockout flag, with real defects and decoys embedded.
- **No real data.** Everything in this pack is general channel knowledge and synthetic data. It is not based on any company, brand or internal data.

## Stage 5 design: channel consequence simulation
Goal: show, scenario by scenario, how forecast error propagates to later periods and through the channel. Example chain: under-forecast → too little sell-in → wholesaler stock drops → pharmacy stockout → observed sell-out drops → the next forecast stays too low.

Design principles:
1. **Parameters are learned, not assumed.** Ordering policy, lead time, target days of cover, minimum order quantity and costs enter a new profile section (`consequence_params`) with evidence and human confirmation. If a parameter is missing, the simulation does not run.
2. **Three scenarios** (design document §6): A = no intervention, B = amplified failure (uses pmi amplify results as input), C = corrected system (output of the stage 6 counterfactual).
3. **Demand uncertainty:** Monte Carlo ranges instead of a single result (seeded demand scenarios).
4. **Outputs:** number of stockout periods, lost sales (as a range), excess stock, holding cost, misallocation across wholesalers, bias per SKU, service level.
5. **Status:** all results are at most `Simulated` and carry the label "scenario conditional on assumptions" in the report.
6. **Feedback loop:** sell-out observed during a stockout enters the next period's training data as censored. The simulator models this explicitly (O2).

## Roadmap
- [ ] `consequence_params` profile section and confirmation flow
- [ ] Two-tier wholesaler-pharmacy stock simulator
- [ ] Censored-demand injector: scales stockout duration and the number of affected entities
- [ ] Segment metrics (new products, season, wholesaler)
- [ ] Walk-forward backtest (1/3/6/12 period horizons)
