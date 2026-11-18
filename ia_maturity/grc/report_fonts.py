"""Embed the legacy report fonts so PDF layout never depends on host fonts."""
import base64
from functools import lru_cache
from pathlib import Path

@lru_cache(maxsize=1)
def report_font_css():
    folder=Path(__file__).parents[1]/"public"/"fonts"/"report"
    rules=[]
    for family,filename,weight in [("GRC Sans","IBMPlexSans.ttf","100 900"),("GRC Serif","SourceSerif4.ttf","200 900"),("GRC Mono","IBMPlexMono.ttf","400"),("GRC Mono","IBMPlexMono-SemiBold.ttf","600 900")]:
        encoded=base64.b64encode((folder/filename).read_bytes()).decode("ascii")
        rules.append("@font-face{font-family:'%s';font-style:normal;font-weight:%s;src:url(data:font/ttf;base64,%s) format('truetype')}"%(family,weight,encoded))
    return "\n".join(rules)
