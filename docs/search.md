# Web Search

Search is a provider-based alpha feature intended for lightweight discovery. Select one provider with `SEARCH_PROVIDER`:

- `disabled`
- `duckduckgo_html`
- `brave_api`
- `searxng`

Provider failures are returned as safe user-facing messages. Users can always send a direct URL when search is unavailable.

## DuckDuckGo HTML

This is the default and requires no API credentials:

```env
SEARCH_PROVIDER=duckduckgo_html
```

It parses DuckDuckGo's public HTML results. It remains an alpha integration because upstream markup, rate limits, availability, and regional networking can change.

## Brave Search API

Create a Brave Search API subscription and configure:

```env
SEARCH_PROVIDER=brave_api
BRAVE_SEARCH_API_KEY=your_api_key
```

The provider uses Brave's web search API, respects the configured timeout/result limit, and never logs the API key. A missing key produces a safe configuration message rather than crashing the bot.

## SearxNG

Point the bot at a trusted SearxNG instance with JSON output enabled:

```env
SEARCH_PROVIDER=searxng
SEARXNG_BASE_URL=https://search.example.com
```

The bot queries the instance's `/search` endpoint with `format=json`. Public instances can be unreliable or rate-limited; a controlled self-hosted instance is preferable. A missing or invalid base URL fails safely.

## Disabled Search

```env
SEARCH_PROVIDER=disabled
```

`/search` responds with a friendly disabled message while direct URL cards and all other bot features continue to work.

## Result Cards

Cards show the active provider name and note when fewer safe results are available than requested. Search result URLs are validated before storage and again before opening a URL card.

## Safety And Limitations

- The project does not scrape Google directly.
- It does not bypass CAPTCHAs, rate limits, or anti-bot systems.
- Localhost, private-network, unsupported-scheme, and otherwise unsafe result URLs are discarded.
- Search queries are not written to application logs.
- API keys are not included in logs or user-facing errors.
- Search sessions are owner-bound, expire, and persist locally across restarts.
- Search result URLs are also checked against the administrator's content policy before storage and before opening a URL card.
- Blocked keywords reject a query before provider access. Allowed keywords permit the query, while each result URL still receives normal URL/domain checks.
- Category-classified results are filtered only when that category is blocked. Adult, gambling, crypto, and media are administrator-configurable.
- Built-in category lists are small classification seeds, not a claim of complete content detection.

General controls:

```env
SEARCH_RESULTS_LIMIT=5
SEARCH_TIMEOUT_SECONDS=15
SEARCH_QUERY_MAX_LENGTH=200
SEARCH_SESSION_TTL_MINUTES=30
```
