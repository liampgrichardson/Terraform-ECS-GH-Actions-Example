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


def load_df():
    np.random.seed(42)  # Ensures reproducibility
    date_range = pd.date_range(start="2023-01-01", periods=10080, freq="T")  # 1 week of minute data
    close_prices = np.cumsum(np.random.randn(len(date_range))) + 100  # Simulated price data

    data = {
        "close": close_prices,
        "pfma": pd.Series(close_prices).rolling(60).mean(),  # Simulated moving average
        "12h_close_mean": pd.Series(close_prices).rolling(720).mean(),  # 12-hour rolling mean
        "desired_op_pct": np.random.rand(len(date_range)),  # Simulated percentage data
        "order_error": np.random.choice(["Error A", "Error B", None], size=len(date_range)),  # Simulated labels
    }

    df = pd.DataFrame(data, index=date_range)
    return df


def query_last_days(timestream_client, database_name, table_name, days):

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


layout = html.Div([
    html.Div(
        className="header-container",
        children=[
            html.H1(
                children='BTC Trading Bot Monitor',
                className="app-title",
            ),
            html.P('A web app for showing live metrics from the bot at every minute on the lookback range',
                   className="app-description"),
        ],
    ),

    html.Div(
        children=[html.Br()]
    ),

    html.Div(
        className="graph-container",
        children=[
            dcc.Graph(id='price-data',
                      figure={'layout': {'title': 'Price Data'}},
                      config={'displayModeBar': False}),
            dcc.Graph(id='volatility-data',
                      figure={'layout': {'title': 'Volatility Data'}},
                      config={'displayModeBar': False}),
            dcc.Graph(id='position-data',
                      figure={'layout': {'title': 'Position Data'}},
                      config={'displayModeBar': False}),
            dcc.Graph(id='order-data',
                      figure={'layout': {'title': 'Label Data'}},
                      config={'displayModeBar': False})
        ]
    ),

    html.Div(
        children=[html.Br()]
    ),

    html.Div([
        html.Div(
            children=[
                html.P('Lookback range', style={'padding-left': '1%'}),
                dcc.RangeSlider(
                    id='range-slider',
                    min=-10080,
                    max=0,
                    step=10,
                    value=[-10080, 0],
                    marks={i: {"label": f"{int(24 * i / 1440)}h"} for i in range(-10080, 1, 1440)})],
            style={
                'width': '80%',
                'display': 'flex',
                'flex-direction': 'column',
                'justify-content': 'center',
                'padding': '1%',
            },
        ),
        html.Div(
            children=[
                html.P(id='button-press-text'),
                html.Button('Reload', id='submit-reload', n_clicks=0),
            ],
            style={
                'width': '20%',
                'display': 'flex',
                'flex-direction': 'column',
                'justify-content': 'center',
                'align-items': 'center',
                'padding-right': '1%',
            },
        ),
    ],
        style={
            'width': '100%',
            'display': 'flex',
            "flex-direction": "row",
            'justify-content': 'center',
            'align-items': 'center',
            'position': 'sticky',
            'bottom': '1%',
            "margin": "auto",
            'background-color': 'white',
            'border-radius': '10px',
            "box-shadow": "0 2px 4px rgba(0, 0, 0, 0.2)",
        },
    ),

    dcc.Store(id='data-store', data=None)

],)


app.layout = layout


@app.callback(
    Output('price-data', 'figure'),
    Output('volatility-data', 'figure'),
    Output('position-data', 'figure'),
    Output('order-data', 'figure'),  # New output
    Input('data-store', 'data'),
    Input('range-slider', 'value'),
    Input('submit-reload', 'n_clicks'))
def update_price_figures(data, slider_range, n_clicks):
    _ = n_clicks  # n_clicks not used
    df = pd.read_json(data, orient='split')
    start = df.index[max(slider_range[0] - 1, -len(df))]
    stop = df.index[max(slider_range[1] - 1, -len(df))]
    df = df.loc[start:stop]

    fig1_cols = ["close", "pfma", "12h_close_mean"]
    fig1 = px.line(df,
                   x=df.index,
                   y=np.intersect1d(fig1_cols, df.columns),
                   template='plotly')
    fig1.update_layout(transition_duration=100, xaxis_title='Datetime', title='Price Data', yaxis_title=None)
    fig1.update_layout(legend=dict(orientation="v", yanchor="auto", xanchor="auto", x=0.01, y=0.96, title=None))
    fig1.update_yaxes(automargin=False)

    fig2_cols = ["12h_close_cv_pct", "12h_close_pos_cv_pct", "12h_close_neg_cv_pct"]
    fig2 = px.line(df,
                   x=df.index,
                   y=np.intersect1d(fig2_cols, df.columns),
                   template='plotly')
    fig2.update_layout(transition_duration=100, xaxis_title='Datetime', title='Volatility Data', yaxis_title=None)
    fig2.update_layout(legend=dict(orientation="v", yanchor="auto", xanchor="auto", x=0.01, y=0.96, title=None))
    fig2.update_yaxes(automargin=False)

    fig3_cols = ["desired_op_pct"]
    fig3 = px.line(df,
                   x=df.index,
                   y=np.intersect1d(fig3_cols, df.columns),
                   template='plotly')
    fig3.update_layout(transition_duration=100, xaxis_title='Datetime', title='Position Data', yaxis_title=None,
                       yaxis_range=[0, 1])
    fig3.update_layout(legend=dict(orientation="v", yanchor="auto", xanchor="auto", x=0.01, y=0.96, title=None))
    fig3.update_yaxes(automargin=False)

    fig4_df = pd.DataFrame(index=df.index.copy())
    unique_strings = set(df['order_error'].dropna())
    for string in unique_strings:
        fig4_df[string] = df['order_error'].where(df['order_error'] == string)

    fig4 = px.scatter(fig4_df,
                      x=fig4_df.index,
                      y=fig4_df.columns,  # Assuming 'label' is the column name for the labels
                      template='plotly')
    fig4.update_layout(transition_duration=100, xaxis_title='Datetime', title='Order Data', yaxis_title=None,
                       xaxis_range=[df.index[0], df.index[-1]])
    fig4.update_layout(legend=dict(orientation="v", yanchor="auto", xanchor="auto", x=0.01, y=0.96, title=None))
    fig4.update_yaxes(automargin=False, showticklabels=False)

    return fig1, fig2, fig3, fig4


@app.callback(
    Output('button-press-text', 'children'),
    Input('data-store', 'data'),
    Input('submit-reload', 'n_clicks'))
def update_text(data, n_clicks):
    _ = n_clicks  # n_clicks not used
    df = pd.read_json(data, orient='split')
    return f"Loaded to \n{df.iloc[-1].name} (UTC)"


@app.callback(
    Output('data-store', 'data'),
    Input('submit-reload', 'n_clicks'))
def update_data(n_clicks):
    _ = n_clicks  # n_clicks not used
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
