# PARANOID ML INVESTIGATOR
## Autonomous ML/AI Failure Discovery, Amplification & Consequence Analysis System

**Project type:** AI Agent / ML Auditing / Adversarial Testing

**Document:** System Design Report and Development Roadmap

**Version:** 1.0 — November 2026

**Goal:** Build a quality-control and investigation system that runs locally and can be reused across different ML/AI projects.

---

# 1. Executive Summary

Paranoid ML Investigator is an AI agent system designed to independently examine machine learning, deep learning, forecasting and artificial intelligence projects.

Traditional code review tools focus on detecting existing bugs and known software problems. This project investigates a further question:

**"We think this system works correctly. If which assumptions are wrong, under which conditions or after which changes does it fail?"**

The agent does not only report errors. It investigates how errors arise, questions hidden assumptions, designs controlled experiments and amplifies problems to determine the model's robustness limits.

For example, if the missing-observation rate in a dataset is 5%, it examines how the model behaves when it is 10%, 15% and 25%.

It also simulates what the problems found could turn into in the future. It calculates the possible effects of wrong forecasts on stock decisions, costs and later periods.

The core approach of the system:

**Discover → Challenge → Amplify → Experiment → Verify → Predict Consequences → Repair → Retest**

The goal is not to invent as many bugs as possible. The goal is to surface important weaknesses with evidence and increase the reliability of the system.

# 2. Problem Definition

Failures in ML and AI projects do not stem only from choosing the wrong algorithm.

Structural errors can arise while preparing data, defining the target variable, training the model, measuring performance and transferring results into business processes.

For example, a model showing high accuracy may harbour the following problems:

- Future information accidentally included in the training data.
- Missing, erroneous or biased data.
- Optimisation metrics misaligned with the business goal.
- The model learning coincidental correlations instead of the relationship it should learn.
- Differences between training and real-world usage conditions.
- Missing evaluation scenarios.
- Small data corruptions turning into large forecast errors.
- Unverified results presented as definite facts in LLM-based components.

Some existing testing approaches rely on predefined checklists.

The key difference of Paranoid ML Investigator is that it also develops failure hypotheses that were not written in advance and tests them with experiments.

# 3. How the Agent Works

The system's behaviour should resemble that of a scientific researcher.

It must first understand the existing project, then generate alternative hypotheses explaining the model's success.

For example, a low error rate in a forecasting model does not necessarily mean it is truly successful.

The agent may investigate questions such as:

"Did the model learn from past data, or did it accidentally use information about the future?"

"Does the high forecast accuracy occur only for certain SKUs?"

"Could it be learning sales that occurred while stock was unavailable as true demand?"

"Does the model's success depend on promotion periods being coded incorrectly?"

For each hypothesis the following loop is followed:

1. State the hypothesis explicitly.
2. Design a counter-test that could show the hypothesis is false.
3. Run the test in an isolated environment.
4. Compare the baseline and experiment results.
5. If there is evidence, confirm the finding; if not, classify it as suspected or rejected.
6. Move the confirmed problem to an impact amplification test.
7. Propose a solution and question the solution itself.

**The agent being skeptical does not mean its findings are definitely correct.**

Therefore the agent's claims and the experiment results measured in Python must be kept separate.

# 4. System Architecture

The system will consist of three main layers.

## Layer A — Intelligence Layer

This layer carries out LLM-supported reasoning and investigation.

**Project Understanding Module**

Examines the project's source code, folder structure, data files, model training processes, configurations and existing performance reports.

The goal is to understand which outputs the model produces from which inputs.

**Skeptical Hypothesis Engine**

Investigates logical gaps, hidden dependencies and failure possibilities that may exist in the project.

For each suspicion it produces a reason, an expected effect and a verification method.

**Experimental Planner**

Turns a hypothesis into an executable test.

Defines which parameter will be changed, which files will be used and which failure criteria will be evaluated.

## Layer B — Experimental Harness

This is the part where test results are produced by real code, not merely interpreted by the LLM.

