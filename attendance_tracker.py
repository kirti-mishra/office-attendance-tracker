import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from collections import defaultdict
import json
import os

st.set_page_config(page_title="📅 Attendance Policy Planner", layout="wide")

POLICY_DAYS_REQUIRED = 24
DATA_FILE = "attendance_data.json"

def get_week_start(date):
    return date - timedelta(days=date.weekday())

def generate_weeks(start_date, num_weeks):
    return [get_week_start(start_date - timedelta(weeks=w)) for w in range(num_weeks)]

def summarize_weeks(attendance):
    summary = {}
    for d in attendance:
        week_start = get_week_start(d)
        summary.setdefault(week_start, []).append(d)
    return {k: len(v) for k, v in summary.items()}

def best_8_week_attendance(attendance, reference_date):
    cutoff = get_week_start(reference_date)
    past_12_weeks = [cutoff - timedelta(weeks=w) for w in range(1, 13)]
    relevant_days = [d for d in attendance if get_week_start(d) in past_12_weeks]
    summary = summarize_weeks(relevant_days)
    best_8 = sorted(summary.items(), key=lambda x: x[1], reverse=True)[:8]
    best_weeks = [week_start for week_start, _ in best_8]
    return sum(days for _, days in best_8), summary, best_8

def calculate_future_needs(summary, ooo_days, reference_date):
    today = datetime.today().date()
    start_week = get_week_start(today)
    end_week = get_week_start(reference_date + timedelta(weeks=5))

    # Generate all weeks from today to end_week
    num_weeks = (end_week - start_week).days // 7 + 1
    candidate_weeks = [start_week + timedelta(weeks=w) for w in range(num_weeks)]

    # Calculate current total from best 8 weeks
    current_total = sum(sorted(summary.values(), reverse=True)[:8])
    shortfall = max(POLICY_DAYS_REQUIRED - current_total, 0)

    plan = {}
    for week in candidate_weeks:
        # Max 3 office days can be suggested per week (per policy), minus any OOO days
        available_days = min(3, 5 - len([d for d in ooo_days if get_week_start(d) == week]))
        plan[week] = min(available_days, shortfall)
        shortfall -= plan[week]
        if shortfall <= 0:
            break

    # Fill the rest with 0
    for week in candidate_weeks:
        if week not in plan:
            plan[week] = 0

    return dict(sorted(plan.items()))  # Ensure chronological order


def serialize_dates(date_set):
    return [d.isoformat() for d in date_set]

def deserialize_dates(date_list):
    return set(pd.to_datetime(d).date() for d in date_list)

def save_data(attendance_set, ooo_set):
    data = {
        "attendance": serialize_dates(attendance_set),
        "ooo": serialize_dates(ooo_set),
    }
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
        attendance = deserialize_dates(data.get("attendance", []))
        ooo = deserialize_dates(data.get("ooo", []))
        return attendance, ooo
    return set(), set()

if "attendance" not in st.session_state or "ooo" not in st.session_state:
    attendance, ooo = load_data()
    st.session_state.attendance = attendance
    st.session_state.ooo = ooo

st.title("🏢 Office Attendance Policy Tracker")

today = datetime.today().date()
next_monday = today + timedelta(days=(7 - today.weekday()) % 7)

selected_future_week = st.date_input(
    "Select any future Monday (to calculate policy alignment as of that week)",
    next_monday,
    min_value=next_monday
)
if selected_future_week.weekday() != 0:
    st.error("Please select a Monday!")
    st.stop()

# === Main layout with 2 columns ===
col_calendar, col_summary = st.columns([2, 1])

with col_calendar:
    st.header("🗓️ Mark Attendance and WFH (Past + Future)")

    # past_weeks = generate_weeks(selected_future_week, 12)[::-1]
    past_weeks = generate_weeks(selected_future_week - timedelta(weeks=1), 12)[::-1]
    future_weeks = [get_week_start(selected_future_week + timedelta(weeks=w)) for w in range(0, 6)]
    combined_weeks = past_weeks + future_weeks

    months = defaultdict(list)
    for week_start in combined_weeks:
        months[week_start.strftime("%B %Y")].append(week_start)

    for month, week_starts in months.items():
        with st.expander(month, expanded=False):  # collapsed by default
            for week_index, week_start in enumerate(week_starts):
                st.markdown(f"#### 📆 Week of {week_start.strftime('%b %d, %Y')}")
                cols = st.columns(5)
                for i in range(5):
                    day = week_start + timedelta(days=i)
                    base_key = f"{day.strftime('%Y-%m-%d')}_week{week_index}"
                    radio_key = f"status_{base_key}"
                    with cols[i]:
                        st.markdown(f"**{day.strftime('%a %b %d')}**")

                        default_index = 0
                        if day in st.session_state.attendance:
                            default_index = 1
                        elif day in st.session_state.ooo:
                            default_index = 2

                        status = st.radio(
                            label="Status",  # non-empty label for accessibility
                            options=["None", "🏢 Office", "🏖️ WFH"],
                            index=default_index,
                            key=radio_key,
                            label_visibility="collapsed"  # visually hidden but accessible
                        )

                        if status == "🏢 Office":
                            st.session_state.attendance.add(day)
                            st.session_state.ooo.discard(day)
                        elif status == "🏖️ WFH":
                            st.session_state.ooo.add(day)
                            st.session_state.attendance.discard(day)
                        else:  # None
                            st.session_state.attendance.discard(day)
                            st.session_state.ooo.discard(day)

    save_data(st.session_state.attendance, st.session_state.ooo)

