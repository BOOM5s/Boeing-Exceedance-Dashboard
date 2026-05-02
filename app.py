"""
FOQA Dashboard

Description:
Interactive dashboard for analyzing flight operational quality data

Author: Himalaya Gaur

"""

import pandas as pd
import panel as pn
import holoviews as hv
import hvplot.pandas
from datetime import timedelta

pn.extension('tabulator')  # Correct usage
hv.extension('bokeh')      # For HoloViews plot rendering

pd.options.mode.chained_assignment = None  # Suppress SettingWithCopy warnings

# ---------------------------------------------------
# LOAD & CLEAN DATA
# ---------------------------------------------------

def load_and_clean_data():
    df = pd.read_excel("Boeing Exceedances 2025_1.xlsx", sheet_name="Sheet1").dropna(how='all')

    if pd.api.types.is_numeric_dtype(df['DATE']):
        df['DATE'] = pd.to_datetime(df['DATE'] - 25569, origin='1970-01-01', unit='D')
    else:
        df['DATE'] = pd.to_datetime(df['DATE'], errors='coerce')

    if 'Closure Date' in df.columns:
        if pd.api.types.is_numeric_dtype(df['Closure Date']):
            df['Closure Date'] = pd.to_datetime(df['Closure Date'] - 25569, origin='1970-01-01', unit='D', errors='coerce')
        else:
            df['Closure Date'] = pd.to_datetime(df['Closure Date'], errors='coerce')

    for col in ['CAPT', 'F/O', 'SECTOR', 'FLT NO', 'EXCEEDANCE', 'Category', 'Final status', 'Flt Ops Recommendation', 'FSD Recommendation']:
        df[col] = df[col].astype(str).str.strip().replace('nan', '')

    for col in ['LIMIT', 'RECORDED', 'Closure Rate']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    return df

df = load_and_clean_data()

# ---------------------------------------------------
# FILTER WIDGETS
# ---------------------------------------------------

date_range = pn.widgets.DateRangePicker(name='Date Range', value=(df['DATE'].min(), df['DATE'].max()))
category_select = pn.widgets.Select(name='Category', options=['All'] + sorted(df['Category'].unique()))
captain_select = pn.widgets.Select(name='Captain', options=['All'] + sorted(df['CAPT'].unique()))
fo_select = pn.widgets.Select(name='First Officer', options=['All'] + sorted(df['F/O'].unique()))
sector_select = pn.widgets.Select(name='Sector', options=['All'] + sorted(df['SECTOR'].unique()))
flt_no_select = pn.widgets.Select(name='Flight No.', options=['All'] + sorted(df['FLT NO'].unique()))
exceedance_select = pn.widgets.Select(name='Exceedance Type', options=['All'] + sorted(df['EXCEEDANCE'].unique()))
status_select = pn.widgets.Select(name='Status', options=['All'] + sorted(df['Final status'].unique()))

# ---------------------------------------------------
# DATA FILTER FUNCTION
# ---------------------------------------------------

def get_filtered_data(df, date_range, category, captain, fo, sector, flt_no, exceedance, status):
    filtered = df.copy()
    start_date, end_date = date_range
    filtered = filtered[(filtered['DATE'] >= start_date) & (filtered['DATE'] <= end_date)]
    if category != 'All': filtered = filtered[filtered['Category'] == category]
    if captain != 'All': filtered = filtered[filtered['CAPT'] == captain]
    if fo != 'All': filtered = filtered[filtered['F/O'] == fo]
    if sector != 'All': filtered = filtered[filtered['SECTOR'] == sector]
    if flt_no != 'All': filtered = filtered[filtered['FLT NO'] == flt_no]
    if exceedance != 'All': filtered = filtered[filtered['EXCEEDANCE'] == exceedance]
    if status != 'All': filtered = filtered[filtered['Final status'] == status]
    return filtered

# ---------------------------------------------------
# KPI PANEL
# ---------------------------------------------------

