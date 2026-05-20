import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

TEAL_CHART_BG = "#2A9D8F"
TEAL_DARK = "#1B4D4D"
TEAL_LIGHT = "#4ECDC4"
WHITE = "#FFFFFF"
YELLOW_ACCENT = "#FFD700"
RED_ACCENT = "#E74C3C"
BLUE_LINE = "#5DADE2"


def _formatear_moneda(valor):
    """Formatea un valor numérico a string de moneda."""
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        return str(valor)
    if abs(valor) >= 1_000_000:
        return f"${valor / 1_000_000:.2f}M"
    elif abs(valor) >= 1_000:
        return f"${valor / 1_000:.0f}k"
    else:
        return f"${valor:.0f}"


def _estilo_base_ejecutivo(ax, fig):
    """Aplica estilo base ejecutivo (fondo teal, ejes blancos, grid, etc.)."""
    fig.patch.set_facecolor(TEAL_CHART_BG)
    ax.set_facecolor(TEAL_CHART_BG)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('white')
    ax.spines['bottom'].set_color('white')
    ax.tick_params(colors='white')
    ax.grid(axis='y', color='white', alpha=0.3, linestyle='-', linewidth=0.5)


def generar_grafico_imprevistos_ejecutivo(df, periodos_col="periodo", cantidad_col="cantidad"):
    """Genera gráfico de línea ejecutivo para imprevistos con cambio de repuestos.

    Retorna io.BytesIO con PNG o None si no hay datos.
    """
    # Extraer datos de forma robusta (soporta DataFrame, dict, lista)
    periodos = None
    cantidades = None

    if df is None:
        return None

    if hasattr(df, 'empty') and df.empty:
        return None

    if hasattr(df, 'columns'):
        # pandas DataFrame
        if periodos_col not in df.columns or cantidad_col not in df.columns:
            return None
        periodos = df[periodos_col].tolist()
        cantidades = df[cantidad_col].tolist()
    elif isinstance(df, dict):
        periodos = list(df.keys())
        cantidades = list(df.values())
    elif isinstance(df, (list, tuple)):
        if len(df) == 0:
            return None
        # Asumir lista de tuplas/listas (periodo, cantidad)
        try:
            periodos = [row[0] for row in df]
            cantidades = [row[1] for row in df]
        except Exception:
            return None
    else:
        return None

    if not periodos or not cantidades or len(periodos) == 0 or len(cantidades) == 0:
        return None

    fig, ax = plt.subplots(figsize=(7, 3.5), dpi=150)
    _estilo_base_ejecutivo(ax, fig)

    x = range(len(periodos))
    ax.plot(
        x, cantidades,
        color=WHITE,
        linewidth=2.5,
        marker='o',
        markerfacecolor=WHITE,
        markeredgecolor=TEAL_DARK,
        markeredgewidth=1.2,
        markersize=7,
        zorder=3,
    )

    # Etiquetas de datos encima de cada punto
    for xi, yi in zip(x, cantidades):
        try:
            val = float(yi)
        except (TypeError, ValueError):
            val = yi
        ax.annotate(
            f"{val}",
            (xi, val),
            textcoords="offset points",
            xytext=(0, 10),
            ha='center',
            color=WHITE,
            fontweight='bold',
            fontsize=9,
            zorder=4,
        )

    ax.set_xticks(x)
    n_periodos = len(periodos)
    fontsize = 8 if n_periodos > 10 else 9
    rotation = 45 if n_periodos > 6 else 0
    ha = 'right' if rotation else 'center'
    ax.set_xticklabels(periodos, color=WHITE, fontsize=fontsize, rotation=rotation, ha=ha)
    ax.set_title("IMPREVISTOS CON CAMBIO DE REPUESTOS", color=WHITE, fontweight='bold', fontsize=12)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', facecolor=fig.get_facecolor(), edgecolor='none')
    buf.seek(0)
    plt.close(fig)
    return buf


