class CommandArgumentError(ValueError):
    pass


def parse_single_url_arg(raw_args: str | None) -> str:
    if raw_args is None:
        raise CommandArgumentError("A URL is required")
    value = raw_args.strip()
    if not value or any(
        character.isspace() or not character.isprintable() for character in value
    ):
        raise CommandArgumentError("A single URL is required")
    return value


def url_usage(command: str) -> str:
    return f"Usage: /{command} https://example.com"