def get_kpis(df):
    total = len(df)
    reported = len(df[df['Final status'].str.lower() == 'reported'])
    info = len(df[df['Final status'].str.lower().isin(['comments', 'information'])])
    closed = len(df[df['Final status'].str.lower() == 'closed'])
    open_cases = total - closed
    counselling = len(df[df['Flt Ops Recommendation'].str.contains('counselling', case=False, na=False)])
    top3 = df['EXCEEDANCE'].value_counts().nlargest(3).index.tolist()

    return {
        'Total': total,
        'Reported %': reported / total * 100 if total else 0,
        'Info %': info / total * 100 if total else 0,
        'Open %': open_cases / total * 100 if total else 0,
        'Closed %': closed / total * 100 if total else 0,
        'Counselling %': counselling / total * 100 if total else 0,
        'Top 3': top3
    }

def create_kpi_pane(df_filtered):
    kpi = get_kpis(df_filtered)
    return pn.pane.Markdown(f"""
    **Total Exceedances**: {kpi['Total']}  
    **Reported %**: {kpi['Reported %']:.2f}%  
    **Open %**: {kpi['Open %']:.2f}% | **Closed %**: {kpi['Closed %']:.2f}%  
    **Counselling %**: {kpi['Counselling %']:.2f}%  
    **Top 3 Exceedances**: {', '.join(kpi['Top 3'])}
    """, sizing_mode='stretch_width')

# ---------------------------------------------------
# FIXED CHARTS (INCLUDING THE PATCH)
# ---------------------------------------------------

def exceedance_breakdown(df_filtered):
    for col in ['EXCEEDANCE', 'SECTOR', 'Category', 'Flt Ops Recommendation']:
        df_filtered[col] = df_filtered[col].astype(str)

    type_counts = df_filtered['EXCEEDANCE'].value_counts().reset_index()
    type_counts.columns = ['Exceedance', 'Count']
    bar_type = hv.Bars(type_counts, 'Exceedance', 'Count').opts(width=400, height=300, xrotation=45, title="By Exceedance")

    sector_counts = df_filtered['SECTOR'].value_counts().reset_index()
    sector_counts.columns = ['Sector', 'Count']
    bar_sector = hv.Bars(sector_counts, 'Sector', 'Count').opts(width=400, height=300, xrotation=45, title="By Sector")

    category_counts = df_filtered['Category'].value_counts().reset_index()
    category_counts.columns = ['Category', 'Count']
    bar_category = hv.Bars(category_counts, 'Category', 'Count').opts(width=400, height=300, xrotation=45, title="By Category")

    recommendation_counts = df_filtered['Flt Ops Recommendation'].value_counts().reset_index()
    recommendation_counts.columns = ['Recommendation', 'Count']
    bar_recommendation = hv.Bars(recommendation_counts, 'Recommendation', 'Count').opts(width=400, height=300, xrotation=45, title="Recommendations")

    return pn.panel((bar_type + bar_sector + bar_category + bar_recommendation).cols(2))

# Remaining visualizations...

def crew_analysis(df_filtered):
    df_filtered['CAPT'] = df_filtered['CAPT'].astype(str)
    df_filtered['F/O'] = df_filtered['F/O'].astype(str)

    capt = hv.Bars(df_filtered['CAPT'].value_counts().head(5).reset_index()).opts(title="Top 5 Captains", width=400, height=300, xrotation=45)
    fo = hv.Bars(df_filtered['F/O'].value_counts().head(5).reset_index()).opts(title="Top 5 F/Os", width=400, height=300, xrotation=45)

    pct = (df_filtered['Flt Ops Recommendation'].str.contains('counselling', case=False, na=False).sum() / len(df_filtered) * 100) if len(df_filtered) else 0
    return pn.Row(pn.panel(capt), pn.panel(fo), pn.pane.Markdown(f"**Counselling %**: {pct:.2f}%", sizing_mode='stretch_width'))

