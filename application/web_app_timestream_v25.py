from dash import Dash, dcc, html, Input, Output
import plotly.graph_objects as go
import plotly.io as pio
import pandas as pd
import numpy as np
import dash_auth
from app_helpers.get_from_db import query_db

# Define authorized users
VALID_USERNAME_PASSWORD_PAIRS = {
    "TAUser": "TA2025"
}

# Set Plotly Theme
plotly_theme = "plotly"
pio.templates.default = plotly_theme

# Define a custom blue colour palette
custom_blue_colors = [
    "#1f77b4", "#aec7e8", "rgba(174, 199, 232, 0.3)", "#005b96", "#539ecd"
]

# Neutral background colour
neutral_bg_color = "#f4f4f9"
dark_blue = "#333333"

# Initialize the Dash app
app = Dash(__name__)
auth = dash_auth.BasicAuth(app, VALID_USERNAME_PASSWORD_PAIRS)

app.title = "Trading Application"

app.layout = html.Div([
    dcc.Interval(id='interval-component', interval=600 * 1000, n_intervals=0),  # Query every 10 minutes
    dcc.Store(id='data-store', data=None),  # Store queried data in memory

    html.Div(
        className="header-container",
        children=[
            html.H1("Trading Application Dashboard", className="ui header", style={"color": dark_blue}),
            html.P("Select View", className="ui sub header", style={"color": dark_blue}),
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
                dcc.Tab(label='Strategy View', value='graph-tab', style={"color": dark_blue, "border": "none"},
                        selected_style={"backgroundColor": 'rgba(0,0,0,0)', "color": dark_blue, "border": "none"}),
                dcc.Tab(label='Information Feed View', value='news-tab', style={"color": dark_blue, "border": "none"},
                        selected_style={"backgroundColor": 'rgba(0,0,0,0)', "color": dark_blue, "border": "none"})
            ], style={}),

            html.Div(id='tabs-content', className='ui padded segment', style={"padding": "10px"})
        ],
        style={"margin": "20px", "marginTop": "20px", "backgroundColor": custom_blue_colors[2]}
    ),

    html.Div(
        className="footer-container",
        children=[
            html.P("Developed by Liam Richardson - 2025", style={"color": dark_blue, "textAlign": "center"}),
            html.P("For inquiries, contact: liampgrichardson@gmail.com",
                   style={"color": dark_blue, "textAlign": "center"}),
            html.A("Connect on LinkedIn", href="https://www.linkedin.com/in/liam-richardson/", target="_blank",
                   style={"color": dark_blue, "textAlign": "center", "display": "block"})
        ],
        style={
            "textAlign": "center", "backgroundColor": custom_blue_colors[2], "color": dark_blue,
            "padding": "10px", "borderTop": f"3px solid {dark_blue}", "borderRadius": "15px", "marginTop": "20px"
        }
    )
])


# Callback to fetch data every minute and store it in memory
@app.callback(
    Output('data-store', 'data'),
    Input('interval-component', 'n_intervals')
)
def fetch_data(n):
    _ = n
    print("Fetching data from database...")
    df = query_db()
    df = df.apply(pd.to_numeric, errors='coerce').dropna(axis=1, how='all')
    return df.to_json(orient='split')  # Store DataFrame as JSON


# Callback to update content when switching tabs
@app.callback(
    Output('tabs-content', 'children'),
    Input('tabs', 'value')
)
def render_content(tab):
    if tab == 'graph-tab':
        return html.Div([
            dcc.Graph(id='multi-axis-graph', config={'displayModeBar': True},
                      figure={'layout': {'plot_bgcolor': 'rgba(0,0,0,0)', 'paper_bgcolor': 'rgba(0,0,0,0)'}}),
            dcc.Dropdown(id='column-selector', multi=True, placeholder="Select columns",
                         value=["close"],
                         className="ui dropdown"),
        ], className="ui raised segment")
    elif tab == 'news-tab':
        return html.Div([
            html.H3("Latest News Headlines", className="ui header", style={"color": dark_blue}),
            html.Ul([html.Li(f"News item {i+1}", style={"color": dark_blue}) for i in range(3)],
                    className="ui list"),
            html.H3("Market Trends", className="ui header", style={"color": dark_blue}),
            html.Ul([html.Li(f"Market Trend {i+1}", style={"color": dark_blue}) for i in range(3)],
                    className="ui list"),
            html.H3("Upcoming Events", className="ui header", style={"color": dark_blue}),
            html.Ul([html.Li(f"Upcoming Event {i+1}", style={"color": dark_blue}) for i in range(3)],
                    className="ui list"),
            html.H3("Investment Trends", className="ui header", style={"color": dark_blue}),
            html.Ul([html.Li(f"Investment Trend {i+1}", style={"color": dark_blue}) for i in range(3)],
                    className="ui list"),
        ], className="ui raised segment")


# Callback to update graph and dropdown from stored data
@app.callback(
    [Output('multi-axis-graph', 'figure'),
     Output('column-selector', 'options')],
    [Input('column-selector', 'value'),
     Input('data-store', 'data')]  # Use stored data instead of re-querying
)
def update_graph(selected_columns, data_json):
    if data_json is None:
        return go.Figure(), []

    df = pd.read_json(data_json, orient='split')

    options = [{'label': col.lower(), 'value': col} for col in df.select_dtypes(include=[np.number]).columns]
    fig = go.Figure()

    if selected_columns:
        y_axes = {'yaxis': {'title': selected_columns[0]}}
        for i, col in enumerate(selected_columns):
            fig.add_trace(go.Scatter(x=df.index, y=df[col], mode='lines', name=col, yaxis=f'y{i + 1}'))
            if i > 0:
                y_axes[f'yaxis{i + 1}'] = {'title': col, 'anchor': 'free', 'overlaying': 'y', 'autoshift': True}
        fig.update_layout(template=plotly_theme, xaxis={'title': "Datetime", 'type': 'date'}, **y_axes)

    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=40, r=40, t=60, b=60, pad=0),
        showlegend=True
    )

    return fig, options


if __name__ == '__main__':
    app.run_server(port=80, debug=False, host="0.0.0.0")
