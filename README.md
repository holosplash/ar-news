# ar-news

Current headlines for the Holosplash AR mug (AR_curved's `NewsTicker`). A GitHub Actions job runs
`collect.py` every 30 minutes and commits `news.json` when the headlines change. The phone reads it from
`https://raw.githubusercontent.com/holosplash/ar-news/main/news.json` (CORS `*`, 5-minute cache).

| Region | Countries (visitor IP) | Source |
|---|---|---|
| `de` | DE, AT, LI, LU | tagesschau (ARD) |
| `ch` | CH | SRF News |
| `it` | IT, SM, VA | ANSA Top News |
| `en` | everyone else | BBC News, World |

Headlines and links come from each publisher's public RSS feed and are shown with the source's name, linking to
the original article. Change sources in `REGIONS` in `collect.py`; run it locally with `python3 collect.py --print`.
Run the job now: Actions ▸ Collect headlines ▸ Run workflow.
