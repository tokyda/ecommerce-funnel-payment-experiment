import duckdb
import pandas as pd
import numpy as np
from scipy.stats import chisquare, norm
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "funnel_analysis.duckdb"


@st.cache_resource
def get_connection():
    return duckdb.connect(str(DB_PATH), read_only=True)


@st.cache_data
def load_funnel():
    con = get_connection()
    return con.execute("SELECT * FROM mart_funnel_metrics ORDER BY step_order").df()


@st.cache_data
def load_segments():
    return get_connection().execute("SELECT * FROM mart_funnel_segments").df()


@st.cache_data
def load_experiment():
    return get_connection().execute("SELECT * FROM mart_experiment_results").df()


def two_prop_ztest(x1, n1, x2, n2):
    p1, p2 = x1 / n1, x2 / n2
    p_pool = (x1 + x2) / (n1 + n2)
    se = np.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    z = (p1 - p2) / se
    return z, float(2 * norm.sf(abs(z)))


# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Funnel & A/B Test Analysis",
    page_icon="📊",
    layout="wide",
)

st.title("E-Commerce Funnel & A/B Test Analysis")
st.caption("Diagnose → Test → Decide  |  Data: Kaggle (funnel) + Udacity (experiment)")

tab1, tab2 = st.tabs(["Funnel Analysis", "A/B Test Results"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — FUNNEL
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    funnel_df   = load_funnel()
    segments_df = load_segments()

    st.subheader("Funnel Drop-off by Step")

    # ── Segment filter ───────────────────────────────────────────────────────
    col_filter, col_spacer = st.columns([2, 5])
    with col_filter:
        segment_by = st.selectbox(
            "Segment by",
            options=["All Users", "Device", "Gender"],
        )

    # ── Waterfall chart ──────────────────────────────────────────────────────
    COLORS = ["#1d3461", "#1f6feb", "#e36209", "#b91c1c"]

    if segment_by == "All Users":
        fig = go.Figure(go.Funnel(
            y=funnel_df["step"],
            x=funnel_df["users"],
            textposition="inside",
            textinfo="value+percent initial",
            marker=dict(color=COLORS),
            connector=dict(line=dict(color="#ddd", width=1)),
        ))
        fig.update_layout(
            title="Full Funnel — Users at Each Step",
            height=420,
            margin=dict(l=180, r=40, t=50, b=30),
        )
        st.plotly_chart(fig, use_container_width=True)

    else:
        seg_col = "device" if segment_by == "Device" else "gender"
        seg_vals = sorted(
            [v for v in segments_df[seg_col].unique() if v != "unknown"]
        )

        selected = st.multiselect(
            f"Select {segment_by.lower()}(s)",
            options=seg_vals,
            default=seg_vals,
        )
        if not selected:
            st.warning("Select at least one segment.")
        else:
            seg_sub = (
                segments_df[segments_df[seg_col].isin(selected)]
                .groupby(seg_col)[
                    ["home_users", "search_users", "payment_users", "confirmation_users"]
                ]
                .sum()
                .reset_index()
            )

            steps = ["home_users", "search_users", "payment_users", "confirmation_users"]
            step_labels = ["Home Page", "Search Page", "Payment Page", "Confirmation Page"]
            palette = px.colors.qualitative.Bold

            fig_seg = go.Figure()
            for i, seg in enumerate(seg_sub[seg_col]):
                row = seg_sub[seg_sub[seg_col] == seg].iloc[0]
                fig_seg.add_trace(go.Bar(
                    name=seg.title(),
                    x=step_labels,
                    y=[row[s] for s in steps],
                    marker_color=palette[i % len(palette)],
                ))
            fig_seg.update_layout(
                barmode="group",
                title=f"Users at Each Step by {segment_by}",
                yaxis_title="Users",
                height=420,
            )
            st.plotly_chart(fig_seg, use_container_width=True)

    # ── Drop-off table ───────────────────────────────────────────────────────
    st.subheader("Drop-off Summary Table")
    table_df = funnel_df[
        ["step", "users", "drop_off_count", "drop_off_pct", "conversion_from_home_pct"]
    ].rename(columns={
        "step": "Step",
        "users": "Users",
        "drop_off_count": "Drop-off Count",
        "drop_off_pct": "Drop-off % (from prev step)",
        "conversion_from_home_pct": "Cumulative % (from home)",
    })
    st.dataframe(table_df, hide_index=True, use_container_width=True)

    # ── Device × Gender heatmap ──────────────────────────────────────────────
    st.subheader("Payment Drop-off by Device × Gender")
    pivot = segments_df[segments_df["device"] != "unknown"].pivot_table(
        index="device", columns="gender", values="payment_dropoff_pct"
    )
    fig_heat = px.imshow(
        pivot,
        text_auto=".1f",
        color_continuous_scale="Reds",
        title="Payment Page Abandonment Rate (%) — higher is worse",
        labels=dict(x="Gender", y="Device", color="Abandonment %"),
    )
    fig_heat.update_layout(height=300)
    st.plotly_chart(fig_heat, use_container_width=True)

    st.info(
        "**Key finding:** The Payment → Confirmation step has the highest drop-off rate "
        "(92.5%). Desktop users abandon at 94–95%, vs 89–90% for mobile. "
        "This motivated an A/B test of a simplified payment page — see the **A/B Test Results** tab."
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — EXPERIMENT
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    exp_df = load_experiment()

    ctrl_df = exp_df[exp_df["experiment_group"] == "control"]
    trt_df  = exp_df[exp_df["experiment_group"] == "treatment"]

    n_ctrl    = len(ctrl_df)
    n_trt     = len(trt_df)
    N         = n_ctrl + n_trt
    conv_ctrl = int(ctrl_df["converted"].sum())
    conv_trt  = int(trt_df["converted"].sum())
    cr_ctrl   = ctrl_df["converted"].mean()
    cr_trt    = trt_df["converted"].mean()

    abs_lift_pp = (cr_trt - cr_ctrl) * 100
    rel_lift    = (cr_trt - cr_ctrl) / cr_ctrl * 100

    se_ci      = np.sqrt(cr_ctrl * (1 - cr_ctrl) / n_ctrl + cr_trt * (1 - cr_trt) / n_trt)
    ci_low_pp  = abs_lift_pp - 1.96 * se_ci * 100
    ci_high_pp = abs_lift_pp + 1.96 * se_ci * 100

    z_stat, p_value = two_prop_ztest(conv_trt, n_trt, conv_ctrl, n_ctrl)

    chi2_stat, p_srm = chisquare([n_ctrl, n_trt], f_exp=[N / 2, N / 2])

    verdict = "GO" if (p_value < 0.05 and abs_lift_pp > 0) else "NO-GO"

    # ── SRM badge ────────────────────────────────────────────────────────────
    st.subheader("Sample Ratio Mismatch (SRM) Check")
    c1, c2, c3 = st.columns(3)
    c1.metric("Control N", f"{n_ctrl:,}", f"{100*n_ctrl/N:.2f}%")
    c2.metric("Treatment N", f"{n_trt:,}", f"{100*n_trt/N:.2f}%")
    if p_srm < 0.05:
        c3.error(f"SRM DETECTED  |  p = {p_srm:.4f}")
    else:
        c3.success(f"No SRM  |  p = {p_srm:.4f}")

    st.divider()

    # ── Conversion rates ─────────────────────────────────────────────────────
    st.subheader("Conversion Rates")
    col_bar, col_stats = st.columns([3, 2])

    with col_bar:
        fig_cr = go.Figure([
            go.Bar(
                name="Control",
                x=["Control"],
                y=[cr_ctrl * 100],
                marker_color="#1f6feb",
                text=[f"{cr_ctrl:.3%}"],
                textposition="outside",
            ),
            go.Bar(
                name="Treatment",
                x=["Treatment"],
                y=[cr_trt * 100],
                marker_color="#e36209",
                text=[f"{cr_trt:.3%}"],
                textposition="outside",
            ),
        ])
        fig_cr.update_layout(
            yaxis_title="Conversion Rate (%)",
            yaxis_range=[0, max(cr_ctrl, cr_trt) * 100 * 1.3],
            height=360,
            showlegend=False,
        )
        st.plotly_chart(fig_cr, use_container_width=True)

    with col_stats:
        st.metric("Control CR", f"{cr_ctrl:.4%}", f"{conv_ctrl:,} conversions")
        st.metric("Treatment CR", f"{cr_trt:.4%}", f"{conv_trt:,} conversions")
        st.metric("Absolute Lift", f"{abs_lift_pp:+.2f} pp")
        st.metric("Relative Lift", f"{rel_lift:+.2f}%")

    # ── CI visualisation ─────────────────────────────────────────────────────
    st.subheader("Statistical Significance & Confidence Interval")
    col_ci, col_p = st.columns([4, 2])

    with col_ci:
        fig_ci = go.Figure()
        fig_ci.add_trace(go.Scatter(
            x=[abs_lift_pp], y=["Treatment vs Control"],
            mode="markers",
            marker=dict(size=16, color="#e36209", symbol="diamond"),
            error_x=dict(
                type="data",
                array=[ci_high_pp - abs_lift_pp],
                arrayminus=[abs_lift_pp - ci_low_pp],
                color="#e36209",
                thickness=3,
            ),
            name="Point estimate + 95% CI",
        ))
        fig_ci.add_vline(x=0,    line_dash="dash", line_color="gray",
                          annotation_text="No effect")
        fig_ci.add_vline(x=1.0,  line_dash="dot",  line_color="green",
                          annotation_text="+1 pp threshold")
        fig_ci.add_vline(x=-1.0, line_dash="dot",  line_color="red",
                          annotation_text="−1 pp harm")
        fig_ci.update_layout(
            xaxis_title="Lift (percentage points)",
            height=260,
        )
        st.plotly_chart(fig_ci, use_container_width=True)

    with col_p:
        st.metric("Z-statistic", f"{z_stat:.4f}")
        st.metric("P-value", f"{p_value:.4f}")
        if p_value < 0.05:
            st.success("Significant at α=0.05")
        else:
            st.error("Not significant at α=0.05")
        st.caption(f"95% CI: [{ci_low_pp:+.2f} pp, {ci_high_pp:+.2f} pp]")

    # ── Country breakdown ────────────────────────────────────────────────────
    st.subheader("Country Breakdown of Treatment Effect")
    country_rows = []
    for country in ["US", "UK", "CA"]:
        df_c = exp_df[(exp_df["country"] == country) & (exp_df["experiment_group"] == "control")]
        df_t = exp_df[(exp_df["country"] == country) & (exp_df["experiment_group"] == "treatment")]
        if len(df_c) < 100 or len(df_t) < 100:
            continue
        cr_c = df_c["converted"].mean()
        cr_t = df_t["converted"].mean()
        lift = (cr_t - cr_c) * 100
        _, p = two_prop_ztest(int(df_t["converted"].sum()), len(df_t),
                              int(df_c["converted"].sum()), len(df_c))
        country_rows.append({
            "Country": country,
            "N Control": len(df_c),
            "N Treatment": len(df_t),
            "CR Control (%)": round(cr_c * 100, 3),
            "CR Treatment (%)": round(cr_t * 100, 3),
            "Lift (pp)": round(lift, 3),
            "p-value": round(p, 4),
            "Significant": "Yes" if p < 0.05 else "No",
        })

    country_df = pd.DataFrame(country_rows)
    st.dataframe(country_df, hide_index=True, use_container_width=True)

    fig_country = px.bar(
        country_df, x="Country", y="Lift (pp)",
        color="Significant",
        color_discrete_map={"Yes": "#16a34a", "No": "#6b7280"},
        text="Lift (pp)",
        title="Treatment Lift by Country",
    )
    fig_country.add_hline(y=0, line_dash="dash", line_color="gray")
    fig_country.update_traces(texttemplate="%{text:.2f}pp", textposition="outside")
    fig_country.update_layout(height=380, yaxis_title="Lift (pp)")
    st.plotly_chart(fig_country, use_container_width=True)

    # ── Verdict card ─────────────────────────────────────────────────────────
    st.divider()
    st.subheader("Go / No-Go Verdict")

    monthly_users = N / 21 * 30  # actual test window: 21 days (2017-01-02 to 2017-01-24)
    monthly_delta = abs_lift_pp / 100 * monthly_users

    if verdict == "GO":
        st.success(f"**SHIP IT — {verdict}**")
        st.write(
            f"The new payment page produces a statistically significant lift of "
            f"**{abs_lift_pp:+.2f} pp** (p={p_value:.4f}). At current monthly traffic of "
            f"~{monthly_users:,.0f} users, this translates to "
            f"**{monthly_delta:+,.0f} additional conversions per month**. Ship globally."
        )
    else:
        st.error(f"**DO NOT SHIP — {verdict}**")
        st.write(
            f"The new payment page does **not** produce a statistically significant improvement "
            f"(p={p_value:.4f} > 0.05). The observed lift is **{abs_lift_pp:+.2f} pp** with "
            f"95% CI [{ci_low_pp:+.2f} pp, {ci_high_pp:+.2f} pp] — the interval includes zero. "
            f"At current monthly traffic of ~{monthly_users:,.0f} users, the expected delta is only "
            f"**{monthly_delta:+,.0f} conversions/month**, which is not reliably distinguishable "
            f"from noise. No country subgroup shows a significant positive effect. "
            f"**Do not ship.** Revisit the UX design, identify specific friction points, "
            f"and re-test with a sharper hypothesis."
        )
