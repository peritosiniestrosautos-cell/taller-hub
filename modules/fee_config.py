"""
================================================================================
FEE CONFIGURATION - Taller Hub
================================================================================
Manages per-taller fee/honorarios configuration with threshold rules, 
customizable rates, and presentation mode toggle.

Each workshop can have its own:
- Threshold (umbral)
- Base percentage (below threshold)
- Premium percentage (above threshold)
"""

import streamlit as st
import json
from pathlib import Path
from typing import Dict, Optional
from .data_processor import filter_authorized_savings_records

# ============================================================================
# FEE CONFIGURATION MANAGEMENT
# ============================================================================

FEE_CONFIG_FILE = Path(__file__).parent.parent / "data" / "fee_config.json"

DEFAULT_FEE_CONFIG = {
    "global_defaults": {
        "threshold": 15000000,  # $15,000,000 threshold
        "base_percentage": 0.18,  # 18% base rate
        "premium_percentage": 0.20,  # 20% premium rate (above threshold)
    },
    "talleres": {},  # Per-taller overrides: {taller_id: {threshold, base_percentage, premium_percentage}}
    "hide_fees_presentation": False  # Toggle for presentation mode
}

SPECIAL_TALLER_DEFAULTS = {
    "renomotriz": {
        "threshold": 15000000,
        "base_percentage": 0.18,
        "premium_percentage": 0.18,
    }
}


def _normalize_taller_key(taller_id: str) -> str:
    """Normaliza identificadores/nombres de taller para reglas especiales."""
    return str(taller_id or "").strip().lower().replace(" ", "_")


def prepare_fee_calculation_df(df):
    """
    Aplica las reglas base para honorarios:
    - solo registros AUTORIZADO
    """
    df = filter_authorized_savings_records(df)
    return df