**Structural Auditor**

Investigates inconsistencies in data schemas, formulas, code dependencies, time ordering, target-variable definitions and evaluation methods.

**Fault Injection Engine**

Removes, delays or corrupts data in a controlled way, or applies scenario changes.

**Failure Amplification Engine**

Measures the model's robustness by taking the severity of the problem to 1×, 2×, 3× and 5× levels.

**Backtesting Engine**

Re-evaluates models in past periods using the information that was actually available at that time.

**Consequence Simulation Engine**

Simulates how forecast errors may spread to later periods and into business processes.

**Evidence Verification Engine**

Recomputes results, compares evidence and separates findings that cannot be verified.

## Layer C — Decision & Reporting Layer

**Root Cause Analyzer**

Explains the root cause of a finding. Separates the symptom from the root cause.

**Solution Planner**

Defines fix options, their expected benefits and possible side effects.

**Counterfactual Tester**

Evaluates, under the same test conditions, how the results would change if the proposed fix had been applied.

**Report Generator**

Turns all experiments into an understandable, evidence-based report.

---

# 5. Failure Amplification Engine

This engine is the system's key differentiator.

## 5.1. The amplification principle

The agent first measures the baseline level of a problem.

Then it increases the problem in a controlled way and measures the model's response.

Example:

5% of a dataset has missing stock information.

| Experiment | Missing data | Problem severity |
|---|---:|---:|
| Baseline | 5% | 1× |
| Test A | 10% | 2× |
| Test B | 15% | 3× |
| Test C | 25% | 5× |

Important point: **The error rate is not automatically doubled or tripled. The condition that causes the error is amplified.**

For example, while missing data grows 3×, the forecast error may grow 1.4×, 2.8× or 5×. The system discovers this relationship experimentally.

Core measure:

**Error Amplification Factor = Stress Test Error / Baseline Error**

For example, if baseline WAPE is 12% and stress-test WAPE is 30%:

**Error Amplification Factor = 2.5×**

This shows the model's sensitivity to the corresponding data corruption.

Unless test results are produced from real data, they are marked as hypothetical.

## 5.2. Problem categories to amplify

Not every error can be amplified the same way. The Fault Injection Engine must therefore choose a strategy suited to the problem type.

| Problem | Amplification method |
|---|---|
| Missing data | Increase the share of missing records |
| Outlier | Increase the number or magnitude of outliers |
| Data leakage | Change the scope of information coming from the future |
| Feature dependency | Remove critical variables one by one |
| Stockout | Increase outage duration and number of affected products |
| Data drift | Shift the data distribution in a controlled way |
| Model bias | Change the data representation of specific subgroups |
| Formula error | Test the wrong formula with inputs of different sizes |
| LLM hallucination | Increase the number of ambiguous, contradictory or under-evidenced tasks |

Where possible, tests should stay within realistic bounds.

If a parameter cannot be amplified 5×, the system must state that a physical or logical limit was exceeded.

## 5.3. Failure Threshold Discovery

This feature will investigate at which point the model becomes unreliable.

For example:

- At what level of missing data does WAPE become unacceptable?
- After how many periods of stock outage does the model systematically under-forecast?
- At what level of data drift does prediction-interval coverage drop?
- Which SKUs fail before the others?

A robustness profile will be derived from these results.

**The goal is not only to show the error, but to determine under which conditions it becomes critical.**

# 6. Consequence Simulation Engine

This engine analyses what may happen in later stages if an error is not fixed.

For example, consider systematic under-forecasting in a demand forecasting model.

Possible process:

**Under-forecast demand → too little sell-in planned → insufficient warehouse stock → stockout → low realised sell-out → new bias in subsequent forecasts**

This loop does not have to occur in every condition. Whether it does depends on stock policy, lead time, demand, ordering decisions and other business rules.

Therefore the engine must first define its cause-effect assumptions explicitly.

It will then create three different scenarios.

**Scenario A — No Intervention**

