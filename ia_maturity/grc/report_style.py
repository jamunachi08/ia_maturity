"""Presentation colors measured from the supplied GRC PDF, independent of scoring."""
from copy import deepcopy
import json
from pathlib import Path
SECTION_COLORS=json.loads((Path(__file__).parents[1]/"public"/"section-score-colors.json").read_text())

DEFAULT_RANGES=json.loads((Path(__file__).parents[1]/"public"/"section-color-ranges.json").read_text())

def section_score_color(score,ranges=None):
    value=float(score or 0)
    return next(row["color"] for row in reversed(ranges or DEFAULT_RANGES) if value>=row["min_score"])

PALETTE = {"Critical":"#B42318", "Low":"#BF530B", "Medium":"#9A6F00", "High":"#2D7A33", "Leading":"#1C5CA3"}

def report_context(context,ranges=None):
    result=deepcopy(context)
    ranges=result.get("section_color_ranges") or ranges or DEFAULT_RANGES
    result["section_color_ranges"]=deepcopy(ranges)
    result["section_scale"]=[{"from":row["min_score"],"width":(ranges[i+1]["min_score"] if i+1<len(ranges) else 100)-row["min_score"],"color":row["color"]} for i,row in enumerate(ranges)]
    boundaries=sorted({0,100}|{row["min_score"] for row in ranges})
    result["section_ticks"]=boundaries if len(boundaries)<=11 else [0,25,50,75,100]
    result["level_color"]=PALETTE.get(result.get("level") or result.get("level_label"),result.get("level_color","#586976"))
    for row in result.get("sections",[]):
        row["color"]=section_score_color(row.get("pct"),ranges)
    for row in result.get("scale",[]):
        row["color"]=PALETTE.get(row.get("level") or row.get("level_name") or row.get("label"),row.get("color","#586976"))
    result["ticks"] = sorted({0,100} | {float(row["from"]) for row in result.get("scale",[]) if "from" in row})
    return result
