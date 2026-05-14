import pandas as pd


SOURCE_DATE_FORMATS = {
    "FECHA_INGR": "%d/%m/%Y",
    "FECHA_AUTO": "%d/%m/%Y",
}


def parse_source_date_column(series: pd.Series, column_name: str) -> pd.Series:
    """
    Parse source date columns using the known input format for each field.

    FECHA_INGR arrives as dd/mm/yyyy.
    FECHA_AUTO arrives as dd/mm/yyyy.

    Falls back to pandas inference for values that do not match the strict
    source format, preserving compatibility with already-normalized datetimes.
    """
    if series is None:
        return pd.Series(dtype="datetime64[ns]")

    if pd.api.types.is_datetime64_any_dtype(series):
        return pd.to_datetime(series, errors="coerce")

    raw = series.copy()
    cleaned = raw.astype(str).str.strip()
    cleaned = cleaned.replace({"": pd.NA, "NAN": pd.NA, "NONE": pd.NA, "NAT": pd.NA})

    date_format = SOURCE_DATE_FORMATS.get(column_name)
    if not date_format:
        return pd.to_datetime(cleaned, errors="coerce")

    parsed = pd.to_datetime(cleaned, format=date_format, errors="coerce")

    missing_mask = parsed.isna() & cleaned.notna()
    if missing_mask.any():
        fallback = pd.to_datetime(
            cleaned[missing_mask],
            errors="coerce",
            dayfirst=True,
        )
        parsed.loc[missing_mask] = fallback

    return parsed