The problem is not fixed and the current system continues.

**Scenario B — Amplified Failure**

The problem reaches 2×, 3× or higher severity.

**Scenario C — Corrected System**

The proposed intervention is applied and the results are re-simulated under the same conditions.

If business data is sufficient, 3-, 6- and 12-month effects can be calculated.

Example outputs:

- Expected excess stock.
- Number of periods with stockouts.
- Possible lost sales quantity.
- Stock holding cost.
- Quantities misallocated between warehouses.
- Forecast bias per SKU.
- Effects on service level.

These future values are not definite results but assumption-dependent scenarios.

If demand uncertainty exists, outcome ranges should be produced with different demand scenarios or Monte Carlo simulations instead of a single result.

# 7. Evidence & Hallucination Control

This is the system's most important reliability mechanism.

To prevent the agent from producing imaginary problems while searching for problems, every claim will have an evidence status.

| Status | Meaning |
|---|---|
| Verified | Confirmed with real code, data or a reproducible experiment |
| Suspected | Plausible hypothesis, insufficient evidence |
| Simulated | Observed only under controlled experimental conditions |
| Rejected | The experiment did not support the hypothesis |
| Inconclusive | Test result insufficient for evaluation |

Every finding must contain at least the following information:

**Finding ID, problem description, source file/line, affected data, hypothesis, test procedure, baseline measurement, experiment measurement, evidence file, uncertainty and proposed fix.**

In addition, there will be tests that investigate the agent's own hallucinations.

Examples:

- Claiming that a function not present in the source code exists.
- Giving a performance result for a test it did not run.
- Presenting a simulation result as real production data.
- Interpreting correlation as proven causation.
- Producing references to wrong or non-existent file lines.
- Saying performance improved without a fix having been made.

**Reporting rule:** No claim without evidence can move to Verified status.

Important findings must go through an independent calculation or a second evaluation stage.

# 8. Technical Architecture and Technology Choices

The first version should be developed as a locally running Python application.

A web interface, cloud infrastructure or multi-agent organisation is not required at the start.

| Component | Recommended technology |
|---|---|
| Core language | Python |
| Agent orchestration | Python state machine at first; LangGraph if needed |
| LLM connection | Swappable model adapter |
| Local LLM option | Ollama |
| Data processing | pandas, NumPy |
| Modelling and testing | scikit-learn, statsmodels |
| Forecast backtesting | MLForecast or custom rolling-origin tests |
| Data quality checks | Great Expectations / Evidently |
| Automated tests | pytest |
| Experiment records | SQLite + JSON/Parquet |
| Report | Markdown + HTML |
| Versioning | Git |

**Our own harness will be the core system; open-source libraries will be used only as calculation and checking tools.**

## 8.1. Proposed repository structure

Project name: `paranoid-ml-investigator`

- `src/core/`: Orchestration, state management, operating rules.
- `src/agents/`: Project analyzer, hypothesis investigator, solution planner.
- `src/auditors/`: Data, code, model and evaluation audits.
- `src/amplification/`: Fault injector, severity controller, threshold detector.
- `src/simulation/`: Consequence simulator, inventory simulator, scenario manager.
- `src/verification/`: Evidence verification, metrics, repeat experiments.
- `src/reporting/`: Report generation, finding records.
- `src/adapters/`: LLM, model, data and forecasting framework connections.
- `config/`: Agent policies, failure levels, test budgets.
- `tests/`: Unit, integration, adversarial and hallucination tests.
- `examples/`: Synthetic forecasting and ML projects.
- `runs/`: Experiment results, logs and reports.

This separation keeps the agent's reasoning mechanism loosely coupled from the computation engines.

## 8.2. Harness operating rules

The harness must enforce the following safety and correctness rules:

- Original project files must be read-only from the start.
- Tests must run in separate working folders.
- Allowed commands and resource limits must be defined for code that will be executed.
- Network access must be fully closed if necessary.
- All data changes must be recorded.
- The random seed, model version and parameters of each experiment must be stored.
- Training and test periods must not be mixed.
- Features that would not be known in the future must not be used at test time.
- The agent must not automatically push model changes to production.
- The process must stop when a defined run time, number of experiments or cost limit is reached.

