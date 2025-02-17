from dash import Dash, dcc, html, Input, Output
import plotly.express as px
import pandas as pd
import numpy as np
import boto3
from botocore.exceptions import ClientError
from app_helpers.get_from_db import query_last_days

# Configuration for Timestream
TIMESTREAM_CLIENT = boto3.client("timestream-query", region_name="eu-west-1")
DATABASE_NAME = "my-timestream-database"  # Replace with your database name
TABLE_NAME = "TestTable"  # Replace with your table name
DAYS = 7  # Lookback range in days

app = Dash(__name__)
app.title = "BTC Trading Bot Monitor"
app.css.config.serve_locally = True

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
        className="graph-container",
        children=[
            dcc.Graph(id='price-data', config={'displayModeBar': False}),
            dcc.Graph(id='volatility-data', config={'displayModeBar': False}),
            dcc.Graph(id='position-data', config={'displayModeBar': False}),
            dcc.Graph(id='order-data', config={'displayModeBar': False}),
        ],
        style={
            "display": "flex",
            "flexDirection": "column",
            "gap": "20px",
            "padding": "20px",
            "backgroundColor": "#F9F9F9",
            "paddingBottom": "7.5%",  # Ensure enough space below the graphs
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
            style={"width": "75%", "padding": "10px"}
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
            "position": "fixed",  # Makes the bar fixed
            "bottom": "0",  # Aligns it to the bottom of the screen
            "left": "0",  # Stretches it across the entire width
            "right": "0",  # Stretches it across the entire width
            "zIndex": "1000",  # Ensures it stays above other elements
        }
    ),

    dcc.Store(id='data-store', data=None),
], style={"fontFamily": "Arial, sans-serif", "backgroundColor": "#E5E5E5"})


@app.callback(
    Output('price-data', 'figure'),
    Output('volatility-data', 'figure'),
    Output('position-data', 'figure'),
    Output('order-data', 'figure'),
    Input('data-store', 'data'),
    Input('range-slider', 'value'),
    Input('submit-reload', 'n_clicks'))
def update_price_figures(data, slider_range, n_clicks):
    _ = n_clicks
    df = pd.read_json(data, orient='split')
    start = df.index[max(slider_range[0] - 1, -len(df))]
    stop = df.index[max(slider_range[1] - 1, -len(df))]
    df = df.loc[start:stop]

    fig1_cols = ["close", "pfma", "12h_close_mean"]
    fig1 = px.line(df, x=df.index, y=np.intersect1d(fig1_cols, df.columns),
                   template='plotly', title='Price Data')
    fig1.update_layout(xaxis_title='Datetime', yaxis_title=None)

    fig2_cols = ["12h_close_cv_pct", "12h_close_pos_cv_pct", "12h_close_neg_cv_pct"]
    fig2 = px.line(df, x=df.index, y=np.intersect1d(fig2_cols, df.columns),
                   template='plotly', title='Volatility Data')
    fig2.update_layout(xaxis_title='Datetime', yaxis_title=None)

    fig3_cols = ["desired_op_pct"]
    fig3 = px.line(df, x=df.index, y=np.intersect1d(fig3_cols, df.columns),
                   template='plotly', title='Position Data')
    fig3.update_layout(xaxis_title='Datetime', yaxis_title=None)

    fig4_df = pd.DataFrame(index=df.index.copy())
    unique_strings = set(df['order_error'].dropna())
    for string in unique_strings:
        fig4_df[string] = df['order_error'].where(df['order_error'] == string)

    fig4 = px.scatter(fig4_df, x=fig4_df.index, y=fig4_df.columns, template='plotly', title='Order Data')
    fig4.update_layout(xaxis_title='Datetime', yaxis_title=None, showlegend=False)

    return fig1, fig2, fig3, fig4


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
