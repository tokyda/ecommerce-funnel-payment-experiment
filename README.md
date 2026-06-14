# E-Commerce Funnel Diagnosis & Payment Page A/B Test

This project was built to teach myself two things I had never done before: funnel analysis and end-to-end A/B test evaluation. I am a data science student and wanted to go beyond classroom theory by constructing a realistic analytics workflow from raw data to a business recommendation.

---

## Honest framing

The two datasets used here are publicly available but **unrelated to each other**. The funnel data (Kaggle) comes from one e-commerce site; the A/B test data (Udacity) comes from a separate experiment on a different product. I constructed a narrative that links them — the funnel analysis diagnoses a problem, and the experiment evaluates a proposed fix — but in reality there is no causal connection between the two datasets.

I chose to be upfront about this because the point of the project is to demonstrate a way of thinking, not to present fabricated end-to-end data as real. The analytical workflow and interpretation are genuine; the data pipeline connecting them is illustrative.

---

## What I built

A four-layer dbt pipeline (staging → intermediate → mart) on a local DuckDB warehouse, two executed Jupyter notebooks, and a Streamlit dashboard.

```
data/raw/              ← source CSVs (gitignored)
dbt_project/
  models/
    staging/           ← typed, renamed, deduplicated views
    intermediate/      ← business logic (user journey, experiment cleaning)
    mart/              ← pre-aggregated tables queried by notebooks + dashboard
notebooks/
  01_funnel_analysis.ipynb
  02_experiment_analysis.ipynb
dashboard/app.py       ← Streamlit, two tabs
```

**Stack:** dbt-duckdb · DuckDB · Python · Plotly · Streamlit

---

## The diagnostic finding

The funnel has four steps: Home → Search → Payment → Confirmation. Running the numbers revealed that **92.5% of users who reached the payment page abandoned before converting** — by far the steepest drop in the funnel.

What made this more interesting was the device breakdown. Desktop users abandon at roughly **95%**; mobile users at roughly **90%**. Desktop accounts for two-thirds of all traffic, meaning the bulk of lost conversions are coming from desktop users who reach the payment step and then leave.

This motivated a natural hypothesis: if the payment page were redesigned to reduce friction, conversion should improve.

---

## The experiment

The A/B test evaluated a simplified payment page (treatment) against the existing page (control), with ~145k users in each group.

**Before looking at the result, I checked for a Sample Ratio Mismatch** — a split that deviates significantly from 50/50 suggests a broken randomiser and would invalidate the analysis regardless of the outcome. The split was 49.99% / 50.01% (χ² p = 0.95), so I proceeded.

**Result:** The treatment produced a conversion rate of 11.88% vs 11.88% control, an absolute lift of **−0.16 pp** (p = 0.19, 95% CI: [−0.39 pp, +0.08 pp]).

**Recommendation: NO-GO.**

---

## The part I found hardest: interpreting the result

Reading a p-value is straightforward. Understanding what it actually means for a decision took more thought.

My first instinct was to treat p = 0.19 as "the experiment was inconclusive." But that framing is imprecise. The 95% confidence interval [−0.39 pp, +0.08 pp] tells a cleaner story: the entire plausible range of effects is well below the 1 pp threshold that would make the redesign worth shipping. Even the optimistic end of the interval (+0.08 pp) represents fewer than 100 additional conversions per month at current traffic. The test is not "inconclusive" — it is saying, with reasonable confidence, that *this particular redesign does not produce a meaningful effect*.

The more important realisation was that the experiment was testing the wrong thing. The funnel analysis identified a **device-specific** problem — desktop users abandoning at a disproportionate rate. The A/B test applied a single global redesign to everyone. A treatment that does not target the actual root cause is unlikely to move the metric that matters.

---

## What a code review taught me

After completing the notebooks, I ran a structured code review which surfaced two issues I had not noticed myself.

**Contaminated users.** In the Udacity dataset, approximately 3,900 users appear in both the control and treatment groups — likely due to cookie clearing or bot traffic. My original implementation kept these users and arbitrarily assigned them to the group of their first recorded visit. The correct approach is to exclude them entirely, which I implemented via a `contaminated` CTE in the intermediate model.

**Multiple comparisons.** I ran sub-group z-tests for three countries (US, UK, CA) each at α = 0.05. Running three independent tests at the same threshold raises the family-wise error rate to approximately 14%, meaning there is a 14% chance of declaring at least one false positive across the three tests even if there is no real effect. The Bonferroni-corrected threshold for three tests is α/3 ≈ 0.017. None of the country sub-groups reach significance under this correction.

I did not discover these independently — they were flagged in review. I include them here because they represent genuine learning about how easy it is to introduce subtle bias in experiment analysis, and because I think transparency about the process is more useful than a polished presentation that omits the mistakes.

---

## What I would test next

The global NO-GO does not mean the payment step cannot be improved. It means *this treatment, applied to everyone, did not work*.

The funnel finding points toward a more targeted hypothesis: a payment page redesigned specifically for desktop — larger click targets, keyboard-friendly autofill, fewer required fields — should reduce the ~5 pp abandonment gap between desktop (95%) and mobile (90%). A desktop-only experiment targeting roughly 278k users per month would be the logical next step. A 2 pp lift at that scale translates to approximately 5,600 additional conversions per month.

This is the loop the project is trying to demonstrate: diagnose → hypothesise → test → decide → diagnose again.

---

## Datasets

| Dataset | Source | Files used |
|---|---|---|
| E-commerce funnel | [aerodinamicc on Kaggle](https://www.kaggle.com/datasets/aerodinamicc/ecommerce-website-funnel-analysis) | `home_page_table.csv`, `search_page_table.csv`, `payment_page_table.csv`, `payment_confirmation_table.csv`, `user_table.csv` |
| A/B test (Udacity) | [kexinlin on GitHub](https://github.com/kexinlin/Udacity-Data-Analysis-2018-Basic/blob/master/Project4/countries.csv) | `ab_data.csv`, `countries.csv` |

---

## Running the project

```bash
pip install -r requirements.txt

# Place source CSVs in data/raw/ (see sources.yml for expected filenames)
cd dbt_project && dbt build

# Notebooks
jupyter notebook notebooks/

# Dashboard
streamlit run dashboard/app.py
```

dbt must be run from the `dbt_project/` directory for relative paths to resolve correctly.