def generar_grafico_tasa_ejecutivo(df, x_col="mes_nombre", y_col="tasa"):
    """Genera gráfico de línea ejecutivo para tasa de imprevistos mensual.

    Retorna io.BytesIO con PNG o None si no hay datos.
    """
    if df is None:
        return None

    if hasattr(df, 'empty') and df.empty:
        return None

    meses = None
    tasas = None

    if hasattr(df, 'columns'):
        if x_col not in df.columns or y_col not in df.columns:
            return None
        meses = df[x_col].tolist()
        tasas = df[y_col].tolist()
    elif isinstance(df, dict):
        meses = list(df.keys())
        tasas = list(df.values())
    elif isinstance(df, (list, tuple)):
        if len(df) == 0:
            return None
        try:
            meses = [row[0] for row in df]
            tasas = [row[1] for row in df]
        except Exception:
            return None
    else:
        return None

    if not meses or not tasas or len(meses) == 0 or len(tasas) == 0:
        return None

    fig, ax = plt.subplots(figsize=(7, 3.5), dpi=150)
    _estilo_base_ejecutivo(ax, fig)

    x = range(len(meses))
    ax.plot(
        x, tasas,
        color=YELLOW_ACCENT,
        linewidth=2.5,
        marker='o',
        markerfacecolor=YELLOW_ACCENT,
        markeredgecolor=TEAL_DARK,
        markeredgewidth=1.2,
        markersize=7,
        zorder=3,
    )

    for xi, yi in zip(x, tasas):
        try:
            val = float(yi)
        except (TypeError, ValueError):
            val = yi
        ax.annotate(
            f"{val}%",
            (xi, val),
            textcoords="offset points",
            xytext=(0, 10),
            ha='center',
            color=WHITE,
            fontweight='bold',
            fontsize=9,
            zorder=4,
        )

    ax.set_xticks(x)
    n_meses = len(meses)
    fontsize = 8 if n_meses > 10 else 9
    rotation = 45 if n_meses > 6 else 0
    ha = 'right' if rotation else 'center'
    ax.set_xticklabels(meses, color=WHITE, fontsize=fontsize, rotation=rotation, ha=ha)
    ax.set_title("TASA DE IMPREVISTOS MENSUAL", color=WHITE, fontweight='bold', fontsize=12)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', facecolor=fig.get_facecolor(), edgecolor='none')
    buf.seek(0)
    plt.close(fig)
    return buf


def generar_grafico_ahorro_comparativo_ejecutivo(df_2025, df_2026, meses_labels):
    """Genera gráfico comparativo de ahorro por mes (2025 vs 2026) con fondo teal.

    Parámetros:
        df_2025: dict o lista con valores por mes para el año anterior.
        df_2026: dict o lista con valores por mes para el año actual.
        meses_labels: lista de etiquetas de meses (e.g., ["ENE", "FEB", ...]).

    Retorna io.BytesIO con PNG o None si no hay datos.
    """
    if not meses_labels:
        return None

    def _extraer_valores(data, expected_len):
        if data is None:
            return None
        valores = None
        if hasattr(data, 'tolist'):
            valores = data.tolist()
        elif isinstance(data, dict):
            valores = list(data.values())
        elif isinstance(data, (list, tuple)):
            valores = list(data)
        if valores is None or len(valores) != expected_len:
            return None
        return valores

    n = len(meses_labels)
    valores_2025 = _extraer_valores(df_2025, n)
    valores_2026 = _extraer_valores(df_2026, n)

    if valores_2025 is None or valores_2026 is None:
        return None

    fig, ax = plt.subplots(figsize=(7, 3.5), dpi=150)
    _estilo_base_ejecutivo(ax, fig)

    x = range(n)

    # Línea 2025
    ax.plot(
        x, valores_2025,
        color=BLUE_LINE,
        linewidth=2.5,
        marker='s',
        markerfacecolor=BLUE_LINE,
        markeredgecolor=WHITE,
        markeredgewidth=1.0,
        markersize=7,
        label='2025',
        zorder=3,
    )

    # Línea 2026
    ax.plot(
        x, valores_2026,
        color=RED_ACCENT,
        linewidth=2.5,
        marker='^',
        markerfacecolor=RED_ACCENT,
        markeredgecolor=WHITE,
        markeredgewidth=1.0,
        markersize=7,
        label='2026',
        zorder=3,
    )

    # Etiquetas de datos encima de cada punto (solo valores > 0, evitar superposición)
    show_all = n <= 8
    for xi, v2025, v2026 in zip(x, valores_2025, valores_2026):
        if show_all or xi % 2 == 0:
            v2025_f = float(v2025) if v2025 is not None else 0
            v2026_f = float(v2026) if v2026 is not None else 0
            if v2025_f > 0:
                ax.annotate(
                    _formatear_moneda(v2025_f),
                    (xi, v2025_f),
                    textcoords="offset points",
                    xytext=(0, 10),
                    ha='center',
                    color=WHITE,
                    fontweight='bold',
                    fontsize=7,
                    zorder=4,
                )
            if v2026_f > 0:
                ax.annotate(
                    _formatear_moneda(v2026_f),
                    (xi, v2026_f),
                    textcoords="offset points",
                    xytext=(0, -14),
                    ha='center',
                    color=WHITE,
                    fontweight='bold',
                    fontsize=7,
                    zorder=4,
                )

    ax.set_xticks(x)
    ax.set_xticklabels(meses_labels, color=WHITE, fontsize=8, rotation=30, ha='right')
    ax.set_title("AHORRO POR MES", color=WHITE, fontweight='bold', fontsize=12)

    # Leyenda
    legend = ax.legend(
        loc='upper right',
        facecolor=TEAL_DARK,
        edgecolor=WHITE,
        framealpha=0.7,
        labelcolor=WHITE,
    )
    if legend is not None:
        for text in legend.get_texts():
            text.set_color(WHITE)
            text.set_fontweight('bold')

    # Formatear eje Y según escala de los datos
    max_value = max(max(valores_2025), max(valores_2026))
    if max_value >= 1_000_000:
        ax.yaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(lambda y, _: f"${y/1_000_000:.0f}M")
        )
    elif max_value >= 1_000:
        ax.yaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(lambda y, _: f"${y/1_000:.0f}k")
        )
    else:
        ax.yaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(lambda y, _: f"${y:.0f}")
        )
    ax.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(6))

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', facecolor=fig.get_facecolor(), edgecolor='none')
    buf.seek(0)
    plt.close(fig)
    return buf


