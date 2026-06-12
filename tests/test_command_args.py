import pytest

from app.core.command_args import (
    CommandArgumentError,
    parse_single_url_arg,
    url_usage,
)


def test_accepts_one_clean_url() -> None:
    assert parse_single_url_arg("  https://example.com/path?x=1  ") == (
        "https://example.com/path?x=1"
    )


@pytest.mark.parametrize("raw_args", [None, "", "   "])
def test_rejects_empty_args(raw_args) -> None:
    with pytest.raises(CommandArgumentError):
        parse_single_url_arg(raw_args)


@pytest.mark.parametrize(
    "raw_args",
    [
        "https://example.com\nhttps://other.com",
        "https://example.com\rhidden",
        "https://example.com\tother",
    ],
)
def test_rejects_url_with_newline_or_hidden_whitespace(raw_args: str) -> None:
    with pytest.raises(CommandArgumentError):
        parse_single_url_arg(raw_args)


@pytest.mark.parametrize(
    "raw_args", ["https://example.com https://other.com", "https://example.com/path here"]
)
def test_rejects_spaces_and_multiple_args(raw_args: str) -> None:
    with pytest.raises(CommandArgumentError):
        parse_single_url_arg(raw_args)


def test_rejects_non_printable_character() -> None:
    with pytest.raises(CommandArgumentError):
        parse_single_url_arg("https://example.com/\x00hidden")


def test_command_specific_usage() -> None:
    assert url_usage("fetch") == "Usage: /fetch https://example.com"
    assert url_usage("pdf") == "Usage: /pdf https://example.com"