def time_trend(df_filtered):
    if df_filtered.empty:
        return pn.pane.Markdown("No data for time trend.")
    df_filtered['Month'] = df_filtered['DATE'].dt.to_period('M').astype(str)
    data = df_filtered.groupby(['Month', 'EXCEEDANCE']).size().reset_index(name='Count')
    ds = hv.Dataset(data, kdims=['Month', 'EXCEEDANCE'], vdims='Count')
    return pn.panel(ds.to(hv.Curve, 'Month', 'Count').opts(width=800, height=400, xrotation=45, title="Monthly Exceedance Trend"))

def status_tracker_table(df_filtered):
    return pn.widgets.Tabulator(
        df_filtered[['ASIR', 'DATE', 'FLT NO', 'CAPT', 'F/O', 'EXCEEDANCE', 'Final status', 'Category', 'Flt Ops Recommendation', 'Comments']],
        layout='fit_data', pagination='local', page_size=10, sizing_mode='stretch_width'
    )

def insights_panel(df_filtered):
    now = df_filtered['DATE'].max() or pd.Timestamp.today()
    overdue = df_filtered[(df_filtered['Final status'].str.upper() != 'CLOSED') & ((now - df_filtered['DATE']).dt.days > 30)]
    recent = df_filtered[df_filtered['DATE'] >= now - timedelta(days=90)]
    high_sector = df_filtered['SECTOR'].value_counts()[df_filtered['SECTOR'].value_counts() > 3].index.tolist()
    high_capt = df_filtered['CAPT'].value_counts()[df_filtered['CAPT'].value_counts() > 3].index.tolist()
    top_recent = recent['EXCEEDANCE'].value_counts().head(3).index.tolist()
    closed_no_rec = df_filtered[(df_filtered['Final status'].str.upper() == 'CLOSED') & (df_filtered['Flt Ops Recommendation'] == 'NR')]
    closed_total = df_filtered[df_filtered['Final status'].str.upper() == 'CLOSED']
    no_rec_pct = (len(closed_no_rec) / len(closed_total)) * 100 if len(closed_total) else 0

    return pn.pane.Markdown(f"""
    ### Insights
    - Sectors >3 Exceedances: {', '.join(high_sector) or 'None'}
    - Captains >3 Exceedances: {', '.join(high_capt) or 'None'}
    - Overdue >30 days: {len(overdue)}
    - Top 3 in Last 90 Days: {', '.join(top_recent) or 'None'}
    - Closed with no recommendation: {no_rec_pct:.2f}%
    """, sizing_mode='stretch_width')

# ---------------------------------------------------
# CALLBACK & LAYOUT
# ---------------------------------------------------

@pn.depends(date_range, category_select, captain_select, fo_select,
            sector_select, flt_no_select, exceedance_select, status_select)
def update_dashboard(date_range, category, captain, fo, sector, flt_no, exceedance, status):
    df_filtered = get_filtered_data(df, date_range, category, captain, fo, sector, flt_no, exceedance, status)
    return pn.Column(
        create_kpi_pane(df_filtered),
        pn.Row(exceedance_breakdown(df_filtered)),
        pn.Row(crew_analysis(df_filtered)),
        time_trend(df_filtered),
        status_tracker_table(df_filtered),
        insights_panel(df_filtered),
        sizing_mode='stretch_width'
    )

# ✅ CALL INITIALLY
initial_dashboard = update_dashboard(
    date_range.value,
    category_select.value,
    captain_select.value,
    fo_select.value,
    sector_select.value,
    flt_no_select.value,
    exceedance_select.value,
    status_select.value
)

dashboard = pn.Column(
    pn.pane.Markdown("# Boeing Exceedances Dashboard"),
    pn.Row(date_range, category_select, captain_select, fo_select),
    pn.Row(sector_select, flt_no_select, exceedance_select, status_select),
    initial_dashboard,
    sizing_mode='stretch_both'
)

dashboard.servable()
