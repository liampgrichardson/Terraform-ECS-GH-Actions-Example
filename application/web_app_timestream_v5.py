from dash import Dash, dcc, html, Input, Output
import plotly.express as px
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
def query_last_days(timestream_client, database_name, table_name, days):
    total_ms = days * 86400000
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
        paginator = timestream_client.get_paginator("query")
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
            df = pd.DataFrame(rows, columns=columns)
            df_pivot = df.pivot_table(index='time', columns='measure_name',
                                       values=[col for col in df.columns if col.startswith('measure_value::')], aggfunc='first')
            df_pivot.columns = df_pivot.columns.droplevel(0)
            return df_pivot
        else:
            print("No data retrieved.")
            return None

    except ClientError as e:
        print(f"Error querying data: {e}")
        return None


# Updated layout
app.layout = html.Div([
    html.Div(
        className="header-container",
        children=[
            html.H1('BTC Trading Bot Monitor', className="app-title"),
            html.P('Live metrics from the trading bot, updated every minute.', className="app-description"),
        ],
        style={
            "textAlign": "center",
            "backgroundColor": "#2D2D2D",
            "color": "white",
            "padding": "20px",
            "borderBottom": "4px solid #FFD700"
        },
    ),

    html.Div(
        id="graph-container",
        className="graph-container",
        children=[],  # Graphs will be dynamically added here
        style={
            "display": "flex",
            "flexDirection": "column",
            "gap": "20px",
            "padding": "20px",
            "backgroundColor": "#F9F9F9",
        },
    ),

    html.Div(
        children=[html.Br()]
    ),

    html.Div([
        html.Div(
            children=[
                html.P('Lookback range (hours):', style={"marginBottom": "5px"}),
                dcc.RangeSlider(
                    id='range-slider',
                    min=-10080,
                    max=0,
                    step=10,
                    value=[-10080, 0],
                    marks={i: {"label": f"{int(24 * i / 1440)}h"} for i in range(-10080, 1, 1440)},
                    tooltip={"placement": "bottom", "always_visible": True},
                )
            ],
            style={"width": "60%", "padding": "10px"}
        ),
        html.Div(
            children=[
                html.P('Select Graphs:', style={"marginBottom": "5px"}),
                dcc.Dropdown(
                    id='graph-selector',
                    options=[
                        {'label': 'Price Data', 'value': 'price-data'},
                        {'label': 'Volatility Data', 'value': 'volatility-data'},
                        {'label': 'Position Data', 'value': 'position-data'},
                        {'label': 'Order Data', 'value': 'order-data'}
                    ],
                    value=['price-data'],  # Default selection
                    multi=True,
                    clearable=False,
                    style={
                        "maxWidth": "100%",  # Ensures dropdown width fits within container
                        "overflowY": "auto",  # Makes sure it is scrollable if necessary
                    },
                    optionHeight=35,  # Adjust this for desired height of each dropdown item
                    maxHeight=200,  # Sets the maximum height for the dropdown menu
                )
            ],
            style={"width": "20%", "padding": "10px"}
        ),
        html.Div(
            children=[
                html.Button('Reload Data', id='submit-reload', n_clicks=0, className="reload-button"),
                html.P(id='button-press-text', style={"marginTop": "10px"})
            ],
            style={"width": "20%", "textAlign": "center", "padding": "10px"}
        ),
    ],
        style={
            "display": "flex",
            "justifyContent": "space-between",
            "alignItems": "center",
            "backgroundColor": "#FFF",
            "borderRadius": "10px",
            "boxShadow": "0 4px 6px rgba(0, 0, 0, 0.1)",
            "padding": "10px",
            "position": "fixed",
            "bottom": "0",
            "left": "0",
            "right": "0",
            "zIndex": "1000",
        }
    ),

    dcc.Store(id='data-store', data=None),
], style={"fontFamily": "Arial, sans-serif", "backgroundColor": "#E5E5E5"})


