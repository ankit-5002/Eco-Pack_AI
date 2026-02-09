from flask import Flask, request, jsonify, render_template, send_file
import pandas as pd
import joblib
import numpy as np
import os
import io
import json
import datetime
import logging
# import psycopg2
# from psycopg2.extras import RealDictCursor
import threading
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Optional: try import reportlab for PDF export support
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as rcanvas
    from reportlab.lib.utils import ImageReader
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

# Optional: try import matplotlib for server-side chart rendering
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.style.use('default')
    plt.rcParams['figure.facecolor'] = 'white'
    plt.rcParams['axes.facecolor'] = 'white'
    plt.rcParams['axes.edgecolor'] = 'black'
    plt.rcParams['text.color'] = 'black'
    plt.rcParams['axes.labelcolor'] = 'black'
    plt.rcParams['xtick.color'] = 'black'
    plt.rcParams['ytick.color'] = 'black'
    MATPLOTLIB_AVAILABLE = True
except Exception:
    MATPLOTLIB_AVAILABLE = False
    plt = None

# Optional: try import PIL for image processing
try:
    from PIL import Image
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

app = Flask(__name__)

# ==========================================
# 1. CONFIGURATION
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, 'models')
# DATABASE_URL = os.getenv('DATABASE_URL')
PORT = int(os.getenv('PORT', 8080))
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

# ==========================================
# 2. LAZY LOADING FOR MODELS (Memory Optimization)
# ==========================================
# Models are loaded on-demand instead of at startup to reduce memory footprint
_model_cost = None
_model_co2 = None
_le_mat = None
_le_cat = None

def get_model_cost():
    global _model_cost
    if _model_cost is None:
        _model_cost = joblib.load(os.path.join(MODEL_DIR, 'model_cost.pkl'))
    return _model_cost

def get_model_co2():
    global _model_co2
    if _model_co2 is None:
        _model_co2 = joblib.load(os.path.join(MODEL_DIR, 'model_co2.pkl'))
    return _model_co2

def get_le_mat():
    global _le_mat
    if _le_mat is None:
        _le_mat = joblib.load(os.path.join(MODEL_DIR, 'le_material.pkl'))
    return _le_mat

def get_le_cat():
    global _le_cat
    if _le_cat is None:
        _le_cat = joblib.load(os.path.join(MODEL_DIR, 'le_category.pkl'))
    return _le_cat

# ==========================================
# 3. DATABASE CONNECTION
# ==========================================
# Cache materials in memory to avoid repeated DB/CSV reads
# Cache materials in memory to avoid repeated DB/CSV reads
_materials_cache = None
_materials_lock = threading.Lock()

# def get_db_connection():
#     """Get PostgreSQL database connection with timeout"""
#     if DATABASE_URL:
#         # Set a short connection timeout (e.g. 2 seconds) to fail fast if DB is unreachable
#         return psycopg2.connect(DATABASE_URL, connect_timeout=2)
#     else:
#         # Fallback to CSV if no database configured (for local development)
#         return None

def get_materials():
    """Get materials from database or CSV fallback, using cache with thread safety"""
    global _materials_cache
    
    # Return cached data if available (double-checked locking pattern)
    if _materials_cache is not None:
        return _materials_cache

    with _materials_lock:
        # Check again inside lock
        if _materials_cache is not None:
            return _materials_cache

        try:
            # DIRECT CSV USAGE as requested
            # conn = get_db_connection()
            # if conn:
            #     query = """
            #     SELECT 
            #         "Material_Type",
            #         "Cost_per_unit",
            #         "CO2_Emission_Score",
            #         "Biodegradability_Score",
            #         "Recyclability_Percent",
            #         "Tensile_Strength_MPa",
            #         "Weight_Capacity_kg",
            #         "Suitability_Tags"
            #     FROM materials
            #     """
            #     materials_df = pd.read_sql_query(query, conn)
            #     conn.close()
            #     
            #     # Convert numeric columns to proper types
            #     numeric_columns = [
            #         'Cost_per_unit', 'CO2_Emission_Score', 'Biodegradability_Score',
            #         'Recyclability_Percent', 'Tensile_Strength_MPa', 'Weight_Capacity_kg'
            #     ]
            #     for col in numeric_columns:
            #         materials_df[col] = pd.to_numeric(materials_df[col], errors='coerce')
            #     
            #     # Update cache
            #     _materials_cache = materials_df
            #     return materials_df
            # else:
            #     # Fallback to CSV
            #     _materials_cache = pd.read_csv(os.path.join(BASE_DIR, 'materials13.csv'))
            #     return _materials_cache
            
            # Load directly from CSV
            _materials_cache = pd.read_csv(os.path.join(BASE_DIR, 'materials13.csv'))
            return _materials_cache

        except Exception as e:
            logging.error(f"Error loading data: {e}. Falling back to CSV.")
            # Fallback to CSV on error
            _materials_cache = pd.read_csv(os.path.join(BASE_DIR, 'materials13.csv'))
            return _materials_cache

