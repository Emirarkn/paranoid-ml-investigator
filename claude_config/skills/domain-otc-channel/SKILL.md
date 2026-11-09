---
name: domain-otc-channel
description: OTC (over-the-counter) / consumer health channel pack. Loaded only AFTER the profile confirms the project is in this domain. Covers data types along the manufacturer → wholesaler → pharmacy/retail → consumer chain (sell-in, sell-out, stock, promotions, price), channel-specific failure families, and how to test them with pmi. Do not use if the project is not in this domain.
---

# Domain pack: OTC channel

This pack does not replace the core; it adds a **knowledge layer** on top of it. Core rules (profile confirmation, pre-registration, status protocol) still apply.

## When to load
Only after `business_context` or `unit_of_analysis` is confirmed and it is clear the project really is a channel/distribution forecast. A column name containing "sell_in" is not enough evidence. Ask the user.

## Channel model (general)
```
Manufacturer ──sell-in──► Wholesaler / distributor ──(depot outflow)──► Pharmacy / retail ──sell-out / offtake──► Consumer
                ▲ orders, promotion loading                ▲ channel stock                          ▲ true demand (often unobserved)
```
Learn **from the project** which arrow is measured. The same name (e.g. "sales") can map to different arrows in different projects.

## Profile mapping (add to the confirmation package)
| Channel concept | Generic profile field | Question for the human |
|---|---|---|
| What is forecast (sell-in, sell-out, demand?) | `target` + `business_context` | "Which decision does this forecast feed: production/import, wholesaler loading, or pharmacy availability?" |
| Product × wholesaler / region / pharmacy | `entity_keys` | Is the aggregation level the same as the decision level? |
| Period (often month or week) | `time_column`, `time_grain` | Learned from the data. Do not assume. |
| Stockout flag, channel days of cover | `feature_availability` | Is this information available at prediction time? |
| Promotion calendar, price changes | `feature_availability` | Is the promotion decision final before the forecast is made? |
| Panel / market data | `feature_availability` | With how many periods of delay does it arrive? |

## OTC-specific hypothesis families
Details and tests: `references/otc-failure-catalog.md`. Priority order:
1. **Proxy target:** sell-in modelled as "demand".
2. **Censored demand:** sales during stockout periods are a lower bound of demand.
3. **Channel stock waves:** loading before a price increase or promotion, depletion afterwards.
4. **Delayed information:** panel and sell-out data arrive late but are used in the model as if known at prediction time.
5. **Seasonality and epidemiology:** seasons such as cold & flu or allergy shift from year to year; success in a single season is not generalisation.
6. **Returns and expiry:** negative or correction rows distort the target.
7. **New products and cannibalisation:** products without history quietly worsen the aggregate metric.

## Testable with today's pmi
- Delayed information → `amplify time_lag` (panel/sell-out features), `check target_proxy` (future lag)
- Random split on a monthly panel → `check temporal_overlap`, `check static_patterns`
- Promotion and price feature dependency → `ablation`
- Missing sell-out reporting → `amplify missing` (sell-out features)
- Key uniqueness (product × wholesaler × period) → `check key_uniqueness`

## Not testable yet (register as Suspected, report "no tool")
Amplifying censored demand, channel stock simulation, service-level and lost-sales impact. These arrive with the **channel consequence simulation** in stage 5 (`domain_packs/otc_channel/README.md`).

## Prohibitions
- Never invent or carry over company, brand or product names from other projects. Use only names seen in the project.
- Never substitute industry "common knowledge" (e.g. "sales rise in winter") for evidence. Show it in the data or register it as a hypothesis.
