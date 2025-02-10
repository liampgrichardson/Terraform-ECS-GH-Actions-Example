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

plotly_bg_color = "#1E1E1E"
plotly_text_color = "#F0F0F0"

app.layout = html.Div([
    html.Div(
        className="header-container",
        children=[
            html.H1("Dynamic Data Graph", className="ui header", style={"color": plotly_text_color}),
            html.P("Select columns to display on the graph.", className="ui sub header", style={"color": plotly_text_color}),
        ],
        style={
            "textAlign": "center", "backgroundColor": plotly_bg_color, "color": plotly_text_color,
            "padding": "30px", "borderBottom": "3px solid #FFD700",
            "borderRadius": "15px"
        },
    ),

    html.Div(
        className="ui segment",
        children=[
            dcc.Tabs(id='tabs', value='graph-tab', children=[
                dcc.Tab(label='Data Plot', value='graph-tab', className='ui tab', style={"borderRadius": "10px", "backgroundColor": plotly_bg_color, "color": plotly_text_color}),
                dcc.Tab(label='News Headlines', value='news-tab', className='ui tab', style={"borderRadius": "10px", "backgroundColor": plotly_bg_color, "color": plotly_text_color})
            ], style={"borderRadius": "15px", "overflow": "hidden", "backgroundColor": plotly_bg_color}),

            html.Div(id='tabs-content', className='ui padded segment', style={"borderRadius": "15px", "backgroundColor": plotly_bg_color, "color": plotly_text_color})
        ],
        style={"margin": "20px", "borderRadius": "15px", "backgroundColor": plotly_bg_color}
    )
])

@app.callback(
    Output('tabs-content', 'children'),
    Input('tabs', 'value')
)
def render_content(tab):
    if tab == 'graph-tab':
        return html.Div([
            dcc.Graph(id='multi-axis-graph', config={'displayModeBar': True}, style={"borderRadius": "15px"}),
            dcc.Dropdown(id='column-selector', multi=True, placeholder="Select columns", value=["close"], className="ui dropdown", style={"borderRadius": "15px"}),
            dcc.Store(id='data-store', data=None)
        ], className="ui raised segment", style={"borderRadius": "15px", "backgroundColor": plotly_bg_color, "color": plotly_text_color})
    elif tab == 'news-tab':
        return html.Div([
            html.H3("Latest News Headlines", className="ui header", style={"color": plotly_text_color}),
            html.Ul([html.Li("News item 1", style={"color": plotly_text_color}), html.Li("News item 2", style={"color": plotly_text_color}), html.Li("News item 3", style={"color": plotly_text_color})], className="ui list")
        ], className="ui raised segment", style={"borderRadius": "15px", "backgroundColor": plotly_bg_color})

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