def load_fee_config():
    """Load fee configuration from JSON file"""
    if FEE_CONFIG_FILE.exists():
        try:
            with open(FEE_CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Merge with defaults to ensure all keys exist
                merged = {**DEFAULT_FEE_CONFIG, **config}
                # Ensure nested structures exist
                merged.setdefault('global_defaults', DEFAULT_FEE_CONFIG['global_defaults'])
                merged.setdefault('talleres', {})
                merged.setdefault('hide_fees_presentation', False)
                return merged
        except Exception as e:
            st.error(f"Error loading fee config: {e}")
            return DEFAULT_FEE_CONFIG.copy()
    return DEFAULT_FEE_CONFIG.copy()


def save_fee_config(config):
    """Save fee configuration to JSON file"""
    try:
        FEE_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(FEE_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Error saving fee config: {e}")
        return False


def get_taller_fee_config(taller_id: str, config=None):
    """
    Get fee configuration for a specific workshop.
    Falls back to global defaults if no per-taller config exists.
    
    Returns:
        dict: {threshold, base_percentage, premium_percentage}
    """
    if config is None:
        config = load_fee_config()
    
    # Check if workshop has specific config
    if taller_id in config.get('talleres', {}):
        return config['talleres'][taller_id]

    normalized_taller_id = _normalize_taller_key(taller_id)
    if normalized_taller_id in config.get('talleres', {}):
        return config['talleres'][normalized_taller_id]

    if normalized_taller_id in SPECIAL_TALLER_DEFAULTS:
        return SPECIAL_TALLER_DEFAULTS[normalized_taller_id]
    
    # Fall back to global defaults
    return config.get('global_defaults', DEFAULT_FEE_CONFIG['global_defaults'])


def update_taller_fee_config(taller_id: str, threshold: float, base_pct: float, premium_pct: float):
    """
    Update fee configuration for a specific workshop.
    
    Args:
        taller_id: Workshop ID
        threshold: Threshold amount
        base_pct: Base percentage (e.g., 0.18 for 18%)
        premium_pct: Premium percentage (e.g., 0.20 for 20%)
    """
    config = load_fee_config()
    
    config['talleres'][taller_id] = {
        'threshold': threshold,
        'base_percentage': base_pct,
        'premium_percentage': premium_pct
    }
    
    return save_fee_config(config)


def calculate_fee(total_savings, taller_id: str = None, config=None):
    """
    Calculate fee based on threshold rule for a specific workshop:
    - If total_savings > threshold → use premium_percentage
    - Else → use base_percentage
    
    Args:
        total_savings: Total savings amount
        taller_id: Workshop ID (uses global defaults if None)
        config: Fee configuration (loads if None)
    
    Returns:
        dict: {
            'fee_amount': calculated fee,
            'fee_percentage': percentage used,
            'should_charge': formatted fee amount,
            'rule_applied': 'premium' or 'base',
            'threshold': threshold used,
            'total_savings': input savings
        }
    """
    if config is None:
        config = load_fee_config()
    
    # Get workshop-specific config or use defaults
    if taller_id:
        fee_config = get_taller_fee_config(taller_id, config)
    else:
        fee_config = config.get('global_defaults', DEFAULT_FEE_CONFIG['global_defaults'])
    
    threshold = fee_config['threshold']
    base_rate = fee_config['base_percentage']
    premium_rate = fee_config['premium_percentage']
    
    # Apply threshold rule
    if total_savings > threshold:
        fee_percentage = premium_rate
        rule_applied = 'premium'
    else:
        fee_percentage = base_rate
        rule_applied = 'base'
    
    fee_amount = total_savings * fee_percentage
    
    return {
        'fee_amount': fee_amount,
        'fee_percentage': fee_percentage,
        'should_charge': fee_amount,
        'rule_applied': rule_applied,
        'threshold': threshold,
        'total_savings': total_savings,
        'taller_id': taller_id
    }


def calculate_fees_for_df(df, config=None):
    """
    Calculate fees for a DataFrame that may contain multiple workshops.
    Returns a DataFrame with fee calculations per workshop.
    
    Args:
        df: DataFrame with 'DIFERENCIA' and optionally 'TALLER_ORIGEN' columns
        config: Fee configuration
    
    Returns:
        dict: {
            'total': {fee_amount, fee_percentage, ...},  # Overall
            'by_taller': {taller_id: {fee_amount, fee_percentage, ...}}  # Per workshop
        }
    """
    if config is None:
        config = load_fee_config()

    df = prepare_fee_calculation_df(df)
    
    result = {
        'total': None,
        'by_taller': {}
    }
    
    if df is None or df.empty or 'DIFERENCIA' not in df.columns:
        return result
    
    # Calculate overall fee
    total_savings = df['DIFERENCIA'].sum()
    result['total'] = calculate_fee(total_savings, None, config)
    
    # Calculate per-workshop fees if applicable
    if 'TALLER_ORIGEN' in df.columns:
        talleres = df['TALLER_ORIGEN'].unique()
        for taller in talleres:
            df_taller = df[df['TALLER_ORIGEN'] == taller]
            savings = df_taller['DIFERENCIA'].sum()
            result['by_taller'][taller] = calculate_fee(savings, taller, config)
    
    return result


def calculate_fees_per_month(df, config=None):
    """
    Calculate fees on a per-month basis. Each month's recovery is evaluated
    independently against the threshold rule (not accumulated).
    
    Args:
        df: DataFrame with DIFERENCIA, AÑO, MES columns (and optionally TALLER_ORIGEN)
        config: Fee configuration
    
    Returns:
        dict: {
            'total_honorarios': float,
            'total_savings': float,
            'monthly_percentages': {period_key: fee_percentage},  # for chart use
            'by_month': [dict per month],
            'by_taller': {taller_id: {...}}  # multitaller only
        }
    """
    if config is None:
        config = load_fee_config()
    
    df = prepare_fee_calculation_df(df)
    
    result = {
        'total_honorarios': 0.0,
        'total_savings': 0.0,
        'monthly_percentages': {},
        'by_month': [],
        'by_taller': {}
    }
    
    if df is None or df.empty or 'DIFERENCIA' not in df.columns:
        return result
    
    if 'AÑO' not in df.columns or 'MES' not in df.columns:
        return result
    
    has_taller = 'TALLER_ORIGEN' in df.columns and df['TALLER_ORIGEN'].nunique() > 1
    
    if has_taller:
        for taller in df['TALLER_ORIGEN'].unique():
            df_taller = df[df['TALLER_ORIGEN'] == taller]
            taller_result = _calculate_fees_per_month_single(df_taller, taller, config)
            result['total_honorarios'] += taller_result['total_honorarios']
            result['total_savings'] += taller_result['total_savings']
            result['by_taller'][taller] = taller_result
        
        # Also populate consolidated monthly_percentages for the combined chart
        # using global threshold rule on aggregated per-month totals
        consolidated_result = _calculate_fees_per_month_single(df, None, config)
        result['monthly_percentages'] = consolidated_result['monthly_percentages']
        result['by_month'] = consolidated_result['by_month']
    else:
        taller_id = df['TALLER_ORIGEN'].iloc[0] if 'TALLER_ORIGEN' in df.columns else None
        single_result = _calculate_fees_per_month_single(df, taller_id, config)
        result['total_honorarios'] = single_result['total_honorarios']
        result['total_savings'] = single_result['total_savings']
        result['monthly_percentages'] = single_result['monthly_percentages']
        result['by_month'] = single_result['by_month']
    
    return result


def _calculate_fees_per_month_single(df, taller_id, config):
    """
    Internal: calculate per-month fees for a single workshop's DataFrame.
    """
    df_valid = df[(df['AÑO'].notna()) & (df['MES'].notna()) &
                  (df['AÑO'] > 2000) & (df['MES'] >= 1) & (df['MES'] <= 12)]
    
    result = {
        'total_honorarios': 0.0,
        'total_savings': 0.0,
        'monthly_percentages': {},
        'by_month': []
    }
    
    if df_valid.empty:
        return result
    
    monthly = df_valid.groupby(['AÑO', 'MES'])['DIFERENCIA'].sum().reset_index()
    monthly.columns = ['AÑO', 'MES', 'RECUPERACION']
    
    for _, row in monthly.iterrows():
        recovery = row['RECUPERACION']
        fee = calculate_fee(recovery, taller_id, config)
        period = f"{int(row['MES']):02d}/{int(row['AÑO'])}"
        
        result['total_savings'] += recovery
        result['total_honorarios'] += fee['fee_amount']
        result['monthly_percentages'][period] = fee['fee_percentage'] * 100
        result['by_month'].append({
            'AÑO': int(row['AÑO']),
            'MES': int(row['MES']),
            'RECUPERACION': recovery,
            'fee_percentage': fee['fee_percentage'] * 100,
            'VALOR_HONORARIOS': fee['fee_amount'],
            'rule_applied': fee['rule_applied']
        })
    
    return result


def _calculate_fees_per_month_for_taller(df, taller_id, config):
    """
    Internal: calculate per-month fees for a specific workshop.
    Returns total honorarios and per-month breakdown.
    """
    df_taller = df[df['TALLER_ORIGEN'] == taller_id]
    return _calculate_fees_per_month_single(df_taller, taller_id, config)


def format_currency(value):
    """Format value as currency string"""
    return f"${value:,.0f}"


# ============================================================================
# FEE CONFIGURATION UI
# ============================================================================

def render_taller_fee_config(taller_id: str, taller_name: str):
    """
    Render fee configuration for a specific workshop.
    Returns True if config was updated, False otherwise
    """
    config = load_fee_config()
    taller_config = get_taller_fee_config(taller_id, config)
    
    st.markdown(f"**🔧 Configuración: {taller_name}**")
    
    # Configuration form
    with st.form(f"fee_config_form_{taller_id}"):
        col1, col2 = st.columns(2)
        
        with col1:
            threshold = st.number_input(
                "💰 Umbral de Ahorro ($)",
                min_value=1000000,
                max_value=100000000,
                value=int(taller_config.get('threshold', 15000000)),
                step=500000,
                help="Si el ahorro total supera este valor, se aplica la tasa premium",
                format="%d",
                key=f"threshold_{taller_id}"
            )
            
            base_percentage = st.number_input(
                "📊 Tasa Base (%)",
                min_value=1.0,
                max_value=50.0,
                value=taller_config.get('base_percentage', 0.18) * 100,
                step=0.5,
                help="Porcentaje de honorarios cuando el ahorro está por debajo del umbral",
                key=f"base_{taller_id}"
            )
        
        with col2:
            premium_percentage = st.number_input(
                "🚀 Tasa Premium (%)",
                min_value=1.0,
                max_value=50.0,
                value=taller_config.get('premium_percentage', 0.20) * 100,
                step=0.5,
                help="Porcentaje de honorarios cuando el ahorro supera el umbral",
                key=f"premium_{taller_id}"
            )
            
            # Show if using defaults or custom
            is_custom = taller_id in config.get('talleres', {})
            st.markdown(f"""
            <div style="background: #1E293B; padding: 0.5rem; border-radius: 6px; margin-top: 1rem;">
            <p style="color: {'#00CC66' if is_custom else '#94A3B8'}; margin: 0; font-size: 0.8rem;">
            {'✅ Configuración personalizada' if is_custom else 'ℹ️ Usando valores por defecto'}
            </p>
            </div>
            """, unsafe_allow_html=True)
        
        # Preview current rule
        st.divider()
        st.markdown("**Vista previa de la regla:**")
        st.info(
            f"💡 Si ahorro > **{format_currency(threshold)}** → "
            f"Aplicar **{premium_percentage:.1f}%**\n\n"
            f"📌 Si ahorro ≤ **{format_currency(threshold)}** → "
            f"Aplicar **{base_percentage:.1f}%**"
        )
        
        # Submit/Reset buttons
        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
        
        with col_btn2:
            submitted = st.form_submit_button("💾 Guardar", use_container_width=True)
        
        with col_btn3:
            reset_button = st.form_submit_button("🔄 Resetear", use_container_width=True)
    
    if submitted:
        new_base = base_percentage / 100
        new_premium = premium_percentage / 100
        
        if update_taller_fee_config(taller_id, threshold, new_base, new_premium):
            st.success(f"✅ Configuración guardada para **{taller_name}**")
            return True
        else:
            st.error("❌ Error al guardar la configuración")
            return False
    
    if reset_button:
        # Remove workshop-specific config (revert to defaults)
        config = load_fee_config()
        if taller_id in config.get('talleres', {}):
            del config['talleres'][taller_id]
            if save_fee_config(config):
                st.info(f"🔄 Configuración de **{taller_name}** reseteada a valores por defecto")
                return True
    
    return False


def render_global_fee_defaults():
    """
    Render global default fee configuration.
    Returns True if config was updated, False otherwise
    """
    config = load_fee_config()
    defaults = config.get('global_defaults', DEFAULT_FEE_CONFIG['global_defaults'])
    
    st.markdown("**🌍 Valores por Defecto Globales**")
    st.caption("Estos valores se aplican a talleres sin configuración personalizada")
    
    with st.form("fee_config_global_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            threshold = st.number_input(
                "💰 Umbral Global ($)",
                min_value=1000000,
                max_value=100000000,
                value=int(defaults.get('threshold', 15000000)),
                step=500000,
                help="Umbral por defecto para nuevos talleres",
                format="%d",
                key="threshold_global"
            )
            
            base_percentage = st.number_input(
                "📊 Tasa Base Global (%)",
                min_value=1.0,
                max_value=50.0,
                value=defaults.get('base_percentage', 0.18) * 100,
                step=0.5,
                help="Tasa base por defecto",
                key="base_global"
            )
        
        with col2:
            premium_percentage = st.number_input(
                "🚀 Tasa Premium Global (%)",
                min_value=1.0,
                max_value=50.0,
                value=defaults.get('premium_percentage', 0.20) * 100,
                step=0.5,
                help="Tasa premium por defecto",
                key="premium_global"
            )
            
            hide_fees = st.checkbox(
                "👁️ Ocultar honorarios en modo presentación",
                value=config.get('hide_fees_presentation', False),
                help="Oculta los valores de honorarios cuando se muestra en modo presentación"
            )
        
        col_btn1, col_btn2 = st.columns([1, 1])
        
        with col_btn2:
            submitted = st.form_submit_button("💾 Guardar Globales", use_container_width=True)
    
    if submitted:
        config['global_defaults'] = {
            'threshold': threshold,
            'base_percentage': base_percentage / 100,
            'premium_percentage': premium_percentage / 100
        }
        config['hide_fees_presentation'] = hide_fees
        
        if save_fee_config(config):
            st.success("✅ Configuración global guardada")
            return True
    
    return False


def render_presentation_toggle():
    """
    Render a simple toggle for presentation mode in sidebar
    Returns True if presentation mode is active
    """
    config = load_fee_config()
    
    st.divider()
    st.markdown("**🎭 Modo Presentación**")
    
    presentation_mode = st.toggle(
        "Ocultar honorarios",
        value=config.get('hide_fees_presentation', False),
        help="Oculta los valores de honorarios para presentaciones"
    )
    
    # Update config if changed
    if presentation_mode != config.get('hide_fees_presentation', False):
        config['hide_fees_presentation'] = presentation_mode
        save_fee_config(config)
    
    return presentation_mode
