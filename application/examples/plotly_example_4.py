import pandas as pd
import plotly.graph_objects as go

# Sample DataFrame
data = {
    "yaxis1": [4, 5, 6, None, None, None, None],
    "yaxis2": [None, 40, 50, 60, None, None, None],
    "yaxis3": [None, None, 400, 500, 600, None, None],
    "yaxis4": [None, None, None, None, 6000, 7000, 8000],
    "yaxis5": [3, 4, 5, None, 6000, 7000, 8000]
}
df = pd.DataFrame(data, index=[1, 2, 3, 4, 5, 6, 7])

fig = go.Figure()

# Add traces dynamically based on DataFrame
for i, column in enumerate(df.columns):
    y_values = df[column]
    fig.add_trace(go.Scatter(x=y_values.index, y=y_values.values, name=f"{column} data", yaxis=f"y{i+1}" if i > 0 else "y"))

# Initialise y axes dictionary
# Then dynamically update y-axis layout
y_axes = {
    'yaxis': dict(title="yaxis title")
}

# Add extra y-axes based on the number of traces
for i in range(2, len(df.columns)+1):
    y_axes[f'yaxis{i}'] = dict(
        title=f"yaxis{i} title",
        anchor="free",
        overlaying="y",
        autoshift=True
    )

fig.update_layout(
    xaxis=dict(domain=[0, 1]),
    **y_axes,  # Unpack y_axes dictionary dynamically
    title_text="Shifting y-axes with autoshift",
)

fig.show()
