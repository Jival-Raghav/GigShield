<div align="center">

<img src="assets/hero-banner.svg" alt="GigShield by InsureEase" width="100%"/>

</div>

---

## 📋 Table of Contents

**Story Layer** *(start here)*
- [The Problem](#-the-problem)
- [Why Now](#-why-now)
- [Meet the Workers](#-meet-the-workers)
- [How GigShield Works](#-how-gigshield-works)
- [Use Case Overview](#-use-case-overview)
- [AI/ML Integration](#-aiml-integration)
- [What Makes Us Different](#-what-makes-us-different)
- [vs Existing Solutions](#-vs-existing-solutions)
- [Parametric Triggers](#-parametric-triggers)
- [Feasibility](#-feasibility)
- [Tech Stack & Development Plan](#-tech-stack--development-plan)
- [2-Minute Video](#-2-minute-video)

**Implementation Detail** *(for judges who dig)*
- [Part 1 · Baseline Income Estimation](#part-1--baseline-income-estimation)
- [Part 2 · Disruption Risk Modelling](#part-2--disruption-risk-modelling)
- [Part 3 · Dynamic Premium Pricing](#part-3--dynamic-premium-pricing)
- [Part 4 · Validation, Payout & Trust](#part-4--validation-payout--trust)
- [Known Issues & Mitigations](#known-issues--mitigations)
- [Team](#-team)

---

## ❌ The Problem

India's 15M+ gig delivery workers have no income protection when floods, heavy rain, curfews, or extreme weather stop them from working. Traditional insurance is slow, manual, and rejects claims without clear reasons.

<img src="assets/before-after.svg" alt="Before and after comparison" width="100%"/>

> *15 million gig workers. Zero income protection when external disruptions hit.*

---

## ⏳ Why Now

<img src="assets/why-now.svg" alt="Why now - 4 key stats" width="100%"/>

The convergence of a growing gig workforce, increasing climate volatility, real-time public APIs, and India's instant UPI payment rails makes this the right moment to build parametric income insurance for delivery workers.

---

## 👤 Meet the Workers

<img src="assets/personas.svg" alt="Ravi, Priya and Suresh - three delivery worker personas" width="100%"/>

> *Three different workers. Three different situations. One system that handles all of them fairly.*

**Ravi** shows the happy path — legitimate flood claim, full proportional payout.
**Priya** shows cold start handling — brand new worker gets peer averages, zero penalties.
**Suresh** shows our anti-gaming approach — suspicious pattern detected, payout scaled down proportionally rather than rejected outright.

---

## ⚙️ How GigShield Works

<img src="assets/system-pipeline.svg" alt="GigShield 4-module pipeline" width="100%"/>

**🔵 Part 1 — Baseline Income: What should you have earned?**

We look at your recent earnings, remove any days where disruptions already happened, and reconstruct what a genuinely normal week looks like for you. New workers are compared to similar riders in their zone until they build enough personal history. This becomes your counterfactual income — the anchor for every payout calculation downstream.

→ [See baseline estimation implementation details](#part-1--baseline-income-estimation)

---

**🟣 Part 2 — Risk Modelling: How bad could this week get?**

Every Monday, we pull weather forecasts, AQI data, flood alerts, and local event calendars for your specific delivery zone. A machine learning model trained on years of historical disruptions predicts how many days are likely to be disrupted and how severe each one will be. High-data zones are ML-driven; new zones lean on historical risk patterns.

→ [See risk modelling implementation details](#part-2--disruption-risk-modelling)

---

**🟡 Part 3 — Premium Pricing: What's fair to charge?**

Your weekly premium is calculated from your expected income loss for that week, adjusted for your zone's risk level and platform. Workers with a strong trust history get a small discount. We build in actuarial margins to keep the platform solvent even during bad monsoon seasons — and zone-level community pricing prevents adverse selection spirals.

→ [See premium pricing implementation details](#part-3--dynamic-premium-pricing)

---

**🔴 Part 4 — Validation & Payout: Was the claim real?**

When disruption hits, we don't just ask "did it happen?" — we ask "how much did it affect this specific worker?" We check GPS location, activity levels compared to peers in the same zone, and historical behaviour patterns. Instead of rejecting ambiguous claims, we scale payouts proportionally. Honest workers get full payouts. Suspicious patterns reduce the payout gradually — with repeated gaming penalised more firmly over time.

→ [See validation and payout implementation details](#part-4--validation-payout--trust)

---

## 🗺️ Use Case Overview

<img src="assets/usecase-diagram.svg" alt="GigShield use case diagram" width="100%"/>

Three actor types interact with the system: **Workers** (register, pay premiums, receive payouts), the **GigShield Platform** (auto-detect, validate, calculate, pay), and **Insurers/Admin** (monitor dashboards, review flagged claims, track loss ratios).

---

## 🤖 AI/ML Integration

> *AI/ML isn't just used for prediction — it runs through every layer of the pipeline, from estimating what you should have earned to detecting when someone is gaming the system.*

| Module | ML Task | Model | Trained On |
|---|---|---|---|
| Baseline Estimation | Predict peer weekly income | XGBoost / Random Forest | Historical cleaned income, zone demand, calendar signals |
| Risk Modelling | Forecast disruption probability + severity | Gradient Boosting classifier | Weather signals, zone vulnerability, disruption history |
| Premium Pricing | Calibrate risk multiplier dynamically | Regression | Zone risk index, platform volatility, trust distribution |
| Claim Validation | Temporal consistency scoring | Sigmoid scoring function | Worker activity vs peer cluster behaviour |
| Anti-Gaming | Detect effort simulation | Rule-based + acceptance rate signal | Order acceptance patterns, online hours vs deliveries |
| Trust Scoring | Behavioural trust update | Asymmetric weighted moving average | BAF history, claim frequency, timing patterns |

---

## ✨ What Makes Us Different

<table>
<tr>
<td width="33%" valign="top">

### 🔄 Proportional, not binary

Most insurance says **yes** or **no**. We say **how much** — payouts are scaled to a worker's actual contribution during the disruption. An ambiguous case gets a partial payout, not a rejection letter.

</td>
<td width="33%" valign="top">

### 🧠 Behaviour-aware, not rule-based

We don't just check if rain happened. We check if rain affected **you specifically** — comparing your activity to peers in your exact zone and time slot at that moment.

</td>
<td width="33%" valign="top">

### 🤝 Trust builds over time

Good behaviour earns premium discounts. Gaming is penalised gradually across a 5-claim lookback window — never with sudden rejection. The system gets smarter the longer you use it.

</td>
</tr>
</table>

---

## 🆚 vs Existing Solutions

| Feature | Traditional Insurance | Existing Gig Products | **GigShield** |
|---|---|---|---|
| Claim process | Manual — forms + photos | Semi-manual | ✅ Fully automatic |
| Payout time | 2–3 weeks | Days | ✅ **< 2 hours** |
| Fraud handling | Reject | Reject | ✅ **Scale payout proportionally** |
| Personalisation | Low | Medium | ✅ **Hyperlocal + behavioural** |
| New worker support | None | None | ✅ **Cold start + peer baseline** |
| Gaming detection | None | Basic blacklisting | ✅ **Acceptance rate + trust scoring** |

---

## ⚡ Parametric Triggers

> *Payouts are triggered automatically based on real-world external signals — no manual claims required.*

| Trigger | Threshold | Data Source | Payout Effect |
|---|---|---|---|
| Heavy rainfall | Exceeds operational mm threshold | IMD API, OpenWeatherMap | Scaled to rainfall intensity |
| AQI spike | Exceeds health threshold | CPCB real-time API | Partial to full day loss |
| Flood / waterlogging alert | Active warning in worker's zone | NDMA, State disaster APIs | High severity — peer ratio excluded |
| Curfew / lockdown | Active government notification | Official government feeds | Full day — signal-dominant calculation |
| Platform outage | Confirmed downtime | Platform API / monitoring | Activity weight reduced in formula |
| Extreme temperature | Heatwave or dense fog advisory | IMD forecasts | Zone-level severity adjusted |

---

## 🔧 Feasibility

- All disruption signals (weather, AQI, flood alerts) are available via **free public APIs** — IMD, CPCB, NDMA, OpenWeatherMap
- Income data sourced via **platform API integrations** or self-reported worker logs during onboarding
- Risk models use **standard ML techniques** — XGBoost, Gradient Boosting, Logistic Regression — no unsolved research
- Real-time claim validation is achievable using **event-driven architecture** with sub-second signal processing
- Instant payouts use **existing UPI rails** — India's payment infrastructure handles this at scale today

| Data Need | Source | Availability |
|---|---|---|
| Rainfall / weather | IMD API, OpenWeatherMap | Free / public |
| AQI levels | CPCB real-time API | Free / public |
| Flood alerts | NDMA, state government APIs | Free / public |
| Worker income data | Platform API integration or self-reported | Partnership required |
| GPS location | Device GPS | Worker consent |
| Order acceptance rate | Platform API | Partnership required |

> *This system is engineering-heavy but uses well-understood components — making it confidently realistic to build within a startup or insurer ecosystem.*

---

## 🛠️ Tech Stack & Development Plan

**Stack**

| Layer | Technology | Purpose |
|---|---|---|
| Backend | Python / FastAPI | ML pipeline, API layer, validation engine |
| ML Models | XGBoost, Random Forest, scikit-learn | Risk forecasting, baseline estimation |
| Database | PostgreSQL + Redis | Claims, trust scores, real-time state |
| External APIs | IMD, CPCB, NDMA, OpenWeatherMap | Disruption signal sources |
| Payments | Razorpay / UPI | Mock in Phase 2, simulated live in Phase 3 |
| Frontend | React PWA | Worker dashboard + insurer admin panel |
| Infrastructure | AWS / GCP | Zone-level model serving |

**Platform choice: Progressive Web App, not native mobile**

Delivery workers switch phones frequently and app store installations create friction at onboarding. A PWA works on any Android browser, installs to the home screen in one tap, and supports low-connectivity zones via service workers — critical for workers in areas with poor signal during monsoon disruptions.

**Development Plan**

| Phase | Dates | Theme | Deliverables |
|---|---|---|---|
| **Phase 1** | Mar 4 – Mar 20 | Know Your Worker | README, system HLD, personas, pipeline architecture, 2-min video |
| **Phase 2** | Mar 21 – Apr 4 | Protect Your Worker | Worker registration + onboarding, insurance policy management, dynamic premium calculator, 3–5 parametric triggers via public APIs, claims management UI, 2-min demo video |
| **Phase 3** | Apr 5 – Apr 17 | Perfect Your Worker | Advanced fraud detection (GPS spoofing, fake weather claims), simulated UPI instant payout (Razorpay test mode), worker dashboard (earnings protected, coverage status), insurer admin dashboard (loss ratios, next-week risk forecast), full BAF pipeline, 5-min demo video, pitch deck |

---

## 🎥 2-Minute Video

> *(Link to be added — covers: problem statement, GigShield solution walkthrough, and the automated claim pipeline in action)*

[![Watch the video](https://img.shields.io/badge/▶%20Watch-2%20Minute%20Overview-red?style=for-the-badge)](YOUR_VIDEO_LINK_HERE)

---

---

# Implementation Detail

> *Everything above is the story. What follows is how we actually build it — the internal design of each module, the math behind the decisions, and the trade-offs we made consciously.*

---

## Part 1 — Baseline Income Estimation

**Objective:** Estimate the counterfactual weekly income a worker would have earned if no disruptions had occurred. This is the financial anchor for all downstream payout calculations.

**The core challenge:** Historical income data contains disrupted days. Averaging directly produces a downward-biased baseline. We reconstruct clean income by removing disrupted days and normalising for the composition of days removed.

**How it works in plain English:**
1. Label each historical day as disrupted or clean using external signals only
2. Keep only clean days and reconstruct what a full week should look like using learned day-weight patterns from the worker's peer cluster
3. New workers use peer cluster averages, transitioning to personal history over 8 weeks
4. A regression model predicts next week's peer income as the anchor

<details>
<summary>📐 See full technical specification</summary>

**Disruption Day Detection**

Each calendar day is labelled using external signals only — never income data (prevents circular dependency):

```
disruption_day = 1  (disrupted)  |  0  (clean)

Signals: rainfall threshold, AQI threshold, flood alerts,
         curfew notices, platform outages, extreme temperature
```

**Day-Aware Normalisation**

```
clean_daily_income = income where disruption_day == 0

expected_week_income =
    sum(clean_daily_income / day_weight[day])
    × sum(day_weights for available working days only)

day_weight[day] = learned from peer cluster historical
                  demand distribution per zone, platform, season
```

**Availability Bias Fix**

Worker availability schedules declared at onboarding constrain which days are reconstructed. Days the worker simply chose not to work are excluded from reconstruction — preventing overestimation for part-time workers.

**Edge Cases**

```
if clean_days < 3 in a week:
    fallback → peer cluster baseline

if clean weeks < 4 in rolling 8-week window:
    automatically widen to 12-week window
```

**Worker Productivity Factor**

```
worker_factor = avg(worker_income_last_8_weeks) /
                avg(peer_income_last_8_weeks)

New workers (tenure < 8 weeks):
    baseline_income = peer_baseline × min(tenure_weeks / 8, 1.0)
```

**Regression Model Features**

- week_of_year, month, weekend_count_in_week
- rolling_peer_income_last_4_weeks
- festival_or_holiday_flag
- zone_demand_index_last_2_weeks

**Output**

```json
{
  "baseline_income": 4200,
  "confidence": 0.85,
  "data_source": "individual"
}
```

</details>

---

## Part 2 — Disruption Risk Modelling

**Objective:** Forecast the expected number of disrupted days and expected severity per disrupted day for the upcoming week to compute expected loss for premium pricing.

**Key design decision:** We model expected disrupted days (not binary probability) — correctly handling weeks where Monday floods and Thursday curfews both affect the same worker.

<details>
<summary>📐 See full technical specification</summary>

**Expected Loss Formula**

```
expected_loss = min(
    baseline_income
    × E(disruption_days)          ← expected days disrupted
    × E(severity_per_day)         ← fraction of daily income lost
    × coverage_ratio,
    max_weekly_coverage            ← insurer viability cap
)

E(disruption_days) = min(ML_predicted, expected_work_days)
```

**Dual Label Versioning — Breaking Circular Dependency**

```
Version A labels → baseline income cleaning (standard threshold)
Version B labels → risk model training (stricter — confirmed severe only)

Severity reference = peer cluster avg income on clean days
                     NOT individually predicted baseline
                     (further breaks the circular dependency)
```

**Hybrid Risk Model**

```
P(disruption_next_week) =
    ML_prediction × α  +  historical_risk × (1 − α)

α = calibrated on held-out validation set

Historical risk: exponential decay weighting over years
                 (recent data weighted higher — climate drift)
```

**ML Features:** Rainfall forecast + intensity, consecutive rainy days, ground saturation proxy (7-day cumulative), AQI forecast, zone flood vulnerability score, road quality index, platform outage history, festival flags, monsoon phase, days since last disruption.

**Severity Levels**

| Severity | Example Event | Income Loss |
|---|---|---|
| Low | Light rain, minor congestion | ~20% |
| Medium | Heavy rain + local flooding | ~50% |
| High | Floods, curfew, full zone closure | ~90% |

**Output**

```json
{
  "E_disruption_days": 2.1,
  "E_severity_per_day": 0.50,
  "confidence": 0.80,
  "risk_source": "hybrid"
}
```

</details>

---

## Part 3 — Dynamic Premium Pricing

**Objective:** Translate expected loss into a weekly premium that is affordable, commercially sustainable, and dynamically adjusted for individual risk profile.

**Plain English:** Your premium is recalculated every Monday. It's based on how much you're expected to lose that week, adjusted for your zone's risk and your own trust history. We build in margins to keep the platform solvent — and zone-level pricing prevents only high-risk workers from buying coverage.

<details>
<summary>📐 See full technical specification</summary>

**Premium Formula**

```
weekly_premium =
    (expected_loss / coverage_ratio)
    × (1 + loading_factor)         ← 30–45% actuarial margin
    × risk_multiplier              ← zone × platform (capped at 2.0×)
    × trust_discount               ← 0.94–1.04 based on trust score

target_loss_ratio = 60%–70%
```

**Loading Factor Breakdown**

| Component | Contribution |
|---|---|
| Claims handling + operations | 8–10% |
| Reinsurance cost | 10–12% |
| Adverse selection buffer | 5–8% |
| Profit margin | 5–10% |
| **Total** | **28–40% (capped at 45%)** |

**Adverse Selection Control**

Zone-level community pricing: all workers in a micro-zone pay the same base premium. This prevents self-selection by individual risk awareness and breaks the adverse selection spiral.

```
risk_multiplier = min(
    zone_risk_index × platform_volatility_index,
    2.0    ← hard cap — affordability floor
)
```

**Coverage Tiers**

| Tier | Coverage Ratio | Max Weekly Payout | Target Worker |
|---|---|---|---|
| Basic | 50% | ₹2,000 | New workers, low-income zones |
| Standard | 70% | ₹3,500 | Established workers |
| Premium | 90% | ₹5,000 | High-income, high-tenure workers |

**Trust Discount**

```
trust_discount = 1 - (trust_score - 0.6) × 0.1

trust_score 0.6 → no change (1.00×)
trust_score 0.8 → 2% reduction (0.98×)
trust_score 1.0 → 4% reduction (0.96×)
trust_score 0.4 → 2% surcharge (1.02×)
```

</details>

---

## Part 4 — Validation, Payout & Trust

**Objective:** Validate claims in real time, compute proportional payouts adjusted for observed worker behaviour, update trust scores, and route for payment or audit.

**Core philosophy:** Replace binary fraud rejection with proportional fairness. Scale payouts by a Behaviour Adjustment Factor (BAF) that reflects the worker's actual contribution during the disruption.

**Claim Validation Flow**

<img src="assets/activity-claim.svg" alt="Claim validation activity diagram" width="100%"/>

**Worker Trust Lifecycle**

<img src="assets/state-trust.svg" alt="Worker trust state diagram" width="100%"/>

**The 2-Hour Payout — End to End**

<img src="assets/sequence-payout.svg" alt="Disruption to payout sequence diagram" width="100%"/>

<details>
<summary>📐 See full technical specification</summary>

**Temporal Consistency Score**

```
behavior_drop_ratio =
    activity_during_disruption /
    max(activity_during_normal_periods, epsilon)

epsilon = max(0.01, 0.1 × avg_activity_last_14_days)
          ← adaptive: prevents inflated ratios for new workers

temporal_consistency_score =
    clamp(1 / (1 + exp(−5 × (behavior_drop_ratio − 1))), 0, 1)

Audit band stored: score > 0.7 → "high" | > 0.4 → "medium" | else → "low"
```

**BAF Computation**

```
BAF_raw = 0.4 × peer_ratio
        + 0.35 × activity_score
        + 0.25 × temporal_consistency_score

Dynamic floor:
    trust_score > 0.8 → floor = 0.30
    trust_score > 0.6 → floor = 0.25
    trust_score > 0.4 → floor = 0.20
    else              → floor = 0.10

BAF = max(BAF_raw, floor)
```

**Peer Manipulation Defense**

```
peer_baseline = 0.5 × real_time_peer_avg
              + 0.5 × historical_cluster_avg

50/50 blend: coordinated suppression can only pull the baseline
down by 50% of the suppression magnitude.
```

**Strategic Behavior Penalty**

```
lookback_window = last 5 disruption events
low_effort_event = (activity_score < 0.4 AND peer_ratio < 0.5)

if low_effort_count >= 3 → penalty = 0.6
elif low_effort_count == 2 → penalty = 0.8
else → penalty = 1.0

final_BAF = BAF × penalty

Detection uses INPUTS only — not BAF output.
Circularity eliminated.
```

**Catastrophic Handling**

```
if severity > 0.9 AND multi-source confirmed:
    BAF = 0.7 × signal_score
        + 0.2 × temporal_score
        + 0.1 × activity_score
    enforce BAF ≥ 0.70
```

**Effort Simulation Detection**

```
acceptance_rate_drop =
    order_acceptance_rate_during_disruption /
    order_acceptance_rate_during_normal_periods

if acceptance_rate_drop < 0.6 AND online_hours > peer_avg:
    reduce activity_score by 15%
    flag for audit

Uses acceptance rate — NOT deliveries/hour.
deliveries/hour is confounded by geography and platform allocation.
```

**Eligible Hours**

```
eligible_hours = min(
    shift_overlap_hours,
    rolling_avg_work_hours_last_14_days,
    platform_max_shift_hours        ← configurable per platform
)

if shift_overlap > worker_90th_percentile_hours:
    flag for audit — do NOT auto-cap
```

**Payout Formula**

```
income_lost = hourly_income × eligible_hours × severity_smoothed
adjusted_payout = income_lost × coverage_ratio × final_BAF
```

**Async Audit Triggers**

```
Flag for audit if ANY of:
  unified_confidence_score < 0.75
  BAF < 0.4
  abs(signal_confidence − behavior_confidence) > 0.4
  shift_overlap > worker_90th_percentile_hours
  acceptance_rate_drop < 0.6 AND online_hours > peer_avg
  claim_timing_flag = TRUE
```

**Trust Score Update**

```
Cold start (first 3 claims): trust = 0.6 fixed, no penalties

After cold start:
    if BAF < 0.4: weight = 0.35   ← punishes faster
    else:         weight = 0.20   ← rewards slower

trust_new = (1 − weight) × trust_old + weight × BAF
```

</details>

---

## Known Issues & Mitigations

<details>
<summary>📋 View full engineering trade-offs table (18 items)</summary>

| Issue | Mitigation |
|---|---|
| Circular dependency: baseline and severity share disruption labels | Dual label versioning (Version A / B), peer cluster baseline for severity |
| Single disruption per week assumption | E(disruption_days) replaces binary probability + max_weekly_coverage cap |
| Alpha calibration in hybrid risk model | Calibrated on held-out validation set, not purely volume-based |
| Probability and severity correlation | Acknowledged — joint model deferred to future iteration |
| Climate trend shifts in historical risk | Exponential decay recency weighting |
| Zone vs worker route mismatch | Optional worker route risk score at onboarding |
| Behavioural avoidance bias in severity labels | Exclude inactive days, peer fallback for high-avoidance workers |
| Sparse data in new zones | Hybrid model falls back to historical risk index |
| Disruption threshold sensitivity | Empirically defined, documented, consistent across pipeline |
| BAF penalty circular dependency | Detection uses only inputs (activity_score, peer_ratio) not BAF output |
| GPS signal loss during disruptions | 3-tier fallback: GPS → cell tower blend → network zone |
| Cold start + asymmetric update conflict | Fixed trust = 0.6 for first 3 claims, no penalties during this period |
| Effort simulation (fake online presence) | Acceptance rate drop detection, not deliveries/hour |
| Adverse selection in premium pricing | Zone-level community pricing, risk multiplier hard cap at 2.0× |
| Insurer insolvency risk in bad monsoon weeks | loading_factor 30–45%, max_weekly_coverage cap, reinsurance limit triggers |
| Peer cluster inconsistency across modules | Unified definition: micro_zone + platform + vehicle + time_slot |
| Transparency band reverse-engineering | Label noise ±0.05 on borderline cases — labels only, not payout math |
| Claim timing exploitation | Compound flag: top 20% rolling avg timing AND activity_drop < 0.7 |

</details>

---

## 👥 Team

<table>
<tr>
<td align="center" width="25%">
<br/>
<b>Janya Mahesh</b>
<br/>
<sub>InsureEase</sub>
</td>
<td align="center" width="25%">
<br/>
<b>Idhant Singh</b>
<br/>
<sub>InsureEase</sub>
</td>
<td align="center" width="25%">
<br/>
<b>Jival Raghav</b>
<br/>
<sub>InsureEase</sub>
</td>
<td align="center" width="25%">
<br/>
<b>Inesh Shanmugam</b>
<br/>
<sub>InsureEase</sub>
</td>
</tr>
</table>

<div align="center">

**InsureEase · DEVTrails 2026 · Guidewire University Hackathon**

*Built with purpose — for India's gig delivery workers.*

</div>
