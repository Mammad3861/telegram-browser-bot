# Web Search

Search is an alpha feature intended for lightweight discovery, not guaranteed search availability.

## Current Provider

The default configuration is:

```env
SEARCH_PROVIDER=duckduckgo_html
```

The provider requests DuckDuckGo's public HTML result page and converts safe results into Telegram cards. Provider markup, availability, rate limits, regional networking, or upstream blocking can cause failures.

When search is unavailable, users can still send a direct URL to open the normal action card.

## Safety And Limitations

- The project does not scrape Google directly.
- It does not bypass CAPTCHAs, rate limits, or anti-bot systems.
- Result URLs are validated with the existing URL/SSRF checks before storage and again before opening a URL card.
- Localhost, private-network, unsupported-scheme, and otherwise unsafe results are discarded.
- Search sessions are owner-bound, expire, and persist locally across restarts.
- Set `SEARCH_PROVIDER=disabled` to disable provider-backed search.

## Future Provider Options

Potential provider integrations include:

- Brave Search API
- SearxNG
- Google Custom Search API
- SerpAPI

These are roadmap options only and are not implemented in this release.