with col_summary:
    st.header("📊 Attendance Policy Projection")

    # create two columns for metrics
    col1, col2 = st.columns(2)

    with col1:
        past_days, past_summary, best_weeks = best_8_week_attendance(st.session_state.attendance, selected_future_week)
        future_attendance = [d for d in st.session_state.attendance if d >= selected_future_week]
        total_projected = past_days + len(future_attendance)

        st.metric("Best 8 Weeks (Prior to Selected Week)", f"{past_days} days")
        st.metric(
            f"Projected Total by {selected_future_week.strftime('%b %d')}",
            f"{total_projected} days",
            delta=total_projected - POLICY_DAYS_REQUIRED,
        )
    with col2:
        # Initialize toggle state if not present
        if "show_best_weeks" not in st.session_state:
            st.session_state.show_best_weeks = False

        # Toggle button
        if st.button("📊 Toggle Best Weeks Taken"):
            st.session_state.show_best_weeks = not st.session_state.show_best_weeks

        if st.session_state.show_best_weeks:
            st.text("⭐ Best Weeks Taken Into Consideration")
            best_weeks.sort()
            for week in best_weeks:
                st.write(f"Week of {week[0].strftime('%b %d, %Y')}: **{week[1]}** day(s)")

    if total_projected >= POLICY_DAYS_REQUIRED:
        st.success("✅ You will be aligned with the policy by the selected week.")
    else:
        st.warning(f"⚠️ You need {POLICY_DAYS_REQUIRED - total_projected} more days by {selected_future_week.strftime('%b %d')}.")

    st.subheader("📅 Suggested Office Days Needed Per Week")
    needs = calculate_future_needs(past_summary, st.session_state.ooo, selected_future_week)

    # Prepare data for chart and cumulative calculation
    past_weeks = generate_weeks(selected_future_week - timedelta(weeks=1), 12)[::-1]
    future_weeks = [get_week_start(selected_future_week + timedelta(weeks=w)) for w in range(0, 6)]
    all_weeks = past_weeks + future_weeks

    data = []
    for week in all_weeks:
        office_days = len([d for d in st.session_state.attendance if get_week_start(d) == week])
        ooo_days = len([d for d in st.session_state.ooo if get_week_start(d) == week])
        suggested_days = needs.get(week, 0)
        data.append({
            "Week": week.strftime("%b %d"),
            "Office Days": office_days,
            "WFH Days": ooo_days,
            "Suggested Days": suggested_days,
        })

    df = pd.DataFrame(data)

    # Melt to long format for stacked bar chart
    df_long = df.melt(id_vars="Week", value_vars=["Office Days", "WFH Days", "Suggested Days"],
                        var_name="Type", value_name="Days")

    # --- Calculate cumulative totals to find alignment week ---
    past_total = past_days
    future_weeks_keys = list(needs.keys())
    cumulative_totals = []
    running_total = past_total

    for week in future_weeks_keys:
        running_total += needs[week]
        cumulative_totals.append(running_total)

    aligned_week_index = None
    for idx, total in enumerate(cumulative_totals):
        if total >= POLICY_DAYS_REQUIRED:
            aligned_week_index = idx
            break

    # Mark aligned week in df
    df['Aligned Week'] = False
    aligned_week_str = None
    if aligned_week_index is not None:
        aligned_week_str = future_weeks_keys[aligned_week_index].strftime("%b %d")
        df.loc[df['Week'] == aligned_week_str, 'Aligned Week'] = True

    # Assign colors, highlight aligned week Suggested Days in red
    base_colors = {
        "Office Days": "#1f77b4",
        "WFH Days": "#ff7f0e",
        "Suggested Days": "#2ca02c",
    }

    def get_color(row):
        if row["Type"] == "Suggested Days" and row["Aligned Week"]:
            return "#d62728"  # red highlight
        return base_colors[row["Type"]]

    df_long = df_long.merge(df[['Week', 'Aligned Week']], on='Week', how='left')
    df_long['Color'] = df_long.apply(get_color, axis=1)

    fig = px.bar(
        df_long,
        x="Week",
        y="Days",
        color="Type",
        barmode="stack",
        title="Office vs WFH Days (12 Weeks Prior + 6 Weeks Future)",
        color_discrete_map=base_colors,
    )

    # Update bar colors manually for the aligned week bars
    for i, trace in enumerate(fig.data):
        colors = []
        for j, x_val in enumerate(trace.x):
            # Find color for each bar segment from df_long by matching x and trace name
            mask = (df_long['Week'] == x_val) & (df_long['Type'] == trace.name)
            if not mask.any():
                colors.append(base_colors[trace.name])
            else:
                colors.append(df_long.loc[mask, 'Color'].values[0])
        trace.marker.color = colors

    st.plotly_chart(fig, use_container_width=True)

    # Show aligned week message
    if aligned_week_index is not None:
        st.success(f"✅ You will be aligned with the policy starting the week of **{aligned_week_str}**.")
    else:
        st.info("⚠️ You are not projected to be aligned within the shown future weeks.")

    # Also list weeks with needed days
    for week, needed in needs.items():
        st.write(f"Week of {week.strftime('%b %d')}: **{needed}** day(s) needed")