def generar_grafico_ahorro_comparativo_historico_ejecutivo(
    df,
    año_col="AÑO",
    mes_col="MES",
    ahorro_col="DIFERENCIA",
):
    """Genera gráfico comparativo de ahorro mensual por año con eje de meses fijo."""
    if df is None or not hasattr(df, "empty") or df.empty:
        return None
    if not {año_col, mes_col, ahorro_col}.issubset(df.columns):
        return None

    df_w = df.copy()
    df_w[año_col] = pd.to_numeric(df_w[año_col], errors="coerce")
    df_w[mes_col] = pd.to_numeric(df_w[mes_col], errors="coerce")
    df_w[ahorro_col] = pd.to_numeric(df_w[ahorro_col], errors="coerce").fillna(0)
    df_w = df_w[
        df_w[año_col].notna()
        & df_w[mes_col].notna()
        & (df_w[mes_col] >= 1)
        & (df_w[mes_col] <= 12)
    ].copy()

    if df_w.empty:
        return None

    df_w[año_col] = df_w[año_col].astype(int)
    df_w[mes_col] = df_w[mes_col].astype(int)
    pivot = df_w.pivot_table(
        index=mes_col,
        columns=año_col,
        values=ahorro_col,
        aggfunc="sum",
        fill_value=0,
    ).reindex(range(1, 13), fill_value=0)

    years = sorted(pivot.columns.tolist())
    if not years:
        return None

    meses_labels = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]
    fig, ax = plt.subplots(figsize=(7, 3.5), dpi=150)
    _estilo_base_ejecutivo(ax, fig)

    palette = [BLUE_LINE, RED_ACCENT, YELLOW_ACCENT, "#22C55E", "#A78BFA", "#F97316", "#38BDF8"]
    x = list(range(12))

    for idx, year in enumerate(years):
        values = pivot[year].tolist()
        values = [float(v) if float(v) != 0 else None for v in values]
        color = palette[idx % len(palette)]
        ax.plot(
            x,
            values,
            color=color,
            linewidth=2.3,
            marker="o",
            markerfacecolor=color,
            markeredgecolor=WHITE,
            markeredgewidth=0.8,
            markersize=5,
            label=str(year),
            zorder=3,
        )
        label_offset = 10 if idx % 2 == 0 else -16
        va = "bottom" if label_offset > 0 else "top"
        for xi, value in zip(x, values):
            if value is None:
                continue
            ax.annotate(
                _formatear_moneda(value),
                (xi, value),
                textcoords="offset points",
                xytext=(0, label_offset),
                ha="center",
                va=va,
                color=WHITE,
                fontsize=6.5,
                fontweight="bold",
                bbox={
                    "boxstyle": "round,pad=0.18",
                    "facecolor": TEAL_DARK,
                    "edgecolor": color,
                    "linewidth": 0.6,
                    "alpha": 0.78,
                },
                zorder=4,
            )

    ax.set_xticks(x)
    ax.set_xticklabels(meses_labels, color=WHITE, fontsize=8, rotation=30, ha="right")
    ax.set_title("AHORRO POR MES", color=WHITE, fontweight="bold", fontsize=12)

    legend = ax.legend(
        loc="upper right",
        facecolor=TEAL_DARK,
        edgecolor=WHITE,
        framealpha=0.7,
        labelcolor=WHITE,
        fontsize=8,
    )
    if legend is not None:
        for text in legend.get_texts():
            text.set_color(WHITE)
            text.set_fontweight("bold")

    max_value = df_w[ahorro_col].max()
    if max_value >= 1_000_000:
        ax.yaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(lambda y, _: f"${y/1_000_000:.0f}M")
        )
    elif max_value >= 1_000:
        ax.yaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(lambda y, _: f"${y/1_000:.0f}k")
        )
    else:
        ax.yaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(lambda y, _: f"${y:.0f}")
        )
    ax.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(6))

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=fig.get_facecolor(), edgecolor="none")
    buf.seek(0)
    plt.close(fig)
    return buf


