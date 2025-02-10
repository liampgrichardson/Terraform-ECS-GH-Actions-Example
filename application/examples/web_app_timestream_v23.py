from dash import Dash, dcc, html, Input, Output
import plotly.graph_objects as go
import plotly.io as pio
import pandas as pd
import numpy as np
import boto3
from app_helpers.get_from_db import query_last_days

# Configuration for Timestream
timestream_client = boto3.client("timestream-query", region_name="eu-west-1")
database_name = "my-timestream-database"
table_name = "TestTable"
days = 7

# Set Plotly Theme
plotly_theme = "plotly"
pio.templates.default = plotly_theme

# Define a custom blue colour palette (sticking only to blue shades)
custom_blue_colors = [
    "#1f77b4",  # Blue (main)
    "#aec7e8",  # Light Blue
    "rgba(174, 199, 232, 0.2)",
    "#005b96",  # Deep Blue
    "#539ecd"   # Soft Blue
]

# Neutral background colour
neutral_bg_color = "#f4f4f9"  # Soft neutral background for better contrast
dark_blue = "#333333"  # Darker text for readability

app = Dash(__name__)
app.title = "Dynamic Data Graph"

app.layout = html.Div([
    html.Div(
        className="header-container",
        children=[
            html.H1("Dynamic Data Graph", className="ui header", style={"color": dark_blue}),
            html.P("Select columns to display on the graph.", className="ui sub header", style={"color": dark_blue}),
        ],
        style={
            "textAlign": "center", "backgroundColor": custom_blue_colors[2], "color": dark_blue,
            "padding": "30px", "borderBottom": f"3px solid {dark_blue}", "borderRadius": "15px"
        },
    ),

    html.Div(
        className="ui segment",
        children=[
            dcc.Tabs(id='tabs', value='graph-tab', children=[
                dcc.Tab(label='Asset View', value='graph-tab', style={
                    "color": dark_blue,
                    "border": "none"
                }, selected_style={
                    "backgroundColor": 'rgba(0,0,0,0)',
                    "color": dark_blue,
                    "border": "none",
                }),
                dcc.Tab(label='Information View', value='news-tab', style={
                    "color": dark_blue,
                    "border": "none"
                }, selected_style={
                    "backgroundColor": 'rgba(0,0,0,0)',
                    "color": dark_blue,
                    "border": "none",
                })
            ], style={}),

            html.Div(id='tabs-content', className='ui padded segment',
                     style={"padding": "10px"
                     })
        ],
        style={
            "margin": "10px",
            "marginTop": "20px",
            "backgroundColor": custom_blue_colors[2],
        }
    ),

    # Footer Section
    html.Div(
        className="footer-container",
        children=[
            html.P("Developed by Liam Richardson - 2025", style={"color": dark_blue, "textAlign": "center"}),
            html.P("For inquiries, contact: your.email@example.com", style={"color": dark_blue, "textAlign": "center"})
        ],
        style={
            "textAlign": "center", "backgroundColor": custom_blue_colors[2], "color": dark_blue,
            "padding": "20px", "borderTop": f"3px solid {dark_blue}", "borderRadius": "15px", "marginTop": "20px"
        }
    )
])


@app.callback(
    Output('tabs-content', 'children'),
    Input('tabs', 'value')
)
def render_content(tab):
    if tab == 'graph-tab':
        return html.Div([
            dcc.Graph(id='multi-axis-graph', config={'displayModeBar': True},
                      figure={'layout': {'plot_bgcolor': 'rgba(0,0,0,0)',
                                         'paper_bgcolor': 'rgba(0,0,0,0)'}},
                      style={}
                      ),
            dcc.Dropdown(id='column-selector', multi=True, placeholder="Select columns", value=["close"],
                         className="ui dropdown",
                         style={}
                         ),
            dcc.Store(id='data-store', data=None)
        ], className="ui raised segment")
    elif tab == 'news-tab':
        return html.Div([
            html.H3("Latest News Headlines", className="ui header", style={"color": dark_blue}),
            html.Ul([
                html.Li("News item 1", style={"color": dark_blue}),
                html.Li("News item 2", style={"color": dark_blue}),
                html.Li("News item 3", style={"color": dark_blue})
            ], className="ui list")
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
        fig.update_layout(template=plotly_theme, xaxis={'title': "Datetime", 'type': 'date'}, **y_axes)

    if selected_columns and len(selected_columns) >= 4:
        options = [{'label': opt['label'], 'value': opt['value'], 'disabled': True} for opt in options]

    # Set background colors
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',  # Inside the graph
        paper_bgcolor='rgba(0,0,0,0)',  # Outside the graph
        margin=dict(l=40, r=40, t=60, b=60, pad=0)
    )

    return fig, options, df.to_json(orient='split')


if __name__ == '__main__':
    app.run_server(port=80, debug=False, host="0.0.0.0")
