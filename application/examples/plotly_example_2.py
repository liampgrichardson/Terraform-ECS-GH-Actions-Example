import pandas as pd
import plotly.graph_objects as go

# Sample DataFrame
data = {
    "yaxis1": [4, 5, 6, None, None, None, None],
    "yaxis2": [None, 40, 50, 60, None, None, None],
    "yaxis3": [None, None, 400, 500, 600, None, None],
    "yaxis4": [None, None, None, None, 6000, 7000, 8000]
}
df = pd.DataFrame(data, index=[1, 2, 3, 4, 5, 6, 7])

fig = go.Figure()

# Add traces with x-axis from DataFrame index
fig.add_trace(go.Scatter(
    x=df.index,
    y=df["yaxis1"],
    name="yaxis1 data"
))

fig.add_trace(go.Scatter(
    x=df.index,
    y=df["yaxis2"],
    name="yaxis2 data",
    yaxis="y2"
))

fig.add_trace(go.Scatter(
    x=df.index,
    y=df["yaxis3"],
    name="yaxis3 data",
    yaxis="y3"
))

fig.add_trace(go.Scatter(
    x=df.index,
    y=df["yaxis4"],
    name="yaxis4 data",
    yaxis="y4"
))

# Create axis objects
fig.update_layout(
    yaxis=dict(
        title=dict(
            text="yaxis title",
            font=dict(
                color="#1f77b4"
            )
        ),
        anchor="free",
        side="left",
    ),
    yaxis2=dict(
        title=dict(
            text="yaxis2 title",
            font=dict(
                color="#ff7f0e"
            )
        ),
        anchor="free",
        overlaying="y",
        side="left",
        position=0.05
    ),
    yaxis3=dict(
        title=dict(
            text="yaxis3 title",
            font=dict(
                color="#d62728"
            )
        ),
        anchor="x",
        overlaying="y",
        side="left",
        position=0.1
    ),
    yaxis4=dict(
        title=dict(
            text="yaxis4 title",
            font=dict(
                color="#9467bd"
            )
        ),
        anchor="free",
        overlaying="y",
        side="left",
        position=0.15
    )
)

# Create axis objects
fig.update_layout(
    xaxis=dict(
        domain=[0, 1]
    ),)

# Update layout properties
fig.update_layout(
    title_text="multiple y-axes example",
    # width=800,
)

fig.show()
