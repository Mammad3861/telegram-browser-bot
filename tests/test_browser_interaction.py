from app.fetchers.browser_interaction import normalize_elements, option_label


def test_interaction_element_extraction_normalizes_links() -> None:
    elements = normalize_elements(
        [
            {"label": " Continue ", "kind": "button"},
            {"label": "Next", "kind": "link", "href": "/next"},
            {"label": "", "kind": "button"},
        ],
        "https://example.com/page",
        10,
    )

    assert [element.label for element in elements] == ["Continue", "Next"]
    assert elements[1].href == "https://example.com/next"


def test_interaction_max_element_limit() -> None:
    items = [
        {"label": f"Button {index}", "kind": "button"} for index in range(20)
    ]

    assert len(normalize_elements(items, "https://example.com", 10)) == 10


def test_page_option_label_includes_type_and_external_domain() -> None:
    element = normalize_elements(
        [{"label": "Continue", "kind": "link", "href": "https://other.example/next"}],
        "https://example.com",
        10,
    )[0]

    assert option_label(element, "https://example.com") == "Continue · link · other.example"
