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
            html.Label("Select Data Columns:"),
            dcc.Checklist(id='column-selector', inline=True, inputStyle={"margin-right": "5px"}),
            html.Button("Reload Data", id="reload-button", n_clicks=0, className="reload-button"),
        ], style={"width": "25%", "padding": "10px", "backgroundColor": "#F0F0F0"}),

        html.Div([
            dcc.Graph(id='multi-axis-graph', config={'displayModeBar': False}),
        ], style={"width": "70%", "padding": "10px"}),
    ], style={"display": "flex", "justifyContent": "space-between"}),

    dcc.Store(id='data-store', data=None),
], style={"fontFamily": "Arial, sans-serif", "backgroundColor": "#E5E5E5"})


@app.callback(
    [Output('column-selector', 'options'), Output('data-store', 'data')],
    Input('reload-button', 'n_clicks')
)
def load_data(n_clicks):
    df = query_last_days(timestream_client, database_name, table_name, days)
    df = df.apply(pd.to_numeric, errors='coerce')
    df = df.dropna(axis=1, how='all')
    options = [{'label': col, 'value': col} for col in df.select_dtypes(include=[np.number]).columns]
    return options, df.to_json(orient='split')


@app.callback(
    Output('multi-axis-graph', 'figure'),
    [Input('column-selector', 'value'), Input('data-store', 'data')]
)
def update_graph(selected_columns, data):
    df = pd.read_json(data, orient='split')
    fig = go.Figure()

    if selected_columns:
        for i, col in enumerate(selected_columns):
            fig.add_trace(go.Scatter(x=df.index, y=df[col], mode='lines', name=col, yaxis=f'y{i + 1}'))

        layout = {
            'title': "Dynamic Data Plot",
            'xaxis': {'title': "Datetime", 'type': 'date'},
            'yaxis': {'title': selected_columns[0]},
        }

        for i, col in enumerate(selected_columns[1:], start=2):
            layout[f'yaxis{i}'] = {
                'title': col,
                'overlaying': 'y',
                'side': 'right' if i % 2 == 0 else 'left',
                'showgrid': False
            }

        fig.update_layout(**layout)

    return fig


if __name__ == '__main__':
    app.run_server(port=80, debug=False, host="0.0.0.0")
