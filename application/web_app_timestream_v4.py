from dash import Dash, dcc, html, Input, Output
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import boto3
from botocore.exceptions import ClientError

# Configuration for Timestream
TIMESTREAM_CLIENT = boto3.client("timestream-query", region_name="eu-west-1")
DATABASE_NAME = "my-timestream-database"  # Replace with your database name
TABLE_NAME = "TestTable"  # Replace with your table name
DAYS = 7  # Lookback range in days

app = Dash(__name__)
app.title = "BTC Trading Bot Monitor"
app.css.config.serve_locally = True


# Function to query Timestream

def query_last_days(client, database_name, table_name, days):
    total_ms = days * 86400000
    # Query to fetch the last record to one day before the last record
    query = f"""
        WITH last_record_time AS (
            SELECT MAX(time) AS last_time
            FROM "{database_name}"."{table_name}"
        )
        SELECT * 
        FROM "{database_name}"."{table_name}"
        WHERE time BETWEEN TIMESTAMPADD('MILLISECOND', -{total_ms}, (SELECT last_time FROM last_record_time))
                       AND (SELECT last_time FROM last_record_time)
        ORDER BY time DESC
    """

    try:
        paginator = client.get_paginator("query")
        response_iterator = paginator.paginate(QueryString=query)

        rows = []
        columns = None

        for response in response_iterator:
            if "ColumnInfo" in response and not columns:
                columns = [col["Name"] for col in response["ColumnInfo"]]
            for row in response["Rows"]:
                rows.append([
                    datum.get("ScalarValue") for datum in row["Data"]
                ])

        if columns and rows:
            # Create DataFrame
            df = pd.DataFrame(rows, columns=columns)
            # Reorganize data to create new columns for each measure_name
            df_pivot = df.pivot_table(index='time', columns='measure_name', values=[col for col in df.columns if col.startswith('measure_value::')], aggfunc='first')
            # Reorganize indexes and columns
            df_pivot.columns = df_pivot.columns.droplevel(0)
            return df_pivot
        else:
            print("No data retrieved.")
            return None

    except ClientError as e:
        print(f"Error querying data: {e}")
        return None


# App Layout
app.layout = html.Div([
    html.Div(
        className="header-container",
        children=[
            html.H1('BTC Trading Bot Monitor', className="app-title"),
            html.P('Live metrics from the trading bot, updated every minute.', className="app-description"),
        ],
        style={"textAlign": "center", "backgroundColor": "#2D2D2D", "color": "white", "padding": "20px"}
    ),

    html.Div(
        style={"display": "flex", "gap": "20px", "padding": "20px"},
        children=[
            html.Div([
                html.P("Select metrics to display:"),
                dcc.Checklist(id='metric-selector', inline=False),
            ], style={"width": "20%", "backgroundColor": "#FFF", "padding": "10px", "borderRadius": "5px"}),
            html.Div([
                dcc.Graph(id='multi-axis-graph', config={'displayModeBar': False})
            ], style={"width": "80%"}),
        ]
    ),

    dcc.Store(id='data-store', data=None),

    html.Div([
        html.Button('Reload Data', id='submit-reload', n_clicks=0, className="reload-button"),
        html.P(id='button-press-text', style={"marginTop": "10px"})
    ], style={"textAlign": "center", "padding": "10px"})
])


@app.callback(
    [Output('multi-axis-graph', 'figure'),
     Output('metric-selector', 'options')],
    [Input('data-store', 'data'),
     Input('metric-selector', 'value')]
)
def update_graph(data, selected_metrics):
    df = pd.read_json(data, orient='split') if data else pd.DataFrame()
    fig = go.Figure()
    available_metrics = [{'label': col, 'value': col} for col in df.columns if df[col].dtype in ['float64', 'int64']]

    for i, metric in enumerate(selected_metrics or []):
        fig.add_trace(go.Scatter(x=df.index, y=df[metric], mode='lines', name=metric, yaxis=f'y{i + 1}'))
        fig.update_layout({f'yaxis{i + 1}': dict(title=metric, overlaying='y', side='right' if i % 2 else 'left')})

    fig.update_layout(title="Selected Metrics", xaxis_title="Datetime")
    return fig, available_metrics


@app.callback(
    Output('button-press-text', 'children'),
    Input('data-store', 'data'),
    Input('submit-reload', 'n_clicks')
)
def update_text(data, n_clicks):
    df = pd.read_json(data, orient='split') if data else pd.DataFrame()
    return f"Data loaded up to {df.index[-1]} (UTC)" if not df.empty else "No data available."


@app.callback(
    Output('data-store', 'data'),
    Input('submit-reload', 'n_clicks')
)
def update_data(n_clicks):
    df = query_last_days(TIMESTREAM_CLIENT, DATABASE_NAME, TABLE_NAME, DAYS)
    print(df.columns)
    return df.to_json(orient='split') if df is not None else None


if __name__ == '__main__':
    app.run_server(port=80, debug=False, host="0.0.0.0")
