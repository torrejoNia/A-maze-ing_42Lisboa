from typing import TypedDict

MANDATORY_KEYS: set[str] = {
    "WIDTH",
    "HEIGHT",
    "ENTRY",
    "EXIT",
    "OUTPUT_FILE",
    "PERFECT",
}


class ConfigData(TypedDict):
    """Structured configuration returned by parse_config."""

    width: int
    height: int
    entry: tuple[int, int]
    exit_: tuple[int, int]
    output_file: str
    perfect: bool
    seed: int | None
    logo: list[str] | None
    algorithm: str


def _parse_raw(filepath: str) -> dict[str, str]:
    """Read a config file and return raw KEY→VALUE string pairs.

    Blank lines and lines starting with '#' are ignored.
    Every other line must follow the KEY=VALUE format.

    Args:
        filepath (str): Path to the configuration file.

    Returns:
        dict[str, str]: Mapping of uppercased keys to raw values.

    Raises:
        ValueError: If the file is not found or a line is malformed.
    """
    raw: dict[str, str] = {}

    try:
        f = open(filepath)
    except FileNotFoundError:
        raise ValueError(f"Config file not found: {filepath}")

    with f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()

            if not line:
                continue

            if line.startswith("#"):
                continue

            if "=" not in line:
                raise ValueError(
                    f"Line {line_number}: expected KEY=VALUE,"
                    f" got: {line}"
                )

            key, value = line.split("=", 1)
            key = key.strip().upper()
            value = value.strip()

            if not key:
                raise ValueError(
                    f"Line {line_number}: key cannot be empty"
                )

            raw[key] = value

    return raw


def _parse_coord(value: str, key: str) -> tuple[int, int]:
    """Convert a 'x,y' config string to an internal (row, col) tuple.

    The config file stores coordinates as col,row (x,y). This
    function swaps them to match the internal (row, col) convention.

    Args:
        value (str): Raw coordinate string, e.g. '0,0'.
        key (str): The config key name, used in error messages.

    Returns:
        tuple[int, int]: Coordinate as (row, col).

    Raises:
        ValueError: If the format is invalid or values are not integers.
    """
    parts: list[str] = value.split(",")

    if len(parts) != 2:
        raise ValueError(
            f"{key}: expected 'x,y', got '{value}'"
        )

    try:
        x: int = int(parts[0].strip())
        y: int = int(parts[1].strip())
    except ValueError:
        raise ValueError(
            f"{key}: coordinates must be integers, got '{value}'"
        )

    return (y, x)


def _parse_logo(filepath: str) -> list[str]:
    """Read a logo file and return its pattern rows.

    Each non-blank, non-comment line must contain only 'X' and '.'
    characters and all rows must share the same length.

    Args:
        filepath (str): Path to the logo pattern file.

    Returns:
        list[str]: Non-empty list of equal-length rows.

    Raises:
        ValueError: If the file is missing, empty, contains invalid
            characters, or has inconsistent row widths.
    """
    try:
        f = open(filepath)
    except FileNotFoundError:
        raise ValueError(f"LOGO file not found: {filepath}")

    rows: list[str] = []
    with f:
        for line in f:
            line = line.rstrip("\n")
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            invalid = set(stripped) - {"X", "."}
            if invalid:
                raise ValueError(
                    f"LOGO file '{filepath}': invalid characters"
                    f" {invalid!r} — only 'X' and '.' are allowed"
                )
            rows.append(stripped)

    if not rows:
        raise ValueError(f"LOGO file '{filepath}' contains no pattern rows")

    row_len = len(rows[0])
    for i, row in enumerate(rows[1:], start=2):
        if len(row) != row_len:
            raise ValueError(
                f"LOGO file '{filepath}': row {i} has width {len(row)},"
                f" expected {row_len}"
            )

    return rows


def _validate(raw: dict[str, str]) -> ConfigData:
    """Validate raw config strings and return a typed ConfigData.

    Checks that all mandatory keys are present, converts each value
    to its correct Python type, and enforces all spec constraints.

    Args:
        raw (dict[str, str]): Output of _parse_raw.

    Returns:
        ConfigData: Fully validated and typed configuration.

    Raises:
        ValueError: On any missing key, bad type, or failed constraint.
    """
    missing: set[str] = MANDATORY_KEYS - set(raw.keys())
    if missing:
        raise ValueError(f"Missing mandatory keys: {missing}")

    try:
        width: int = int(raw["WIDTH"])
    except ValueError:
        raise ValueError(
            f"WIDTH must be an integer, got '{raw['WIDTH']}'"
        )
    if width < 1:
        raise ValueError(f"WIDTH must be >= 1, got {width}")

    try:
        height: int = int(raw["HEIGHT"])
    except ValueError:
        raise ValueError(
            f"HEIGHT must be an integer, got '{raw['HEIGHT']}'"
        )
    if height < 1:
        raise ValueError(f"HEIGHT must be >= 1, got {height}")

    entry: tuple[int, int] = _parse_coord(raw["ENTRY"], "ENTRY")
    entry_row: int = entry[0]
    entry_col: int = entry[1]
    if not (0 <= entry_row < height and 0 <= entry_col < width):
        raise ValueError(
            f"ENTRY {entry} is outside maze bounds ({width}x{height})"
        )

    exit_: tuple[int, int] = _parse_coord(raw["EXIT"], "EXIT")
    exit_row: int = exit_[0]
    exit_col: int = exit_[1]
    if not (0 <= exit_row < height and 0 <= exit_col < width):
        raise ValueError(
            f"EXIT {exit_} is outside maze bounds ({width}x{height})"
        )

    if entry == exit_:
        raise ValueError("ENTRY and EXIT must be different cells")

    output_file: str = raw["OUTPUT_FILE"]
    if not output_file:
        raise ValueError("OUTPUT_FILE cannot be empty")

    perfect_str: str = raw["PERFECT"].capitalize()
    if perfect_str not in ("True", "False"):
        raise ValueError(
            f"PERFECT must be 'True' or 'False',"
            f" got '{raw['PERFECT']}'"
        )
    perfect: bool = perfect_str == "True"

    seed: int | None = None
    if "SEED" in raw:
        try:
            seed = int(raw["SEED"])
        except ValueError:
            raise ValueError(
                f"SEED must be an integer, got '{raw['SEED']}'"
            )

    logo: list[str] | None = None
    if "LOGO" in raw:
        logo = _parse_logo(raw["LOGO"])

    algorithm: str = raw.get("ALGORITHM", "dfs").lower()
    if algorithm not in {"dfs", "prim"}:
        raise ValueError(
            f"ALGORITHM must be 'dfs' or 'prim', got '{raw['ALGORITHM']}'"
        )

    return ConfigData(
        width=width,
        height=height,
        entry=entry,
        exit_=exit_,
        output_file=output_file,
        perfect=perfect,
        seed=seed,
        logo=logo,
        algorithm=algorithm,
    )


def parse_config(filepath: str) -> ConfigData:
    """Parse and validate a maze configuration file.

    Args:
        filepath (str): Path to the configuration file.

    Returns:
        ConfigData: Validated configuration ready for use.

    Raises:
        ValueError: On any file, syntax, or validation error.
    """
    raw: dict[str, str] = _parse_raw(filepath)
    return _validate(raw)


if __name__ == "__main__":
    cfg = parse_config('config.txt')
    print(cfg)