@app.callback(
    Output('graph-container', 'children'),
    Input('data-store', 'data'),
    Input('graph-selector', 'value'),
    Input('range-slider', 'value'))
def update_graphs(data, selected_graphs, slider_range):
    df = pd.read_json(data, orient='split')
    start = df.index[max(slider_range[0] - 1, -len(df))]
    stop = df.index[max(slider_range[1] - 1, -len(df))]
    df = df.loc[start:stop]

    # Generate graphs dynamically
    graphs = []
    for graph_id in selected_graphs:
        if graph_id == 'price-data':
            fig1_cols = ["close", "pfma", "12h_close_mean"]
            fig = px.line(df, x=df.index, y=np.intersect1d(fig1_cols, df.columns),
                          template='plotly', title='Price Data')
            fig.update_layout(xaxis_title='Datetime', yaxis_title=None)
        elif graph_id == 'volatility-data':
            fig2_cols = ["12h_close_cv_pct", "12h_close_pos_cv_pct", "12h_close_neg_cv_pct"]
            fig = px.line(df, x=df.index, y=np.intersect1d(fig2_cols, df.columns),
                          template='plotly', title='Volatility Data')
            fig.update_layout(xaxis_title='Datetime', yaxis_title=None)
        elif graph_id == 'position-data':
            fig3_cols = ["desired_op_pct"]
            fig = px.line(df, x=df.index, y=np.intersect1d(fig3_cols, df.columns),
                          template='plotly', title='Position Data')
            fig.update_layout(xaxis_title='Datetime', yaxis_title=None)
        elif graph_id == 'order-data':
            fig4_df = pd.DataFrame(index=df.index.copy())
            unique_strings = set(df['order_error'].dropna())
            for string in unique_strings:
                fig4_df[string] = df['order_error'].where(df['order_error'] == string)

            fig = px.scatter(fig4_df, x=fig4_df.index, y=fig4_df.columns, template='plotly', title='Order Data')
            fig.update_layout(xaxis_title='Datetime', yaxis_title=None, showlegend=False)

        graphs.append(dcc.Graph(figure=fig, style={'width': '100%'}))

    return graphs


@app.callback(
    Output('button-press-text', 'children'),
    Input('data-store', 'data'),
    Input('submit-reload', 'n_clicks'))
def update_text(data, n_clicks):
    _ = n_clicks
    df = pd.read_json(data, orient='split')
    return f"Data loaded up to {df.iloc[-1].name} (UTC)"


@app.callback(
    Output('data-store', 'data'),
    Input('submit-reload', 'n_clicks'))
def update_data(n_clicks):
    _ = n_clicks
    df = query_last_days(TIMESTREAM_CLIENT, DATABASE_NAME, TABLE_NAME, DAYS)
    for col in ["close", "12h_close_mean", "desired_op_pct", "pfma"]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df["12h_close_mean"] = df['close'].rolling(720).mean()
    df["12h_close_std"] = df['close'].rolling(720).std()
    df["12h_close_pos_std"] = (df['close'] - df["12h_close_mean"]).where(
        df['close'] > df["12h_close_mean"]).fillna(0).pow(2).rolling(720, min_periods=1).mean().apply(np.sqrt)
    df["12h_close_neg_std"] = (df['close'] - df["12h_close_mean"]).where(
        df['close'] < df["12h_close_mean"]).fillna(0).pow(2).rolling(720, min_periods=1).mean().apply(np.sqrt)
    df["12h_close_cv_pct"] = 100 * df['12h_close_std'] / df["12h_close_mean"]
    df["12h_close_pos_cv_pct"] = 100 * df['12h_close_pos_std'] / df["12h_close_mean"]
    df["12h_close_neg_cv_pct"] = 100 * df['12h_close_neg_std'] / df["12h_close_mean"]
    return df.to_json(orient='split')


if __name__ == '__main__':
    app.run_server(port=80, debug=False, host="0.0.0.0")