def generar_grafico_ahorro_mes_ejecutivo(df, periodo_col="periodo", ahorro_col="DIFERENCIA"):
    """Genera gráfico de barras ejecutivo para ahorro por período.

    Retorna io.BytesIO con PNG o None si no hay datos.
    """
    if df is None:
        return None

    if hasattr(df, 'empty') and df.empty:
        return None

    periodos = None
    ahorros = None

    if hasattr(df, 'columns'):
        if periodo_col not in df.columns or ahorro_col not in df.columns:
            return None
        periodos = df[periodo_col].tolist()
        ahorros = df[ahorro_col].tolist()
    elif isinstance(df, dict):
        periodos = list(df.keys())
        ahorros = list(df.values())
    elif isinstance(df, (list, tuple)):
        if len(df) == 0:
            return None
        try:
            periodos = [row[0] for row in df]
            ahorros = [row[1] for row in df]
        except Exception:
            return None
    else:
        return None

    if not periodos or not ahorros or len(periodos) == 0 or len(ahorros) == 0:
        return None

    fig, ax = plt.subplots(figsize=(7, 3.5), dpi=150)
    _estilo_base_ejecutivo(ax, fig)

    x = range(len(periodos))
    bars = ax.bar(
        x, ahorros,
        color=YELLOW_ACCENT,
        edgecolor=WHITE,
        linewidth=0.8,
        zorder=3,
    )

    # Etiquetas encima de barras
    for bar, val in zip(bars, ahorros):
        height = bar.get_height()
        try:
            h = float(height)
        except (TypeError, ValueError):
            h = height
        ax.annotate(
            _formatear_moneda(h),
            xy=(bar.get_x() + bar.get_width() / 2, h),
            xytext=(0, 5),
            textcoords="offset points",
            ha='center',
            color=WHITE,
            fontweight='bold',
            fontsize=9,
            zorder=4,
        )

    ax.set_xticks(x)
    n_periodos = len(periodos)
    fontsize = 8 if n_periodos > 10 else 9
    rotation = 45 if n_periodos > 6 else 0
    ha = 'right' if rotation else 'center'
    ax.set_xticklabels(periodos, color=WHITE, fontsize=fontsize, rotation=rotation, ha=ha)
    ax.set_title("AHORRO POR MES", color=WHITE, fontweight='bold', fontsize=12)

    # Formatear eje Y en millones
    ax.yaxis.set_major_formatter(
        matplotlib.ticker.FuncFormatter(lambda y, _: f"${_formatear_moneda(y).replace('$', '')}")
    )

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', facecolor=fig.get_facecolor(), edgecolor='none')
    buf.seek(0)
    plt.close(fig)
    return buf
