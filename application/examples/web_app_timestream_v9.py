from dash import Dash, dcc, html, Input, Output
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import boto3
from app_helpers.get_from_db import query_last_days

# Configuration for Timestream
timestream_client = boto3.client("timestream-query", region_name="eu-west-1")
database_name = "my-timestream-database"
table_name = "TestTable"
days = 7

app = Dash(__name__)
app.title = "Dynamic Data Graph"

app.layout = html.Div([
    html.Div(
        className="header-container",
        children=[
            html.H1("Dynamic Data Graph", className="app-title"),
            html.P("Select columns to display on the graph.", className="app-description"),
        ],
        style={
            "textAlign": "center", "backgroundColor": "#2D2D2D", "color": "white",
            "padding": "20px", "borderBottom": "4px solid #FFD700"
        },
    ),

    html.Div([
        html.Div([
            dcc.Graph(id='multi-axis-graph', config={'displayModeBar': False}),
        ], style={"width": "100%", "padding": "10px"}),
    ], style={"display": "flex", "justifyContent": "center"}),

    html.Div([
        html.Div([
            dcc.Dropdown(id='column-selector', multi=True, placeholder="Select columns"),
        ], style={"width": "100%"}),
    ], style={"display": "flex", "justifyContent": "center", "padding": "10px"}),

    html.Div(id="warning"),

    dcc.Store(id='data-store', data=None),
], style={"fontFamily": "Arial, sans-serif", "backgroundColor": "#E5E5E5"})


@app.callback(
    [Output('multi-axis-graph', 'figure'), Output('column-selector', 'options'), Output('warning', 'children'),
     Output('data-store', 'data')],
    [Input('column-selector', 'value')]
)
def update_graph_and_data(selected_columns):
    df = query_last_days(timestream_client, database_name, table_name, days)
    df = df.apply(pd.to_numeric, errors='coerce')
    df = df.dropna(axis=1, how='all')

    options = [{'label': col, 'value': col} for col in df.select_dtypes(include=[np.number]).columns]
    fig = go.Figure()
    warning_message = None

    if selected_columns:
        y_axes = {'yaxis': {'title': selected_columns[0]}}

        for i, col in enumerate(selected_columns):
            fig.add_trace(go.Scatter(x=df.index, y=df[col], mode='lines', name=col, yaxis=f'y{i + 1}'))

            if i > 0:
                y_axes[f'yaxis{i + 1}'] = {
                    'title': col,
                    'anchor': 'free',
                    'overlaying': 'y',
                    'autoshift': True
                }

        fig.update_layout(
            title="Dynamic Data Plot",
            xaxis={'title': "Datetime", 'type': 'date'},
            **y_axes  # Unpacking dynamically generated y-axes
        )

    if selected_columns and len(selected_columns) >= 4:
        options = [{'label': opt['label'], 'value': opt['value'], 'disabled': True} for opt in options]
        warning_message = html.P("Limit of 4 selections reached.", style={"color": "red"})

    return fig, options, warning_message, df.to_json(orient='split')


if __name__ == '__main__':
    app.run_server(port=80, debug=False, host="0.0.0.0")
