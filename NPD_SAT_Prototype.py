# Importing necessary libraries
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
from dash import Dash, html, dcc, Output, Input, State, dash_table
from dataretrieval import nwis
import calendar

# Function to fetch and process data from USGS using NWIS
def fetch_usgs_data(site_no, start_date, end_date):
    df, metadata = nwis.get_dv(sites=site_no, start=start_date, end=end_date, parameterCd='00060')
    if not df.empty and '00060_Mean' in df.columns:
        df.rename(columns={'00060_Mean': 'cfs'}, inplace=True)
        df.index.rename('datetime', inplace=True)
        df.reset_index(inplace=True)
        return df
    return pd.DataFrame(columns=['datetime', 'cfs'])

# Function to assign seasons to months
def assign_season(month):
    if 3 <= month <= 5:
        return 'Spring'
    elif 6 <= month <= 8:
        return 'Summer'
    elif 9 <= month <= 11:
        return 'Fall'
    else:
        return 'Winter'
    
# Function to plot the flow duration curve
def plot_flow_duration_curve(df):
    df_sorted = df.sort_values('cfs', ascending=False)
    exceedance_probability = df_sorted['cfs'].rank(method='min', pct=True) * 100
    df_sorted['exceedance'] = 100 - exceedance_probability
    fig = px.line(df_sorted, x='exceedance', y='cfs', labels={'cfs': 'Streamflow (cfs)', 'exceedance': 'Exceedance Probability (%)'})
    fig.update_layout(plot_layout)
    return fig

# Loading the CSV file with dam data
df = pd.read_csv('NPD_App.csv')

# Setting up external stylesheet for styling
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

# Initializing the Dash app with a more modern look
app = Dash(__name__, external_stylesheets=['https://codepen.io/chriddyp/pen/dZVMbK.css'], suppress_callback_exceptions=True)
server = app.server

# Styling variables for plots
plot_style = {'height': '400px', 'width': '600px'}
default_margin = {'marginTop': '5px'}
plot_layout = {'height': 400, 'width': 600, 'showlegend': False}
tabs_styles = {
    'fontSize': '12px', # Reducing font size
}

# Creating a scatter mapbox figure with Plotly Express
fig = px.scatter_mapbox(data_frame=df, lat='LATITUDE', lon='LONGITUDE', hover_name='DAM_NAME', zoom=3.5)
fig.update_layout(mapbox_style="open-street-map", mapbox_center={"lat": 38.8, "lon": -98}, margin={"r": 0, "t": 0, "l": 0, "b": 0})
fig.update_traces(marker={"size": 15, 'color': 'orange', 'opacity': 0.75})

# Defining the layout of the app
app.layout = html.Div([
    html.Div([
        html.Div([
            html.H4('CONUS Non-powered Dams'),
            dcc.Graph(id='your-map-graph', figure=fig, style={'height': '600px', 'width': '1000px'}),
        ], style={'display': 'inline-block', 'paddingRight': '10px'}),
        
        html.Div([
            html.H4('Red Flag Feature Descriptions'),
            html.Div(id='dam-details', style={'overflowY': 'auto', 'height': '360px', 'width': '550px'}),
            
            html.Div([
                # html.H6('USGS Site and Date Range Selection'),
                html.H4('USGS Flow Characteristics Plots'),
                # Embedding the link below the "USGS Flow Characteristics Plots" header
                html.Div([
                    html.A("Explore Sites at USGS Water Data Mapper", 
                           href="https://maps.waterdata.usgs.gov/mapper/", 
                           target="_blank", 
                           style={'color': '#0074D9', 'fontSize': '12px', 'display': 'block', 'marginBottom': '10px'})
                ]),
                html.Div([
                    dcc.Input(id='site-number-input', type='text', placeholder='Enter USGS Site Number', style={'marginRight': '6px', 'fontSize': '12px'}),
                    dcc.DatePickerSingle(id='start-date-picker', placeholder='Start Date', style={'marginRight': '6px', 'fontSize': '12px'}),
                    dcc.DatePickerSingle(id='end-date-picker', placeholder='End Date', style={'marginRight': '6px', 'fontSize': '12px'}),
                    html.Button('Submit', id='submit-val', n_clicks=0, style={'fontSize': '10px'}),
                ], style={'display': 'flex', 'justifyContent': 'flex-start', 'alignItems': 'center'}),
            ], style=default_margin),
            
            html.Div([
                dcc.Tabs(id="tabs", children=[
                dcc.Tab(label='Time Series', children=[dcc.Graph(id='time-series-plot', style=plot_style)]),
                dcc.Tab(label='Seasonal Avg.', children=[dcc.Graph(id='seasonal-avg-plot', style=plot_style)]),
                dcc.Tab(label='Monthly Avg.', children=[dcc.Graph(id='monthly-avg-plot', style=plot_style)]),
                dcc.Tab(label='Flow Duration', children=[dcc.Graph(id='flow-duration-plot', style=plot_style)])
            ], style=tabs_styles), # Applying custom style to tabs
        ], style=default_margin),
        ], style={'display': 'inline-block', 'verticalAlign': 'top', 'width': '550px'}),
    ], style={'textAlign': 'center'}),
], style={'fontFamily': 'Arial, sans-serif', 'marginTop': '10px'})

