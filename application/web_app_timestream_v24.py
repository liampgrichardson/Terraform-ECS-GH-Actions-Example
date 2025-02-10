from dash import Dash, dcc, html, Input, Output
import plotly.graph_objects as go
import plotly.io as pio
import pandas as pd
import numpy as np
import boto3
import dash_auth
from app_helpers.get_from_db import query_last_days

# Define authorized users
VALID_USERNAME_PASSWORD_PAIRS = {
    "TradeAppUser": "TradeApp2025"
}

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
    "rgba(174, 199, 232, 0.3)",
    "#005b96",  # Deep Blue
    "#539ecd"   # Soft Blue
]

# Neutral background colour
neutral_bg_color = "#f4f4f9"  # Soft neutral background for better contrast
dark_blue = "#333333"  # Darker text for readability

# Initialize the Dash app
app = Dash(__name__)
auth = dash_auth.BasicAuth(app, VALID_USERNAME_PASSWORD_PAIRS)

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
                dcc.Tab(label='Strategy View', value='graph-tab', style={
                    "color": dark_blue,
                    "border": "none"
                }, selected_style={
                    "backgroundColor": 'rgba(0,0,0,0)',
                    "color": dark_blue,
                    "border": "none",
                }),
                dcc.Tab(label='Information Feed View', value='news-tab', style={
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
            "margin": "20px",
            "marginTop": "20px",
            "backgroundColor": custom_blue_colors[2],
        }
    ),

    # Footer Section
    html.Div(
        className="footer-container",
        children=[
            html.P("Developed by Liam Richardson - 2025", style={"color": dark_blue, "textAlign": "center"}),
            html.P("For inquiries, contact: liampgrichardson@gmail.com", style={"color": dark_blue, "textAlign": "center"}),
            html.A("Connect on LinkedIn", href="https://www.linkedin.com/in/liam-richardson/", target="_blank",
                   style={"color": dark_blue, "textAlign": "center", "display": "block"})
        ],
        style={
            "textAlign": "center", "backgroundColor": custom_blue_colors[2], "color": dark_blue,
            "padding": "10px", "borderTop": f"3px solid {dark_blue}", "borderRadius": "15px", "marginTop": "20px"
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
                html.Li("News item 3", style={"color": dark_blue}),
            ], className="ui list"),
            html.H3("Market Trends", className="ui header", style={"color": dark_blue}),
            html.Ul([
                html.Li("Market Trend item 1", style={"color": dark_blue}),
                html.Li("Market Trend item 2", style={"color": dark_blue}),
                html.Li("Market Trend item 3", style={"color": dark_blue}),
            ], className="ui list"),
            html.H3("Upcoming Events", className="ui header", style={"color": dark_blue}),
            html.Ul([
                html.Li("Upcoming Event item 1", style={"color": dark_blue}),
                html.Li("Upcoming Event item 2", style={"color": dark_blue}),
                html.Li("Upcoming Event item 3", style={"color": dark_blue})
            ], className="ui list"),
            html.H3("Investment Trends", className="ui header", style={"color": dark_blue}),
            html.Ul([
                html.Li("Investment Trend item 1", style={"color": dark_blue}),
                html.Li("Investment Trend item 2", style={"color": dark_blue}),
                html.Li("Investment Trend item 3", style={"color": dark_blue})
            ], className="ui list")
        ], className="ui raised segment")


@app.callback(
    [Output('multi-axis-graph', 'figure'), Output('column-selector', 'options'),
     Output('data-store', 'data')],
    [Input('column-selector', 'value')]
)
def update_graph_and_data(selected_columns):
    print("going to query_last_days")
    df = query_last_days(timestream_client, database_name, table_name, days)
    print("got query")
    print(f"len(df): {len(df)}")
    print(f"len(df.columns): {len(df.columns)}")
    print(f"df.iloc[-5:]): {df.iloc[-5:]}")
    df = df.apply(pd.to_numeric, errors='coerce').dropna(axis=1, how='all')

    options = [{'label': col.lower(), 'value': col} for col in df.select_dtypes(include=[np.number]).columns]
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
        margin=dict(l=40, r=40, t=60, b=60, pad=0),
        showlegend=True
    )
    print("going to return update_graph_and_data")
    return fig, options, df.to_json(orient='split')


if __name__ == '__main__':
    app.run_server(port=80, debug=False, host="0.0.0.0")