# 9. Roadmap — Development Stages

The roadmap is divided into eight stages. A working core system will be built in the first stages, and more complex capabilities will be added on top of it.

| Stage | Development | Concrete output |
|---|---|---|
| 1 | System contract and repo infrastructure | Working Python project skeleton |
| 2 | Project intelligence and data audit | Auditor that analyses files |
| 3 | Hypothesis & evidence system | Hypothesis records linked to evidence |
| 4 | Failure amplification | 1×, 2×, 3×, 5× stress tests |
| 5 | Consequence simulation | Future impact scenarios |
| 6 | Solution & counterfactual | Before/after intervention comparison |
| 7 | Agent hallucination & red teaming | Tests that catch false claims |
| 8 | Integration and quality control | Usable, reproducible MVP |

## Stage 1 — Foundation

First, project standards are defined.

Input types, supported model families, safety limits, the finding record schema and output formats are determined.

A sample project must be scannable with a single command.

**Acceptance criterion:** The system must be able to read files safely, produce a project inventory and modify no original file.

## Stage 2 — Structural Intelligence

The agent analyses the project structure, data flow and model training logic.

The first version should support Python files, CSV/Excel data, model configurations and performance outputs.

**Acceptance criterion:** The target, features, data period, model and evaluation method used must be identified correctly.

## Stage 3 — Hypothesis Engine

The agent generates suspicions, but must also explain how each hypothesis will be tested.

In the first version a limited number of prioritised hypotheses is run.

**Acceptance criterion:** Suspected, verified and rejected hypotheses must not be mixed.

## Stage 4 — Amplification MVP

Start with three failure families:

1. Missing data amplification.
2. Outlier / distribution shift amplification.
3. Forecast feature and timing corruptions.

Stockout, leakage and combined failure scenarios are added later.

**Acceptance criterion:** Experiments of different severity on the same model must run automatically, the change in error must be calculated correctly, and the results must be reproducible.

## Stage 5 — Consequence Engine

First, a simple stock simulation specific to forecasting is developed.

The relationship between forecast output, ordering plan and stock movements is defined.

**Acceptance criterion:** No-intervention and corrected scenarios must be comparable under the same assumptions.

## Stage 6 — Repair & Retest

The agent proposes a solution and the proposed fix is applied in an isolated environment.

The corrected model is compared with the original model under the same temporal evaluation conditions.

**Acceptance criterion:** If fixing one problem causes serious degradation in another SKU, period or performance metric, the report must show it.

## Stage 7 — Agent Red Team

The agent is deliberately given incomplete documents, misleading metrics, fake error hints and broken file references.

The goal is to find when the agent itself becomes unreliable.

**Acceptance criterion:** The agent must not present experiments it did not run as if they were run, and must explicitly mark unknown or unverifiable information.

## Stage 8 — Production Hardening

In the final stage, code organisation, traceability, performance, error handling and report clarity are evaluated.

Recovery mechanisms are added for large files, failed experiments and interrupted runs.

**Acceptance criterion:** When the user provides the same input and the same experiment settings, they must obtain the same numerical test results. LLM interpretations may vary, but evidence records must not change.

# 10. First Pilot: Demand Forecasting

The first real application area should be a product- and month-level demand forecasting project.

Example inputs:

- Historical sell-out.
- Sell-in by product/warehouse.
- Stockout periods, if known.
- Stock and promotion information.
- The model code used.
- Past forecasts and actuals.
- Existing performance reports.

The agent first independently evaluates the existing model's accuracy over past periods.

It then investigates the following questions:

**A. Can the model really predict the future?**

A rolling-origin backtest is applied. In particular, 1-, 3-, 6- and 12-month forecast horizons are separated.

**B. Have sales and demand been confused?**