def calculate_surface_area(l, w, h):
    return 2 * (l*w + l*h + w*h)

# ==========================================
# 2. TRADITIONAL BASELINES (Static Industry Data)
# ==========================================
TRADITIONAL_BASELINES = {
    "Food & Beverages": {"Material": "Plastic Film (LDPE)", "cost_sq": 0.015, "co2_sq": 0.009},
    "Electronics": {"Material": "Styrofoam (EPS)", "cost_sq": 0.022, "co2_sq": 0.015},
    "Industrial Goods": {"Material": "Heavy Virgin Plastic", "cost_sq": 0.030, "co2_sq": 0.019},
    "Home & Living": {"Material": "Virgin Cardboard", "cost_sq": 0.013, "co2_sq": 0.007},
    "Apparel & Fashion": {"Material": "Plastic Poly-mailer", "cost_sq": 0.010, "co2_sq": 0.007},
    "Cosmetics & Beauty": {"Material": "Acrylic/Plastic", "cost_sq": 0.025, "co2_sq": 0.012},
    "Pharmaceuticals": {"Material": "Virgin Glass/Plastic", "cost_sq": 0.035, "co2_sq": 0.015},
    "Toys": {"Material": "Plastic Blister Pack", "cost_sq": 0.018, "co2_sq": 0.010},
    "E-commerce & Logistics Goods": {"Material": "Double-wall Cardboard", "cost_sq": 0.015, "co2_sq": 0.008},
    "Agriculture & Raw Materials": {"Material": "Woven Polypropylene", "cost_sq": 0.020, "co2_sq": 0.014},
    "Automotive parts & Accessories": {"Material": "Heavy-duty Corrugated", "cost_sq": 0.028, "co2_sq": 0.016},
    "Personal Care": {"Material": "Plastic Squeeze Bottle", "cost_sq": 0.016, "co2_sq": 0.009},
    "General": {"Material": "Standard Mixed Plastic", "cost_sq": 0.018, "co2_sq": 0.011}
}