# Callback for updating dam details and map zoom on click
@app.callback(
    [Output('dam-details', 'children'), Output('your-map-graph', 'figure')],
    [Input('your-map-graph', 'clickData')]
)
def display_dam_details_and_zoom(clickData):
    fig_layout = {
        'mapbox': {'style': "open-street-map", 'center': {"lat": 38.8, "lon": -98}, 'zoom': 3.5},
        'margin': {"r": 0, "t": 0, "l": 0, "b": 0}
    }

    def format_value(val):
        return f"{val:.3f}" if isinstance(val, float) else val

    if clickData is not None:
        lat = clickData['points'][0]['lat']
        lon = clickData['points'][0]['lon']
        dam_row = df[(df['LATITUDE'] == lat) & (df['LONGITUDE'] == lon)]

        fig_layout['mapbox']['center'] = {"lat": lat, "lon": lon}
        fig_layout['mapbox']['zoom'] = 15

        if not dam_row.empty:
            table_data = [
                {"Feature": "Dam Name", "Value": dam_row.iloc[0]['DAM_NAME']},
                {"Feature": "Dam Owner", "Value": dam_row.iloc[0]['OWNER_NAME']},
                {"Feature": "Primary Purpose", "Value": dam_row.iloc[0]['PRMR_PRPS']},
                {"Feature": "Gen. Capacity (MW)", "Value": format_value(dam_row.iloc[0]['CAP_MW'])},
                {"Feature": "Distance to Substation (Mi)", "Value": format_value(dam_row.iloc[0]['DIST_SUBST'])},
                {"Feature": "FEMA Hazard Category", "Value": dam_row.iloc[0]['FEMA_HAZ']},
                {"Feature": "Dam Condition", "Value": dam_row.iloc[0]['DAM_COND']},
                {"Feature": "Dam Removal Consideration (%)", "Value": format_value(dam_row.iloc[0]['COMP_SCORE'])},
                {"Feature": "Fish Species Count", "Value": dam_row.iloc[0]['SPECIES_CT']},
                {"Feature": "Fish Passage Requirement (%)", "Value": dam_row.iloc[0]['FSH_PSSG_PCT']},
                {"Feature": "Protected Land", "Value": dam_row.iloc[0]['PROT_LAND']},
                {"Feature": "Impaired Stream", "Value": dam_row.iloc[0]['IMP_STREAM']},
                {"Feature": "Critical Habitat", "Value": dam_row.iloc[0]['CRIT_HAB']}
            ]
            return dash_table.DataTable(
                data=table_data,
                columns=[{"name": i, "id": i} for i in ("Feature", "Value")],
                style_as_list_view=True,
                style_cell={'padding': '5px', 'fontSize': 12, 'font-family': 'sans-serif'},
                style_header={'backgroundColor': 'white', 'fontWeight': 'bold'},
                style_table={'width': '500px'}
            ), go.Figure(data=px.scatter_mapbox(
                data_frame=df, lat='LATITUDE', lon='LONGITUDE', hover_name='DAM_NAME', hover_data=dict(LATITUDE=False, LONGITUDE=False), zoom=15
            ).update_layout(fig_layout).update_traces(marker={"size": 15, 'color': 'orange', 'opacity': 0.75}))
    return html.Div(), go.Figure(data=px.scatter_mapbox(
        data_frame=df, lat='LATITUDE', lon='LONGITUDE', hover_name='DAM_NAME', hover_data=dict(LATITUDE=False, LONGITUDE=False), zoom=3.5
    ).update_layout(fig_layout).update_traces(marker={"size": 15, 'color': 'orange', 'opacity': 0.75}))

@app.callback(
    [Output('time-series-plot', 'figure'),
     Output('seasonal-avg-plot', 'figure'),
     Output('monthly-avg-plot', 'figure'),
     Output('flow-duration-plot', 'figure')],
    [Input('submit-val', 'n_clicks')],
    [State('site-number-input', 'value'), State('start-date-picker', 'date'), State('end-date-picker', 'date')]
)
def update_plots(n_clicks, site_no, start_date, end_date):
    if n_clicks > 0 and site_no and start_date and end_date:
        df = fetch_usgs_data(site_no, start_date, end_date)
        if not df.empty:
            # Time Series Plot
            time_series_fig = px.line(df, x='datetime', y='cfs', labels={'cfs': 'Streamflow (cfs)'}).update_layout(plot_layout)

            # Seasonal Averages Plot
            df['season_name'] = df['datetime'].dt.month.apply(assign_season)
            seasonal_avg = df.groupby('season_name')['cfs'].mean().reindex(['Winter', 'Spring', 'Summer', 'Fall'])
            seasonal_avg_fig = px.bar(seasonal_avg, labels={'value': 'Avg. Streamflow (cfs)', 'season_name': 'Season'}).update_layout(plot_layout)

            # Monthly Averages Plot
            df['month'] = df['datetime'].dt.month
            df['month_name'] = df['month'].apply(lambda x: calendar.month_abbr[x])
            monthly_avg = df.groupby('month_name')['cfs'].mean()
            monthly_avg_fig = px.bar(monthly_avg, labels={'value': 'Avg. Streamflow (cfs)', 'month_name': 'Month'}).update_layout(plot_layout)

            # Flow Duration Curve Plot
            flow_duration_fig = plot_flow_duration_curve(df)

            return time_series_fig, seasonal_avg_fig, monthly_avg_fig, flow_duration_fig
        else:
            # No data available plot
            no_data_fig = go.Figure().add_annotation(text="No data available for the selected range", xref="paper", yref="paper", showarrow=False, font=dict(size=16))
            no_data_fig.update_layout(plot_layout)
            return no_data_fig, no_data_fig, no_data_fig, no_data_fig
    else:
        # Select data plot
        select_data_fig = go.Figure().add_annotation(text="Select a site and date range", xref="paper", yref="paper", showarrow=False, font=dict(size=16))
        select_data_fig.update_layout(plot_layout)
        return select_data_fig, select_data_fig, select_data_fig, select_data_fig

# Running the app
if __name__ == '__main__':
    app.run_server(debug=True)
