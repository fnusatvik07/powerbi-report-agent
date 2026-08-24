"""Deterministic example: build the IPL cricket dashboard from a ReportSpec.

Run it:
    python examples/cricket_spec.py
It writes a PBIP project to ./build/CricketAnalytics and validates it. Publish with:
    pbi-report-agent publish ./build/CricketAnalytics CricketAnalytics "My workspace.Personal"
"""

import os

from pbi_report_agent import Column, Measure, Model, Page, ReportSpec, Visual, generate, validate

PLAYERS = [
    ["Virat Sharma", "Bengaluru", "Batter", 14, 620, 2, 148.5, 28],
    ["KL Reddy", "Bengaluru", "Batter", 14, 480, 0, 138.0, 19],
    ["Yuzvendra Chahal", "Bengaluru", "Bowler", 14, 20, 21, 90.0, 1],
    ["Rohit Menon", "Mumbai", "Batter", 14, 540, 0, 139.2, 24],
    ["Jasprit Singh", "Mumbai", "Bowler", 14, 45, 24, 110.0, 2],
    ["Hardik Desai", "Mumbai", "All-rounder", 13, 300, 12, 145.0, 16],
    ["MS Rao", "Chennai", "Batter", 13, 410, 0, 135.6, 18],
    ["Ravindra Patel", "Chennai", "All-rounder", 14, 380, 15, 142.1, 20],
    ["Ruturaj G", "Chennai", "Batter", 14, 590, 0, 140.2, 22],
    ["Shubman Gupta", "Gujarat", "Batter", 14, 700, 0, 151.3, 30],
    ["Rashid Khan", "Gujarat", "Bowler", 14, 90, 27, 155.0, 6],
    ["Mohammed Siraj", "Gujarat", "Bowler", 14, 15, 19, 85.0, 0],
]

model = Model(
    table="Players",
    columns=[
        Column("Player", "text"), Column("Team", "text"), Column("Role", "text"),
        Column("Matches", "int64", "sum"), Column("Runs", "int64", "sum"),
        Column("Wickets", "int64", "sum"), Column("StrikeRate", "double", "average"),
        Column("Sixes", "int64", "sum"),
    ],
    rows=PLAYERS,
    measures=[
        Measure("Total Runs", "SUM(Players[Runs])", "#,##0"),
        Measure("Total Wickets", "SUM(Players[Wickets])", "#,##0"),
        Measure("Total Sixes", "SUM(Players[Sixes])", "#,##0"),
        Measure("Avg Strike Rate", "AVERAGE(Players[StrikeRate])", "#,##0.0"),
        Measure("Players", "DISTINCTCOUNT(Players[Player])", "0"),
    ],
)

ACCENTS = ["#F4A259", "#5B8E7D", "#BC4B51", "#8CB369", "#3D5A80"]
cards = ["Total Runs", "Total Wickets", "Total Sixes", "Avg Strike Rate", "Players"]

overview = Page("Overview", visuals=[
    Visual("shape", 0, 0, 1280, 64, color="#0B2545"),
    Visual("textbox", 24, 12, 1000, 50, text="IPL 2026 - Cricket Analytics Dashboard"),
    *[Visual("cardVisual", 24 + i * 248, 80, 236, 92,
             roles={"Data": [{"measure": m}]}, color=ACCENTS[i]) for i, m in enumerate(cards)],
    Visual("slicer", 24, 196, 236, 150, roles={"Values": ["Team"]}, title="Team"),
    Visual("slicer", 24, 356, 236, 150, roles={"Values": ["Role"]}, title="Role"),
    Visual("clusteredBarChart", 284, 196, 470, 310,
           roles={"Category": ["Player"], "Y": [{"measure": "Total Runs"}]}),
    Visual("donutChart", 770, 196, 486, 310,
           roles={"Category": ["Team"], "Y": [{"measure": "Total Sixes"}]}),
    Visual("pageNavigator", 284, 520, 300, 44),
])

bowling = Page("Bowling & Stats", visuals=[
    Visual("shape", 0, 0, 1280, 64, color="#0B2545"),
    Visual("textbox", 24, 12, 1000, 50, text="Bowling & Team Statistics"),
    Visual("clusteredColumnChart", 24, 88, 600, 300,
           roles={"Category": ["Team"], "Y": [{"measure": "Total Wickets"}]}),
    Visual("lineChart", 644, 88, 612, 300,
           roles={"Category": ["Player"], "Y": [{"measure": "Avg Strike Rate"}]}),
    Visual("pivotTable", 24, 404, 1232, 296,
           roles={"Rows": ["Team"],
                  "Values": [{"measure": m} for m in ["Total Runs", "Total Wickets", "Total Sixes", "Players"]]}),
    Visual("pageNavigator", 24, 620, 300, 44),
])

spec = ReportSpec(name="CricketAnalytics", model=model, pages=[overview, bowling])

if __name__ == "__main__":
    pbip = generate(spec, os.path.abspath("./build/CricketAnalytics"))
    print("generated:", pbip)
    print("validation:", validate(pbip))
