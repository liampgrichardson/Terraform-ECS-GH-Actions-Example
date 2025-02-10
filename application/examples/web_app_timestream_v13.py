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

# External stylesheet for a modern look
app.css.append_css({"external_url": "https://cdnjs.cloudflare.com/ajax/libs/semantic-ui/2.4.1/semantic.min.css"})

app.layout = html.Div([
    html.Div(
        className="header-container",
        children=[
            html.H1("Dynamic Data Graph", className="ui header"),
            html.P("Select columns to display on the graph.", className="ui sub header"),
        ],
        style={
            "textAlign": "center", "backgroundColor": "#1E1E1E", "color": "#FFD700",
            "padding": "30px", "borderBottom": "3px solid #FFD700",
            "borderRadius": "5px"
        },
    ),

    html.Div(
        className="ui segment",
        children=[
            dcc.Tabs(id='tabs', value='graph-tab', children=[
                dcc.Tab(label='Data Plot', value='graph-tab', className='ui blue tab'),
                dcc.Tab(label='News Headlines', value='news-tab', className='ui blue tab')
            ]),

            html.Div(id='tabs-content', className='ui padded segment')
        ],
        style={"margin": "20px"}
    )
])

@app.callback(
    Output('tabs-content', 'children'),
    Input('tabs', 'value')
)
def render_content(tab):
    if tab == 'graph-tab':
        return html.Div([
            dcc.Graph(id='multi-axis-graph', config={'displayModeBar': True}, style={"borderRadius": "5px"}),
            dcc.Dropdown(id='column-selector', multi=True, placeholder="Select columns", value=["close"], className="ui dropdown"),
            dcc.Store(id='data-store', data=None)
        ], className="ui raised segment")
    elif tab == 'news-tab':
        return html.Div([
            html.H3("Latest News Headlines", className="ui header"),
            html.Ul([html.Li("News item 1"), html.Li("News item 2"), html.Li("News item 3")], className="ui list")
        ], className="ui raised segment")

@app.callback(
    [Output('multi-axis-graph', 'figure'), Output('column-selector', 'options'),
     Output('data-store', 'data')],
    [Input('column-selector', 'value')]
)
def update_graph_and_data(selected_columns):
    df = query_last_days(timestream_client, database_name, table_name, days)
    df = df.apply(pd.to_numeric, errors='coerce').dropna(axis=1, how='all')

    options = [{'label': col, 'value': col} for col in df.select_dtypes(include=[np.number]).columns]
    fig = go.Figure()

    if selected_columns:
        y_axes = {'yaxis': {'title': selected_columns[0]}}
        for i, col in enumerate(selected_columns):
            fig.add_trace(go.Scatter(x=df.index, y=df[col], mode='lines', name=col, yaxis=f'y{i + 1}'))
            if i > 0:
                y_axes[f'yaxis{i + 1}'] = {'title': col, 'anchor': 'free', 'overlaying': 'y', 'autoshift': True}
        fig.update_layout(xaxis={'title': "Datetime", 'type': 'date'}, **y_axes)

    if selected_columns and len(selected_columns) >= 4:
        options = [{'label': opt['label'], 'value': opt['value'], 'disabled': True} for opt in options]

    return fig, options, df.to_json(orient='split')

if __name__ == '__main__':
    app.run_server(port=80, debug=False, host="0.0.0.0")