# ==========================================
# 4. HEALTH CHECK ENDPOINT (for Cloud Run)
# ==========================================
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Cloud Run"""
    return jsonify({"status": "healthy", "environment": ENVIRONMENT}), 200

# ==========================================
# 5. API ENDPOINT FOR RECOMMENDATIONS
# ==========================================
@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()
        category = data.get('category', 'General')
        l = float(data.get('length'))
        w = float(data.get('width'))
        h = float(data.get('height'))
        weight = float(data.get('weight'))
        
        # Get models (lazy loaded)
        model_cost = get_model_cost()
        model_co2 = get_model_co2()
        le_mat = get_le_mat()
        le_cat = get_le_cat()
        
        # Get materials from database
        materials = get_materials()
        
        sa = calculate_surface_area(l, w, h)
        base = TRADITIONAL_BASELINES.get(category, TRADITIONAL_BASELINES['General'])
        trad_cost = sa * base['cost_sq']
        trad_co2 = sa * base['co2_sq']

        results = []
        unique_mats = materials.drop_duplicates(subset=['Material_Type'])
        
        primary_results = []
        fallback_results = []
        
        for _, m in unique_mats.iterrows():
            # Check mandatory constraints first
            if m['Weight_Capacity_kg'] < weight: continue

            # --- DEBUG LOGGING & DATA CORRECTION ---
            tensile = float(m['Tensile_Strength_MPa'])
            
            # Correction for Pascals vs MPa (if > 1000, assume Pa and convert)
            if tensile > 1000:
                logging.warning(f"Material {m['Material_Type']} has huge tensile strength ({tensile}). converting Pa -> MPa")
                tensile = tensile / 1000000.0

            # AI Inference
            m_enc = le_mat.transform([m['Material_Type']])[0]
            # Handle unknown category safely
            safe_cat = category if category in le_cat.classes_ else "General"
            c_enc = le_cat.transform([safe_cat])[0]
            
            features = ['length', 'width', 'height', 'weight', 'category_enc', 'material_type_enc', 'tensile_strength']
            pred_df = pd.DataFrame([[l, w, h, weight, c_enc, m_enc, tensile]], columns=features)
            
            est_cost = model_cost.predict(pred_df)[0]
            est_co2 = model_co2.predict(pred_df)[0]

            # Log prediction for debugging
            if est_co2 < 0:
                logging.error(f"NEGATIVE CO2 DETECTED: {est_co2} | Material: {m['Material_Type']} | Tensile: {tensile}")

            # Calculate differences
            cost_diff = trad_cost - est_cost  # Positive = savings, Negative = increase
            co2_diff = trad_co2 - est_co2     # Positive = reduction, Negative = increase
            
            # Calculate percentages
            cost_pct = (abs(cost_diff) / trad_cost * 100) if trad_cost > 0 else 0
            co2_pct = (abs(co2_diff) / trad_co2 * 100) if trad_co2 > 0 else 0

            # Sustainability Scoring (only reward actual CO2 reduction)
            co2_score = co2_pct if co2_diff > 0 else 0
            score = (m['Biodegradability_Score'] * 0.5) + (co2_score * 0.5)

            result_item = {
                'material': m['Material_Type'],
                'cost': round(float(est_cost), 2),
                'cost_impact': f"{'Save' if cost_diff > 0 else 'Add'} Rs.{abs(cost_diff):.2f}",
                'co2': round(float(est_co2), 4),
                'co2_impact': f"🌱 {co2_pct:.1f}% {'Cleaner' if co2_diff > 0 else 'Higher'}",
                'co2_saved_kg': round(float(abs(co2_diff)), 4),
                'cost_savings': round(float(abs(cost_diff)), 2),
                'cost_savings_direction': 'reduced' if cost_diff > 0 else 'increased',
                'cost_savings_percent': round(float(cost_pct), 1),
                'co2_savings': round(float(abs(co2_diff)), 4),
                'co2_savings_direction': 'reduced' if co2_diff > 0 else 'increased',
                'co2_savings_percent': round(float(co2_pct), 1),
                'traditional_material': base['Material'],
                'traditional_cost': round(float(trad_cost), 2),
                'traditional_co2': round(float(trad_co2), 4),
                'score': round(float(score), 4),
                'biodegradability_score': round(float(m['Biodegradability_Score']), 1),
                'recyclability_percent': round(float(m['Recyclability_Percent']), 1),
                'tensile_strength_mpa': round(float(m['Tensile_Strength_MPa']), 1),
                'weight_capacity_kg': round(float(m['Weight_Capacity_kg']), 1),
                'suitability_tags': m['Suitability_Tags']
            }

            # Check if primary match (category tag match)
            tags = m['Suitability_Tags'].lower()
            if category.lower() in tags or "general" in tags:
                primary_results.append(result_item)
            else:
                fallback_results.append(result_item)

        # Sort results by score
        primary_results = sorted(primary_results, key=lambda x: x['score'], reverse=True)
        fallback_results = sorted(fallback_results, key=lambda x: x['score'], reverse=True)

        # Prioritize primary results, fill with fallback if needed to reach 3
        recommendations = primary_results[:3]
        if len(recommendations) < 3:
            needed = 3 - len(recommendations)
            recommendations.extend(fallback_results[:needed])

        return jsonify({"recommendations": recommendations, "baseline_used": base['Material']})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ==========================================
# 6. BI DASHBOARD DATA ENDPOINTS
# ==========================================
@app.route('/api/dashboard-stats', methods=['GET'])
def get_dashboard_stats():
    materials = get_materials()
    return jsonify({
        'total_materials': int(len(materials)),
        'eco_friendly_count': int(len(materials[materials['Biodegradability_Score'] > 80])),
        'avg_co2': round(float(materials['CO2_Emission_Score'].mean()), 2),
        'avg_cost': round(float(materials['Cost_per_unit'].mean()), 2),
        'avg_biodegradability': round(float(materials['Biodegradability_Score'].mean()), 2),
        'avg_recyclability': round(float(materials['Recyclability_Percent'].mean()), 2)
    })


# ============================================================================
# Helper: plotting + image helpers for PDF export (defensive)
# ============================================================================

def _fig_to_png_bytes(fig):
    """Convert matplotlib figure to PNG bytes and ensure light background."""
    buf = io.BytesIO()
    try:
        fig.savefig(buf, format='png', bbox_inches='tight', facecolor='white', edgecolor='none')
        buf.seek(0)
        png_bytes = buf.getvalue()

        if PIL_AVAILABLE:
            try:
                img = Image.open(io.BytesIO(png_bytes)).convert('RGBA')
                # sample corners to decide if background is dark
                w, h = img.size
                corners = [img.getpixel((5,5)), img.getpixel((w-5,5)), img.getpixel((5,h-5)), img.getpixel((w-5,h-5))]
                avg_brightness = sum([sum(c[:3])/3 for c in corners]) / 4
                if avg_brightness < 128:
                    # invert colors preserving alpha
                    r,g,b,a = img.split()
                    inv = Image.merge('RGBA', (Image.eval(r, lambda x: 255-x), Image.eval(g, lambda x: 255-x), Image.eval(b, lambda x: 255-x), a))
                    out = io.BytesIO()
                    inv.save(out, format='PNG')
                    out.seek(0)
                    return out.getvalue()
            except Exception:
                logging.exception('Image post-processing failed; using original PNG')
        return png_bytes
    finally:
        try:
            plt.close(fig)
        except Exception:
            pass


def generate_co2_chart_png(comp_data):
    if not MATPLOTLIB_AVAILABLE:
        raise RuntimeError('Matplotlib not available')
    plt.style.use('default')
    labels = [str(d.get('material') or d.get('Material_Type')) for d in comp_data]
    values = [float(d.get('co2', d.get('CO2_Emission_Score', 0))) for d in comp_data]
    fig, ax = plt.subplots(figsize=(12,6), facecolor='white')
    ax.set_facecolor('white')
    ax.bar(labels, values, color='#4FD1C5')
    ax.set_title('CO2 Emissions (lower is better)', color='#000000', fontweight='bold', fontsize=14)
    ax.set_ylabel('CO2', color='#000000', fontsize=11)
    ax.tick_params(axis='x', labelrotation=45, labelcolor='#000000', labelsize=10)
    ax.tick_params(axis='y', labelcolor='#000000', labelsize=10)
    # Improve label visibility
    for label in ax.get_xticklabels():
        label.set_ha('right')
    ax.spines['bottom'].set_color('#000000')
    ax.spines['left'].set_color('#000000')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.subplots_adjust(bottom=0.25)
    fig.tight_layout(pad=2.0)
    return _fig_to_png_bytes(fig)


def generate_cost_chart_png(comp_data):
    if not MATPLOTLIB_AVAILABLE:
        raise RuntimeError('Matplotlib not available')
    plt.style.use('default')
    labels = [str(d.get('material') or d.get('Material_Type')) for d in comp_data]
    # Use actual cost values, not normalized
    values = [float(d.get('cost', d.get('Cost_per_unit', 0))) for d in comp_data]
    fig, ax = plt.subplots(figsize=(12,6), facecolor='white')
    ax.set_facecolor('white')
    ax.plot(labels, values, marker='o', color='#1A365D', linewidth=2, markersize=6)
    ax.set_title('Cost per Unit (Rs)', color='#000000', fontweight='bold', fontsize=14)
    ax.set_ylabel('Cost (Rs)', color='#000000', fontsize=11)
    ax.tick_params(axis='x', labelrotation=45, labelcolor='#000000', labelsize=10)
    ax.tick_params(axis='y', labelcolor='#000000', labelsize=10)
    # Improve label visibility
    for label in ax.get_xticklabels():
        label.set_ha('right')
    ax.spines['bottom'].set_color('#000000')
    ax.spines['left'].set_color('#000000')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(True, alpha=0.3, color='#cccccc')
    plt.subplots_adjust(bottom=0.25)
    fig.tight_layout(pad=2.0)
    return _fig_to_png_bytes(fig)


def generate_bio_chart_png(comp_data):
    if not MATPLOTLIB_AVAILABLE:
        raise RuntimeError('Matplotlib not available')
    plt.style.use('default')
    labels = [str(d.get('material') or d.get('Material_Type')) for d in comp_data]
    values = [float(d.get('biodegradability', d.get('Biodegradability_Score', 0))) for d in comp_data]
    fig, ax = plt.subplots(figsize=(10,6), facecolor='white')
    ax.set_facecolor('white')
    ax.bar(labels, values, color='#2ecc71')
    ax.set_title('Biodegradability (%)', color='#000000', fontweight='bold', fontsize=14)
    ax.set_ylabel('%', color='#000000', fontsize=11)
    ax.tick_params(axis='x', labelrotation=45, labelcolor='#000000', labelsize=10)
    ax.tick_params(axis='y', labelcolor='#000000', labelsize=10)
    # Improve label visibility
    for label in ax.get_xticklabels():
        label.set_ha('right')
    ax.spines['bottom'].set_color('#000000')
    ax.spines['left'].set_color('#000000')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.subplots_adjust(bottom=0.25)
    fig.tight_layout(pad=2.0)
    return _fig_to_png_bytes(fig)


def generate_recycle_chart_png(comp_data):
    if not MATPLOTLIB_AVAILABLE:
        raise RuntimeError('Matplotlib not available')
    plt.style.use('default')
    labels = [str(d.get('material') or d.get('Material_Type')) for d in comp_data]
    values = [float(d.get('recyclability', d.get('Recyclability_Percent', 0))) for d in comp_data]
    fig, ax = plt.subplots(figsize=(8,8), facecolor='white')
    ax.set_facecolor('white')
    wedges, texts, autotexts = ax.pie(values[:8], labels=labels[:8], autopct='%1.1f%%', colors=plt.cm.Blues(np.linspace(0.4,1,len(labels[:8]))), textprops={'fontsize': 10})
    for text in texts:
        text.set_color('#000000')
        text.set_fontweight('bold')
        text.set_fontsize(10)
    for autotext in autotexts:
        autotext.set_color('#ffffff')
        autotext.set_fontweight('bold')
        autotext.set_fontsize(10)
    ax.set_title('Top Recyclability', color='#000000', fontweight='bold', fontsize=14)
    fig.tight_layout(pad=2.0)
    return _fig_to_png_bytes(fig)


def generate_whatif_chart_png(whatif):
    if not MATPLOTLIB_AVAILABLE:
        raise RuntimeError('Matplotlib not available')
    plt.style.use('default')
    if isinstance(whatif, dict) and 'labels' in whatif:
        labels = whatif.get('labels')
        costs = whatif.get('cost', [])
        co2s = whatif.get('co2', [])
    else:
        labels = [str(x.get('material')) for x in whatif]
        costs = [float(x.get('cost')) for x in whatif]
        co2s = [float(x.get('co2')) for x in whatif]

    fig, ax = plt.subplots(figsize=(12,6), facecolor='white')
    ax.set_facecolor('white')
    x = np.arange(len(labels))
    width = 0.4
    ax.bar(x - width/2, costs, width=width, label='Cost (Rs)', color='#1A365D')
    ax.bar(x + width/2, co2s, width=width, label='CO2 (kg)', color='#4FD1C5')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha='right', color='#000000', fontsize=10)
    ax.tick_params(axis='y', labelcolor='#000000', labelsize=10)
    ax.spines['bottom'].set_color('#000000')
    ax.spines['left'].set_color('#000000')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    legend = ax.legend(fontsize=10)
    for text in legend.get_texts():
        text.set_color('#000000')
    ax.set_title('What-If: Cost vs CO2', color='#000000', fontweight='bold', fontsize=14)
    plt.subplots_adjust(bottom=0.25)
    fig.tight_layout(pad=2.0)
    return _fig_to_png_bytes(fig)

@app.route('/api/material-comparison', methods=['GET'])
def get_material_comparison():
    # Return material metrics and normalized scores for charts
    materials = get_materials()
    co2_vals = materials['CO2_Emission_Score'].astype(float)
    cost_vals = materials['Cost_per_unit'].astype(float)
    co2_min, co2_max = co2_vals.min(), co2_vals.max()
    cost_min, cost_max = cost_vals.min(), cost_vals.max()

    result = []
    for _, row in materials.iterrows():
        co2 = float(row['CO2_Emission_Score'])
        cost = float(row['Cost_per_unit'])
        # Lower is better for cost & CO2 -> normalize to efficiency (1 = best)
        co2_norm = 1.0 - ((co2 - co2_min) / (co2_max - co2_min)) if co2_max > co2_min else 1.0
        cost_norm = 1.0 - ((cost - cost_min) / (cost_max - cost_min)) if cost_max > cost_min else 1.0

        result.append({
            'material': row['Material_Type'],
            'co2': round(co2, 2),
            'cost': round(cost, 2),
            'biodegradability': round(float(row['Biodegradability_Score']), 1),
            'recyclability': round(float(row['Recyclability_Percent']), 1),
            'strength': round(float(row['Tensile_Strength_MPa']), 1),
            'co2_normalized': round(co2_norm, 3),
            'cost_normalized': round(cost_norm, 3)
        })
    return jsonify(result)


@app.route('/api/sustainability-metrics', methods=['GET'])
def get_sustainability_metrics():
    try:
        materials = get_materials()
        # Support a limit query parameter so the UI can expand lists (default 4)
        try:
            limit = int(request.args.get('limit', 4))
        except Exception:
            limit = 4
        limit = max(1, min(limit, 50))  # clamp between 1 and 50

        lowest_co2 = materials.nsmallest(limit, 'CO2_Emission_Score')[['Material_Type','CO2_Emission_Score']].to_dict(orient='records')
        highest_bio = materials.nlargest(limit,'Biodegradability_Score')[['Material_Type','Biodegradability_Score']].to_dict(orient='records')
        highest_recycle = materials.nlargest(limit,'Recyclability_Percent')[['Material_Type','Recyclability_Percent']].to_dict(orient='records')
        eco_candidates = materials[materials['Biodegradability_Score'] >= 80].sort_values('Cost_per_unit')[['Material_Type','Cost_per_unit','Biodegradability_Score']].to_dict(orient='records')

        return jsonify({
            'requested_limit': limit,
            'lowest_co2_materials': lowest_co2,
            'highest_biodegradability': highest_bio,
            'highest_recyclability': highest_recycle,
            'cost_effective_eco': eco_candidates[:limit]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/eco-impact', methods=['GET'])
def get_eco_impact():
    try:
        materials = get_materials()
        total = len(materials)
        eco_materials = int(len(materials[materials['Biodegradability_Score'] >= 80]))
        percent = round(eco_materials / total * 100, 1) if total>0 else 0
        max_co2 = materials['CO2_Emission_Score'].max()
        co2_reduction_potential = (materials['CO2_Emission_Score'].apply(lambda x: float(max_co2) - float(x))).sum()
        avg_reduction = round(co2_reduction_potential / total, 2) if total>0 else 0

        return jsonify({
            'eco_materials_available': eco_materials,
            'percentage_eco_in_catalog': percent,
            'total_co2_reduction_potential': round(float(co2_reduction_potential),2),
            'avg_co2_reduction_per_material': round(float(avg_reduction),2)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/material-suitability', methods=['GET'])
def get_material_suitability():
    try:
        materials = get_materials()
        rows = []
        for _, row in materials.iterrows():
            tags_raw = str(row.get('Suitability_Tags', ''))
            tags = [t.strip() for t in tags_raw.split(',') if t.strip()]
            for t in tags:
                rows.append({
                    'category': t,
                    'material': row['Material_Type'],
                    'cost': float(row['Cost_per_unit']),
                    'biodegradability': float(row['Biodegradability_Score'])
                })
        if not rows:
            return jsonify([])

        df = pd.DataFrame(rows)
        grouped = df.groupby('category').agg(
            material_count=('material', 'count'),
            avg_cost=('cost','mean'),
            avg_biodegradability=('biodegradability','mean')
        ).reset_index()

        result = []
        for _, r in grouped.iterrows():
            result.append({
                'category': r['category'],
                'material_count': int(r['material_count']),
                'avg_cost': round(float(r['avg_cost']),2),
                'avg_biodegradability': round(float(r['avg_biodegradability']),1)
            })

        result = sorted(result, key=lambda x: x['material_count'], reverse=True)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error':str(e)}),500

@app.route('/api/material-details/<material_name>', methods=['GET'])
def get_material_details(material_name):
    """Get comprehensive details for a specific material"""
    try:
        materials = get_materials()
        material = materials[materials['Material_Type'] == material_name]
        
        if material.empty:
            return jsonify({'error': 'Material not found'}), 404
        
        material_data = material.iloc[0]
        
        return jsonify({
            'material': material_data['Material_Type'],
            'cost_per_unit': round(float(material_data['Cost_per_unit']), 2),
            'co2_emission_score': round(float(material_data['CO2_Emission_Score']), 4),
            'biodegradability_score': round(float(material_data['Biodegradability_Score']), 1),
            'recyclability_percent': round(float(material_data['Recyclability_Percent']), 1),
            'tensile_strength_mpa': round(float(material_data['Tensile_Strength_MPa']), 1),
            'weight_capacity_kg': round(float(material_data['Weight_Capacity_kg']), 1),
            'suitability_tags': material_data['Suitability_Tags']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==========================================
# 4.5 PDF EXPORT ENDPOINT
# ==========================================
@app.route('/export/pdf', methods=['POST'])
def export_pdf():
    """Generate a PDF report for current dashboard data. Accepts multipart/form-data with 'data' JSON field and returns application/pdf."""
    try:
        if not REPORTLAB_AVAILABLE:
            return jsonify({'error':'Server is missing PDF generation library (reportlab). Please `pip install reportlab` to enable export.'}), 400

        materials = get_materials()
        payload = None
        if request.form.get('data'):
            try:
                payload = json.loads(request.form.get('data'))
            except Exception:
                payload = None

        # Gather stats fallback
        stats = payload.get('stats') if payload and isinstance(payload.get('stats'), dict) else {
            'total_materials': int(len(materials)),
            'eco_friendly_count': int(len(materials[materials['Biodegradability_Score'] > 80])),
            'avg_co2': round(float(materials['CO2_Emission_Score'].mean()), 2),
            'avg_cost': round(float(materials['Cost_per_unit'].mean()), 2),
            'avg_biodegradability': round(float(materials['Biodegradability_Score'].mean()), 2),
            'avg_recyclability': round(float(materials['Recyclability_Percent'].mean()), 2)
        }

        limit = int(request.form.get('limit', 10))
        limit = max(1, min(limit, 50))
        lowest_co2 = materials.nsmallest(limit, 'CO2_Emission_Score')[['Material_Type','CO2_Emission_Score']].to_dict(orient='records')
        highest_bio = materials.nlargest(limit, 'Biodegradability_Score')[['Material_Type','Biodegradability_Score']].to_dict(orient='records')

        # Always use server-side chart generation for PDF to ensure light theme
        images = {}
        try:
            comp_data = payload.get('comp') if payload and isinstance(payload.get('comp'), list) else []
            if comp_data and MATPLOTLIB_AVAILABLE:
                images['co2Chart'] = generate_co2_chart_png(comp_data)
                images['costChart'] = generate_cost_chart_png(comp_data)
                images['bioChart'] = generate_bio_chart_png(comp_data)
                images['recycleChart'] = generate_recycle_chart_png(comp_data)
            whatif = payload.get('whatif') if payload else None
            if whatif and MATPLOTLIB_AVAILABLE:
                images['whatIfChart'] = generate_whatif_chart_png(whatif)
        except Exception:
            logging.exception('Server-side chart rendering failed')

        # Begin PDF generation
        buffer = io.BytesIO()
        c = rcanvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        margin = 40
        y = height - margin

        # Set PDF metadata
        c.setTitle('EcoPackAI Dashboard Report')
        c.setAuthor('EcoPackAI')
        c.setSubject('Sustainability Intelligence Dashboard Report')

        # Helper function to draw section header
        def draw_section_header(canvas, y_pos, title):
            canvas.setFont('Helvetica-Bold', 14)
            canvas.drawString(margin, y_pos, title)
            y_pos -= 8
            canvas.setStrokeColorRGB(0.3, 0.3, 0.3)
            canvas.setLineWidth(1)
            canvas.line(margin, y_pos, width - margin, y_pos)
            return y_pos - 16

        # Title
        c.setFont('Helvetica-Bold', 18)
        c.drawString(margin, y, 'EcoPackAI — Dashboard Report')
        c.setFont('Helvetica', 10)
        y -= 20
        c.drawString(margin, y, f'Generated: {datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC')
        y -= 30

        # Key Metrics Section
        y = draw_section_header(c, y, 'Key Metrics')
        c.setFont('Helvetica', 11)
        metrics_data = [
            ('Total Materials', stats.get('total_materials', 'N/A')),
            ('Eco-Friendly Materials', stats.get('eco_friendly_count', 'N/A')),
            ('Average CO2 Score', stats.get('avg_co2', 'N/A')),
            ('Average Cost (Rs)', stats.get('avg_cost', 'N/A')),
            ('Average Biodegradability (%)', stats.get('avg_biodegradability', 'N/A')),
            ('Average Recyclability (%)', stats.get('avg_recyclability', 'N/A'))
        ]
        
        for label, value in metrics_data:
            c.drawString(margin + 10, y, f'• {label}: {value}')
            y -= 14

        y -= 20

        # Charts Section
        if y < margin + 100:
            c.showPage()
            y = height - margin
        
        y = draw_section_header(c, y, 'Visual Analytics')
        
        # Embed charts with better spacing
        img_h = 220
        chart_configs = [
            ('co2Chart', 'CO2 Emissions Comparison'),
            ('costChart', 'Cost Analysis'),
            ('bioChart', 'Biodegradability Scores'),
            ('recycleChart', 'Recyclability Distribution'),
            ('whatIfChart', 'What-If Analysis')
        ]
        
        for key, title in chart_configs:
            if images.get(key):
                try:
                    # Check if we need a new page
                    if y - img_h - 30 < margin:
                        c.showPage()
                        y = height - margin
                    
                    # Draw chart title
                    c.setFont('Helvetica-Bold', 12)
                    c.drawString(margin, y, title)
                    y -= 18
                    
                    # Draw chart image
                    img = ImageReader(io.BytesIO(images[key]))
                    c.drawImage(img, margin, y - img_h, width=width-2*margin, height=img_h, preserveAspectRatio=True)
                    y -= (img_h + 20)
                except Exception:
                    logging.exception('Failed to embed image %s', key)
                    continue

        # Top Performers Section
        if y < margin + 150:
            c.showPage()
            y = height - margin
        
        y = draw_section_header(c, y, 'Top Performing Materials')
        
        # Low CO2 Materials
        c.setFont('Helvetica-Bold', 11)
        c.drawString(margin, y, 'Lowest CO2 Emissions')
        y -= 16
        c.setFont('Helvetica', 10)
        for i, item in enumerate(lowest_co2[:limit], 1):
            if y < margin + 30:
                c.showPage()
                y = height - margin
            line = f"{i}. {item['Material_Type']} — CO2: {item['CO2_Emission_Score']}"
            c.drawString(margin + 15, y, line)
            y -= 13

        y -= 10

        # High Biodegradability
        if y < margin + 100:
            c.showPage()
            y = height - margin
        
        c.setFont('Helvetica-Bold', 11)
        c.drawString(margin, y, 'Highest Biodegradability')
        y -= 16
        c.setFont('Helvetica', 10)
        for i, item in enumerate(highest_bio[:limit], 1):
            if y < margin + 30:
                c.showPage()
                y = height - margin
            line = f"{i}. {item['Material_Type']} — Biodegradability: {item['Biodegradability_Score']}%"
            c.drawString(margin + 15, y, line)
            y -= 13

        # Footer
        c.showPage()
        c.setFont('Helvetica-Oblique', 9)
        c.drawString(margin, margin - 20, 'EcoPackAI © 2026 | AI-Powered Sustainable Packaging Intelligence')
        
        c.save()
        buffer.seek(0)
        return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='ecopackai_dashboard_report.pdf')
    except Exception as e:
        logging.exception('Export PDF failed')
        return jsonify({'error': str(e)}), 500


# ==========================================
# 5. FRONTEND ROUTES
# ==========================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/categories')
def categories():
    return render_template('categories.html')

@app.route('/how-it-works')
def how_it_works():
    return render_template('how-it-works.html')

@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == '__main__':
    # Pre-warm cache to avoid delay on first request
    print("Pre-loading materials data...")
    get_materials()
    print("Materials data loaded.")
    
    # Use PORT from environment variable for Cloud Run compatibility
    app.run(host='0.0.0.0', port=PORT, debug=(ENVIRONMENT == 'development'))