It investigates whether sales realised during stockout periods understate true demand. If true demand cannot be observed directly, this is stated explicitly.

**C. Is the sell-in / sell-out relationship set up correctly?**

The relationship between warehouse loadings and sales in the following months is examined. The possibility that sell-in is mistakenly used instead of realised consumer demand is tested.

**D. Under which conditions does the model fail?**

Stress tests are applied by increasing anomalies, stock outages, missing data and large volume changes.

**E. How do errors reflect on planning?**

Effects on stock availability, excess stock, lost sales and next-period forecasts are calculated scenario by scenario.

At the end of the first pilot, the following outputs should be produced at SKU and month level:

- Baseline forecast.
- Baseline WAPE, MAE, Bias and other appropriate metrics.
- The most important verified problems.
- Amplification experiments and error sensitivity curves.
- Critical failure thresholds.
- No-intervention and corrected scenarios.
- Solution proposals and retest results.

# 11. Success Criteria

The system should not be evaluated only by the number of problems it finds.

Success should be measured along five separate dimensions.

**Detection Quality:** How many of the deliberately created problems can it find?

**False Positive Control:** How often does it report problems that do not exist as verified?

**Evidence Reliability:** Is every important finding supported by real tests and file records?

**Experiment Reproducibility:** Can numerical experiments be reproduced under the same conditions?

**Remediation Quality:** Do the proposed fixes really deliver improvement on independent evaluation data?

Synthetic projects with known errors should be prepared as the initial benchmark.

For example, 20 controlled problem scenarios could be created. Some should be real errors, others misleading but error-free scenarios.

The agent's success at telling them apart is measured.

MVP acceptance thresholds should be decided based on the first benchmark results; no success rate should be promised before experiments are done.

# 12. Risks and Controls

**Risk 1 — Over-skepticism**

Because the agent looks for problems everywhere, it may produce false findings.

Control: Evidence statuses, independent verification and recording of rejected hypotheses.

**Risk 2 — Unrealistic amplification**

A 5× corruption may create a scenario that is impossible in real life.

Control: The realism level, assumptions and physical limits of each experiment are reported.

**Risk 3 — Overfitting to test data**

While trying many fixes, the agent may indirectly use the test data for optimisation.

Control: Development backtests and the final independent evaluation period are separated. The final evaluation data is frozen in advance.

**Risk 4 — Wrong causality**

The fact that forecast error rises as a variable increases does not always prove a real-world cause-effect relationship.

Control: Controlled interventions, alternative explanations and causal assumptions are documented explicitly.

**Risk 5 — Uncontrolled agent behaviour**

The agent may break the project, run wrong commands or export sensitive data.

Control: Local sandbox, allowed tools, read-only sources, network restrictions and human approval.

# 13. Final Product Vision

When the project is complete, the goal is for the user to be able to start an audit simply by selecting an ML/AI project.

Example usage:

**User:** "Audit this forecasting project. Find the errors, apply 2× and 3× stress tests and show the possible effects on the 12-month stock plan."

**Agent:** Scans the project, prioritises hypotheses, runs experiments, verifies findings and turns the results into an explainable report.

**User:** "Try fixing the two most critical problems."

**Agent:** Applies the fix in a separate environment, re-measures model performance, examines side effects and produces a comparative result.

In the long term the system can be extended to:

- Regression and classification models.
- Deep learning.
- Time-series forecasting.
- Optimisation algorithms.
- LLM-based applications.
- RAG systems.
- AI agent and multi-agent architectures.

## Final Architecture Decision

**A custom agent harness will be built from scratch, but statistical testing and data processing libraries will not be rewritten.**

The first version will have a single orchestrator agent, independent Python modules, an isolated experiment environment and an evidence recording system.

A multi-agent architecture, a visual interface and more complex automation will be added only after the first core system has been successfully validated.

The central principle of the project:

**Assume nothing. Challenge everything. Amplify weaknesses. Verify the evidence. Predict the consequences. Test every fix.**
