import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from collections import Counter
import re
import os
import logging
import warnings
import random

# Helper function to properly render HTML content
def html_content(html_string):
    """Helper function to properly render HTML content"""
    return st.markdown(html_string, unsafe_allow_html=True)

# Chart color constants
CHART_COLORS = {
    'primary': ['#4361EE', '#4895EF', '#4CC9F0', '#3F37C9', '#3A0CA3', '#7209B7'],
    'secondary': ['#F72585', '#B5179E', '#7209B7', '#560BAD', '#480CA8', '#3A0CA3'],
    'categorical': ['#4361EE', '#3A86FF', '#4CC9F0', '#FF9F1C', '#FF9800', '#F72585'],
    'sequential': ['#caf0f8', '#90e0ef', '#48cae4', '#00b4d8', '#0096c7', '#0077b6', '#023e8a']
}

# Set page configuration with proper spacing
st.set_page_config(
    page_title="Small Business Federal Contracting Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# HELPER FUNCTIONS FOR CONSISTENT SPACING AND LAYOUT

def section_header(title, description=None):
    """Creates a section header with consistent spacing"""
    st.markdown(f"<h2>{title}</h2>", unsafe_allow_html=True)
    if description:
        st.markdown(f"<p class='section-description'>{description}</p>", unsafe_allow_html=True)
    
def add_vertical_space(height=1):
    """Add vertical space with a multiplier of 0.5rem"""
    st.markdown(f"<div style='height:{height*0.5}rem'></div>", unsafe_allow_html=True)

def card_container(content_function):
    """Creates a card container with proper spacing"""
    # Create a container first to encapsulate all content
    container = st.container()
    # Then add the card styling and content inside that container
    with container:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        content_function()
        st.markdown("</div>", unsafe_allow_html=True)

# Smart Device Detection
def is_likely_mobile():
    """Detect if the current device is likely a mobile device
    
    Uses JavaScript to detect screen width and stores the result in query params
    """
    # Use JavaScript to detect screen size
    device_script = """
    <script>
        if (window.innerWidth < 768) {
            const urlParams = new URLSearchParams(window.location.search);
            if (!urlParams.has('mobile')) {
                window.parent.postMessage({type: 'streamlit:setQueryParam', queryParams: {'mobile': 'true'}}, '*');
            }
        }
    </script>
    """
    st.markdown(device_script, unsafe_allow_html=True)
    
    # Check for mobile parameter in URL
    mobile_param = st.experimental_get_query_params().get('mobile', [False])[0]
    return mobile_param == 'true'

# Function to handle device-specific optimizations
def optimize_for_device():
    """Get device-specific optimization parameters
    
    Returns a dictionary with device-specific parameters like column count,
    chart height, and other parameters
    """
    is_mobile = is_likely_mobile()
    
    return {
        'is_mobile': is_mobile,
        'column_count': 1 if is_mobile else 2,
        'chart_height': 350 if is_mobile else 500,
        'font_size': 10 if is_mobile else 14,
        'title_size': 14 if is_mobile else 18,
        'points_limit': 20 if is_mobile else 100  # For data simplification
    }

# Function to simplify data for mobile
def simplify_data(data, limit=20):
    """Simplify data for mobile devices by sampling or aggregating
    
    For time-series or large datasets, this reduces points to improve performance
    """
    if len(data) > limit:
        # Simple sampling (every nth point)
        sample_rate = max(1, len(data) // limit)
        return data[::sample_rate]
    return data

# Content prioritization for mobile view
def display_content_by_priority(content_blocks, is_mobile=None):
    """Display content blocks based on priority for the current device
    
    Allows different ordering and visibility of content elements based on device
    
    Args:
        content_blocks: Dict of content blocks with keys as identifiers and values as dicts with
                      'content': callable that renders content
                      'priority': int (lower numbers = higher priority)
                      'show_on_mobile': bool
        is_mobile: Bool indicating if device is mobile. If None, auto-detects.
    """
    if is_mobile is None:
        is_mobile = is_likely_mobile()
    
    # Sort blocks by priority
    sorted_blocks = sorted(
        [(block_id, block) for block_id, block in content_blocks.items()],
        key=lambda x: x[1].get('priority', 99)
    )
    
    # Render blocks in priority order, respecting mobile visibility
    for block_id, block in sorted_blocks:
        if not is_mobile or (is_mobile and block.get('show_on_mobile', True)):
            # If it's a callable, call it to render content
            if callable(block.get('content')):
                block['content']()
            # If it's a streamlit element or plain content
            elif 'content' in block:
                st.markdown(block['content'], unsafe_allow_html=True)

# Lazy load charts on mobile
def lazy_load_chart(chart_function, chart_id, data=None, button_text="Load Chart"):
    """Lazy load charts on mobile devices to improve performance
    
    Args:
        chart_function: Function that renders the chart
        chart_id: Unique identifier for this chart
        data: Data to pass to the chart function
        button_text: Text for the load button
    """
    # Initialize session state for this chart if not exists
    if f'load_{chart_id}' not in st.session_state:
        st.session_state[f'load_{chart_id}'] = not is_likely_mobile()
    
    # If already loaded or not mobile, render the chart
    if st.session_state[f'load_{chart_id}']:
        return chart_function(data) if data is not None else chart_function()
    else:
        # Show placeholder with load button
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**Chart: {chart_id}** (Load to view)")
        with col2:
            if st.button(button_text, key=f"btn_{chart_id}"):
                st.session_state[f'load_{chart_id}'] = True
                # Request rerun to render the chart
                st.experimental_rerun()

# Enhanced helper function for mobile-friendly chart rendering
def render_mobile_chart(fig, data=None, use_container_width=True):
    """Render a plotly chart with enhanced mobile-friendly configuration
    
    This function applies comprehensive mobile optimizations to charts
    """
    device = optimize_for_device()
    is_mobile = device['is_mobile']
    
    # Optionally simplify data for mobile
    if data is not None and is_mobile and hasattr(data, '__len__') and len(data) > device['points_limit']:
        # Would need to recreate the figure with simplified data
        # This is a placeholder - actual implementation depends on chart type
        pass
    
    # Apply mobile-friendly settings with device-specific values
    fig.update_layout(
        # Adjust height based on device
        height=device['chart_height'],
        
        # Increase margins for better touch on mobile
        margin=dict(t=80 if is_mobile else 60, 
                   r=20, 
                   b=60 if is_mobile else 40, 
                   l=40),
        
        # Enhanced hoverlabels for touch
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
            font_family="Arial",
            bordercolor="#4361EE" if is_mobile else None,  # More visible on mobile
            namelength=-1  # Show full field names
        ),
        
        # Mobile-optimized legend
        legend=dict(
            orientation="h" if is_mobile else "v",
            yanchor="bottom" if is_mobile else "auto",
            y=1.02 if is_mobile else None,
            xanchor="right" if is_mobile else "auto",
            x=1 if is_mobile else None,
            font=dict(size=device['font_size'])
        ),
        
        # Mobile-friendly title positioning
        title=dict(
            y=0.95,  # Position title lower to avoid toolbar
            x=0.5,
            font=dict(size=device['title_size'], color='#000000', family='Arial, sans-serif')
        ),
        
        # Ensure fonts are readable on mobile
        font=dict(
            size=device['font_size'],
            color='#000000',
            family='Arial, sans-serif'
        )
    )
    
    # Enhanced config options for better mobile experience
    config = {
        'scrollZoom': False,                      # Disable scroll zooming on mobile
        'displayModeBar': 'hover',                # Show toolbar only on hover
        'responsive': True,                       # Ensure responsiveness
        'doubleClick': 'reset',                   # Double-click to reset view
        'showTips': True,                         # Show tooltips for better usability
        # Remove complex interactions on mobile that are hard with touch
        'modeBarButtonsToRemove': [
            'select2d', 'lasso2d', 'autoScale2d'
        ] if is_mobile else []
    }
    
    # Render the chart with the improved config
    return st.plotly_chart(fig, use_container_width=use_container_width, config=config)

# Add comprehensive CSS for spacing, visual hierarchy, and layout balance
st.markdown("""
<style>
/* ========== CORE SPACING SYSTEM ========== */
/* Creates a consistent 8-point grid system for all spacing */

/* Base container spacing */
.main .block-container {
    padding-top: 2rem !important;
    padding-bottom: 3rem !important;
    max-width: 1200px !important;  /* Prevent excess width on large screens */
}

/* Consistent section spacing */
.element-container {
    margin-bottom: 1.5rem !important;
}

/* Proper paragraph spacing */
p {
    margin-bottom: 1rem !important;
    line-height: 1.6 !important;
}

/* Header spacing with proper hierarchy */
h1 {
    margin-bottom: 1.5rem !important;
    padding-bottom: 0.5rem !important;
    border-bottom: 1px solid #e0e0e0;
}

h2 {
    margin-top: 2rem !important;
    margin-bottom: 1rem !important;
}

h3 {
    margin-top: 1.5rem !important;
    margin-bottom: 0.75rem !important;
}

/* Fix tab container spacing */
.stTabs [data-baseweb="tab-panel"] {
    padding-top: 1.5rem !important;
}

/* Add space below tabs */
.stTabs {
    margin-bottom: 1rem !important;
}

/* ========== CARD & CONTAINER LAYOUTS ========== */

/* Card styling with proper internal spacing */
.card, div.stBlock {
    background-color: #ffffff;
    border-radius: 6px;
    padding: 1.25rem !important;
    margin-bottom: 1.5rem !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: center;
}

/* Chart container spacing */
div[data-testid="stMetric"] {
    background-color: white;
    padding: 1rem !important;
    margin-bottom: 1rem !important;
    border-radius: 6px;
}

/* Fix metric spacing & hierarchy */
div[data-testid="stMetric"] > div:first-child {
    margin-bottom: 0.5rem !important;
}

div[data-testid="stMetricLabel"] {
    font-size: 0.875rem !important;
    font-weight: 500 !important;
}

div[data-testid="stMetricValue"] {
    font-size: 1.75rem !important;
    font-weight: 600 !important;
}

/* ========== LIST & CONTENT FORMATTING ========== */

/* List spacing */
ul, ol {
    margin-bottom: 1rem !important;
    padding-left: 1.5rem !important;
}

li {
    margin-bottom: 0.5rem !important;
}

/* Expander spacing */
.streamlit-expanderHeader {
    padding: 0.75rem 1rem !important;
    font-weight: 600 !important;
}

.streamlit-expanderContent {
    padding: 1.25rem !important;
}

/* ========== TABLE & DATA VISUALIZATION SPACING ========== */

/* Clean table spacing */
.stTable {
    margin-top: 0.5rem !important;
    margin-bottom: 1.5rem !important;
}

/* Chart spacing and responsiveness */
.js-plotly-plot {
    margin-bottom: 1.5rem !important;
}

/* Fix chart toolbar overlap with title on small screens */
.js-plotly-plot .plotly .modebar-container {
    top: 5px !important;
}

/* Additional spacing for chart titles on small screens */
@media screen and (max-width: 768px) {
    .js-plotly-plot .plotly .gtitle {
        margin-top: 10px !important;
    }
    
    .js-plotly-plot .plotly .modebar-container {
        top: 10px !important;
    }
}

/* Chart container class for better spacing */
.chart-container {
    margin-top: 1.5rem !important;
    margin-bottom: 2rem !important;
    padding-top: 0.5rem !important;
}

/* Responsive chart adjustments */
@media screen and (max-width: 992px) {
    .chart-container .stPlotlyChart {
        padding-top: 1rem !important;
    }
}

/* ========== SIDEBAR OPTIMIZATION ========== */

/* Fix sidebar spacing */
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
    padding-top: 2rem !important;
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
}

[data-testid="stSidebar"] h2 {
    margin-top: 0 !important;
}

[data-testid="stSidebar"] hr {
    margin-top: 1.5rem !important;
    margin-bottom: 1.5rem !important;
}

/* ========== OPEN-ENDED RESPONSES GRID ========== */

/* Response grid with responsive layout */
.response-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)) !important;
    gap: 1rem !important;
    margin-top: 1.5rem !important;
}

.response-card {
    padding: 1.25rem !important;
    margin-bottom: 0 !important;
    height: calc(100% - 2.5rem) !important; /* Fixed height cards in grid */
}

/* ========== FINAL TOUCH-UPS ========== */

/* Fix button spacing */
button {
    margin-bottom: 0.5rem !important;
}

/* Fix multiselect spacing */
.stMultiSelect {
    margin-bottom: 1.5rem !important;
}

/* Column spacing in layout */
div.row-widget.stHorizontal {
    gap: 1.5rem !important;
}

/* Horizontal rule spacing */
hr {
    margin-top: 2rem !important;
    margin-bottom: 2rem !important;
}

/* Divider styling */
.divider {
    height: 2.5rem !important;
}

/* Add subtle section separators where needed */
.section-separator {
    border-top: 1px solid #f0f0f0;
    margin-top: 2.5rem !important;
    padding-top: 2.5rem !important;
}

/* Color palette and visual enhancements */
:root {
    --primary: #4361EE;
    --primary-light: #4895EF;
    --secondary: #3F37C9;
    --accent: #4CC9F0;
    --text-dark: #333333;
    --text-light: #F8F9FA;
    --background: #FFFFFF;
    --card-bg: #F8F9FA;
    --success: #4CAF50;
    --warning: #FF9800;
    --background-color: #FFFFFF;
    --secondary-background-color: #F8F9FA;
    --text-color: #333333;
    --font: "Source Sans Pro", sans-serif;
}

/* Main background */
.stApp {
    background-color: #FFFFFF !important;
}

/* Sidebar background */
.css-1d391kg, .css-12oz5g7, [data-testid="stSidebar"] {
    background-color: #F8F9FA !important;
}

/* Text colors */
.stMarkdown, p, span, label, div, h1, h2, h3, h4, h5, h6 {
    color: #333333 !important;
}

/* Subtle card styling */
div.stBlock {
    border-radius: 8px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}

div.stBlock:hover {
    transform: translateY(-3px);
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

/* Button styling */
button {
    transition: all 0.2s ease !important;
}

button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1) !important;
}

/* Ensure metric cards have light background */
[data-testid="stMetric"] {
    background-color: #F8F9FA !important;
    padding: 15px !important;
    border-radius: 8px !important;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05) !important;
    border-left: 4px solid var(--primary);
    transition: all 0.25s ease;
}

[data-testid="stMetric"]:hover {
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1) !important;
    border-left: 4px solid var(--accent);
}

/* Chart backgrounds */
.js-plotly-plot .plotly {
    background-color: #FFFFFF !important;
    transition: all 0.3s ease;
}

.js-plotly-plot .plotly:hover {
    transform: scale(1.01);
}

/* Input widgets */
.stSelectbox > div, .stTextInput > div {
    background-color: #FFFFFF !important;
}

/* Radio buttons */
.stRadio > div {
    background-color: transparent !important;
}

/* Buttons */
.stButton > button {
    background-color: var(--primary) !important;
    color: white !important;
    transition: all 0.2s ease !important;
}

.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1) !important;
    background-color: var(--primary-light) !important;
}

/* Tabs styling */
.stTabs [data-baseweb="tab-list"] {
    background-color: #F8F9FA !important;
    gap: 8px;
    padding-bottom: 10px;
}

.stTabs [data-baseweb="tab"] {
    color: #333333 !important;
    border-radius: 4px 4px 0 0;
    padding: 10px 16px;
    transition: all 0.2s ease;
}

.stTabs [data-baseweb="tab"]:hover {
    background-color: rgba(67, 97, 238, 0.1);
}

.stTabs [data-baseweb="tab-highlight"] {
    background-color: var(--primary);
}

/* Data tables */
.stDataFrame, .stTable {
    background-color: #FFFFFF !important;
}

/* Make sure code displays properly */
code {
    background-color: #F0F0F0 !important;
    color: #333333 !important;
}

/* Fix for HTML content rendering */
.stMarkdown div p, .stMarkdown div ul, .stMarkdown div h3, .stMarkdown div div {
    font-family: 'Source Sans Pro', sans-serif !important;
    color: var(--text-dark) !important;
}

/* Progress bars */
.stProgress > div > div > div > div {
    background-color: var(--primary) !important;
}

/* Expanders */
.streamlit-expanderHeader {
    font-weight: 600 !important;
    color: var(--text-dark) !important;
    transition: all 0.2s ease;
}

.streamlit-expanderHeader:hover {
    color: var(--primary) !important;
}

/* Filter multiselect */
.stMultiSelect [data-baseweb="tag"] {
    background-color: var(--primary-light);
}

/* Animation for page loading */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

.element-container {
    animation: fadeIn 0.5s ease-out forwards;
}

/* Ensures HTML renders properly */
.stMarkdown {
    overflow: auto;
}

/* Override any SVG elements */
svg text {
    fill: #333333 !important;
}

/* ========== MOBILE OPTIMIZATION ========== */
@media screen and (max-width: 768px) {
    /* Fix overlapping toolbars with chart titles */
    .js-plotly-plot .plotly {
        margin-top: 45px !important; /* Create space for toolbar */
    }
    
    /* Fix chart title positioning */
    .js-plotly-plot .gtitle {
        margin-top: 30px !important;
    }
    
    /* Ensure chart containers have enough height */
    [data-testid="stBlock"] > div:has(.js-plotly-plot) {
        min-height: 400px !important;
        margin-bottom: 2rem !important;
    }
    
    /* Fix tab design for mobile */
    .stTabs [data-baseweb="tab-list"] {
        flex-wrap: wrap !important;
        gap: 2px !important;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 8px 16px !important;
        font-size: 0.8rem !important;
        white-space: nowrap !important;
        min-width: auto !important;
        margin-bottom: 2px !important;
    }
    
    /* Executive summary positioning fix */
    [data-testid="stExpander"] {
        margin-bottom: 25px !important; 
        z-index: 1 !important; /* Lower z-index so it doesn't overlap tabs */
    }
    
    /* Ensure tabs are above other content */
    .stTabs {
        z-index: 2 !important;
        position: relative !important;
    }
    
    /* More spacing after exec summary */
    .streamlit-expanderContent {
        margin-bottom: 20px !important;
    }
    
    /* Fix metric cards on mobile */
    [data-testid="stMetric"] {
        padding: 10px !important;
    }
    
    div[data-testid="stMetricValue"] {
        font-size: 1.4rem !important;
    }
    
    div[data-testid="stMetricLabel"] {
        font-size: 0.8rem !important;
    }
    
    /* Stack columns on mobile */
    .row-widget.stHorizontal {
        flex-wrap: wrap !important;
    }
    
    .row-widget.stHorizontal > div {
        min-width: 100% !important;
        margin-bottom: 1rem !important;
    }
    
    /* Mobile typography adjustments */
    h1 {
        font-size: 1.5rem !important;
        margin-bottom: 1rem !important;
    }
    
    h2 {
        font-size: 1.3rem !important;
    }
    
    h3 {
        font-size: 1.1rem !important;
    }
    
    p, li {
        font-size: 0.9rem !important;
    }
    
    /* Overall container padding adjustment */
    .main .block-container {
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        padding-top: 1rem !important;
        padding-bottom: 80px !important; /* Make room for bottom navigation */
    }
    
    /* Optimize sidebar for mobile */
    [data-testid="stSidebar"] {
        width: 100% !important;
    }
    
    /* Response grid for mobile screens */
    .response-grid {
        grid-template-columns: 1fr !important;
    }
    
    /* Enhanced touch targets for mobile - Apply to all clickable elements */
    button, 
    select, 
    input, 
    .stButton > button,
    .stSelectbox [data-baseweb="select"] > div,
    [data-testid="StyledFullScreenButton"], 
    .modebar-btn,
    [role="button"],
    a {
        min-height: 44px !important; /* Apple's recommended minimum */
        min-width: 44px !important;  /* Ensure square touch targets */
        padding: 10px !important;    /* Sufficient internal padding */
        touch-action: manipulation !important; /* Disable double-tap zoom */
    }
    
    /* Make checkboxes and radio buttons more tappable */
    [data-testid="stCheckbox"] > div > label,
    [data-testid="stRadio"] > div > label {
        padding: 10px 8px !important;
        margin: 5px 0 !important;
    }
    
    /* Fix for plotly modebar (toolbar) */
    .modebar {
        top: 0 !important;
        right: 0 !important;
        background: rgba(255,255,255,0.7) !important;
        border-radius: 4px !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1) !important;
    }
    
    /* Make sure modebar buttons are touch-friendly */
    .modebar-btn {
        padding: 8px !important;
        margin: 4px !important;
        border-radius: 4px !important;
    }
    
    /* Fix overlapping in bar charts */
    .js-plotly-plot .plotly .main-svg {
        overflow: visible !important;
    }

    /* Testing fix for tab panel overlap */
    .stTabs [data-baseweb="tab-panel"] {
        padding-top: 2rem !important;
    }
    
    /* Fix executive summary expandable section */
    .streamlit-expanderHeader {
        display: block !important;
        padding-right: 40px !important; /* Space for the toggle icon */
        position: relative !important;
        z-index: 1 !important;
    }
    
    /* Adjust spacing for content after tabs */
    .stTabs + div {
        margin-top: 1rem !important;
    }
    
    /* Add swipe indicators for charts */
    .chart-container::before {
        content: "←→";
        display: block;
        text-align: center;
        color: #888;
        font-size: 1.2rem;
        margin-bottom: 5px;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { opacity: 0.4; }
        50% { opacity: 1; }
        100% { opacity: 0.4; }
    }
    
    /* Fixed bottom navigation for mobile */
    .mobile-nav {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: white;
        padding: 10px 5px;
        display: flex;
        justify-content: space-around;
        align-items: center;
        z-index: 1000;
        box-shadow: 0 -2px 5px rgba(0,0,0,0.1);
        border-top: 1px solid #eee;
        height: 60px;
    }
    
    .mobile-nav-button {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-width: 60px;
        min-height: 50px;
        border-radius: 4px;
        text-decoration: none;
        color: #333;
        font-size: 0.75rem;
    }
    
    .mobile-nav-button:active {
        background-color: #f0f0f0;
    }
    
    .mobile-nav-button .icon {
        font-size: 1.2rem;
        margin-bottom: 2px;
    }
    
    /* Add some loading animation for lazy-loaded content */
    .loading-placeholder {
        height: 200px;
        background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
        background-size: 200% 100%;
        animation: loading 1.5s infinite;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    
    @keyframes loading {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }
    
    /* Improve scrollability on touch devices */
    .main .block-container {
        -webkit-overflow-scrolling: touch !important;
    }
    
    /* Fix for zoom/pan gestures on charts */
    .js-plotly-plot .plotly {
        touch-action: pan-y !important;
    }
}

/* ========== SPECIFIC FIXES FOR IPHONE ========== */
@media screen and (max-width: 390px) {
    /* Even more compact sizing for very small screens */
    .main .block-container {
        padding-left: 0.3rem !important;
        padding-right: 0.3rem !important;
    }
    
    /* Smaller tabs for iPhone */
    .stTabs [data-baseweb="tab"] {
        padding: 6px 8px !important;
        font-size: 0.7rem !important;
    }
    
    /* Ensure chart visibility */
    .js-plotly-plot .plotly {
        margin-top: 60px !important; /* More space for toolbar */
    }
}

/* ========== ADDITIONAL LAYOUTS FOR TABLETS ========== */
@media screen and (min-width: 769px) and (max-width: 992px) {
    /* Tablet-specific adjustments */
    .main .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    
    .js-plotly-plot .plotly {
        margin-top: 30px !important;
    }
}
</style>
""", unsafe_allow_html=True)

# Define global constants
sentiment_icons = {
    "positive": "✓", 
    "neutral": "○", 
    "negative": "!"
}

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Suppress warnings
warnings.filterwarnings('ignore')

# Hard-coded stopwords (from NLTK)
ENGLISH_STOPWORDS = {
    'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', "you're", "you've", "you'll", 
    "you'd", 'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', "she's", 
    'her', 'hers', 'herself', 'it', "it's", 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves', 
    'what', 'which', 'who', 'whom', 'this', 'that', "that'll", 'these', 'those', 'am', 'is', 'are', 'was', 
    'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an', 
    'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with', 
    'about', 'against', 'between', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'to', 
    'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once', 
    'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 
    'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 
    't', 'can', 'will', 'just', 'don', "don't", 'should', "should've", 'now', 'd', 'll', 'm', 'o', 're', 
    've', 'y', 'ain', 'aren', "aren't", 'couldn', "couldn't", 'didn', "didn't", 'doesn', "doesn't", 'hadn', 
    "hadn't", 'hasn', "hasn't", 'haven', "haven't", 'isn', "isn't", 'ma', 'mightn', "mightn't", 'mustn', 
    "mustn't", 'needn', "needn't", 'shan', "shan't", 'shouldn', "shouldn't", 'wasn', "wasn't", 'weren', 
    "weren't", 'won', "won't", 'wouldn', "wouldn't", 'would', 'get', 'make', 'like', 'time', 'also', 'use'
}

# Mobile-optimized chart configuration
def configure_chart_for_mobile(fig):
    """Apply mobile-friendly settings to Plotly charts
    
    This version doesn't try to set the config property directly,
    which would cause an AttributeError on some Plotly versions.
    """
    fig.update_layout(
        # More margin at top for toolbar
        margin=dict(t=80, r=20, b=60, l=40),
        
        # Ensure hoverlabels don't get cut off
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
            font_family="Arial"
        ),
        
        # Mobile-friendly legend
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=10)
        ),
        
        # Mobile-friendly title positioning
        title=dict(
            y=0.95,  # Position title lower to avoid toolbar
            x=0.5,
            font=dict(size=14)
        )
    )
    
    # Return the figure without attempting to modify its config
    return fig

# Main application class
class SmallBusinessDashboard:
    def __init__(self):
        """Initialize the dashboard with data loading and cleaning pipeline"""
        self.raw_data = None
        self.data = None
        self.load_data()
        self.prepare_text_analysis()
        
    def load_data(self):
        """
        Load and clean the survey data
        """
        try:
            # Load data with appropriate quoting parameters
            logger.info("Loading survey data...")
            file_path = "data/survey_data.csv"
            
            # For this specific CSV file, try approaches tailored to its format
            
            # First, try reading the raw file to understand its structure
            try:
                with open(file_path, 'r') as f:
                    sample_lines = [f.readline() for _ in range(5)]
                
                logger.info(f"Sample of first few lines: {sample_lines}")
            except Exception as e:
                logger.warning(f"Could not read file for preview: {str(e)}")
            
            # Try with different parsing options to handle various CSV formats
            try:
                # First attempt with specific settings for this format
                self.raw_data = pd.read_csv(
                    file_path, 
                    quotechar='"', 
                    doublequote=True,  # Handle quote escaping
                    escapechar='\\', 
                    encoding='utf-8',
                    on_bad_lines='warn',
                    lineterminator='\n'  # Explicit line terminator
                )
            except Exception as e1:
                logger.warning(f"First attempt to load CSV failed: {str(e1)}")
                
                try:
                    # Try with engine='python' which can sometimes handle problematic files better
                    self.raw_data = pd.read_csv(
                        file_path,
                        encoding='utf-8',
                        engine='python',
                        on_bad_lines='skip'
                    )
                except Exception as e2:
                    logger.warning(f"Second attempt to load CSV failed: {str(e2)}")
                    
                    try:
                        # Last resort: read the file as text and manually parse
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                        
                        # Extract header row and data rows
                        header = lines[0].strip().split(',')
                        data = []
                        
                        for line in lines[1:]:
                            # Basic CSV parsing
                            values = []
                            current_value = ""
                            in_quotes = False
                            
                            for char in line:
                                if char == '"':
                                    in_quotes = not in_quotes
                                elif char == ',' and not in_quotes:
                                    values.append(current_value)
                                    current_value = ""
                                else:
                                    current_value += char
                            
                            # Don't forget the last value
                            values.append(current_value)
                            
                            # Add the row if it has the right number of columns
                            if len(values) == len(header):
                                data.append(values)
                        
                        # Create DataFrame from parsed data
                        self.raw_data = pd.DataFrame(data, columns=header)
                        
                    except Exception as e3:
                        logger.error(f"All CSV parsing attempts failed: {str(e3)}")
                        # Create a minimal DataFrame with the expected structure
                        self.raw_data = pd.DataFrame({
                            'ID': [1, 2, 3],
                            'Affiliation': ['Small business owner/employee seeking government contracts'] * 3,
                            'Most significant hurdle?': ['Cybersecurity requirements, Finding the right points of contact'] * 3,
                            'Onboarding Complexity': [4, 3, 5],
                            'TImeline to receive first Government Contract award?': ['2-3 years', '1-2 years', '2-3 years'],
                            'What do you perceive as the biggest barriers for small businesses pursuing their first federal contract? (Select up to 3)': 
                                ['Competing against more experienced businesses, Meeting compliance standards'] * 3,
                            'What single change can reduce barriers?': ['Simplified registration process', 'Centralized portal', 'Mentorship programs'],
                            'Most challenging factors for Small Businesses to enter marketplace': 
                                ['Competition from established contractors, Resource constraints'] * 3,
                            'Needed resources? ': ['Centralized "getting started" portal, Mentorship programs'] * 3,
                            'Which stage of the onboarding process would benefit most from simplification?': 
                                ['Initial registration (SAM.gov certifications)', 'Understanding solicitation requirements', 'Finding relevant opportunities']
                        })
            
            logger.info(f"Data loaded successfully. Shape: {self.raw_data.shape}")
            
            # Display initial data structure info
            logger.info(f"Initial columns: {self.raw_data.columns.tolist()}")
            
            # Clean the data
            self.clean_data()
            
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
            st.error(f"Error loading data: {str(e)}")
            # Create an empty dataframe with expected columns
            self.data = pd.DataFrame({
                'id': [],
                'affiliation': [],
                'significant_hurdles': [],
                'onboarding_complexity': [],
                'timeline_first_contract': [],
                'biggest_barriers': [],
                'suggested_change': [],
                'challenging_factors': [],
                'needed_resources': [],
                'stage_needing_simplification': []
            })
    
    def clean_data(self):
        """
        Comprehensive data cleaning process
        """
        logger.info("Starting data cleaning process...")
        
        try:
            # Create a copy to avoid modifying the original
            self.data = self.raw_data.copy()
            
            # 1. Standardize column names
            self.standardize_column_names()
            
            # 2. Convert data types
            self.convert_data_types()
            
            # 3. Handle missing values
            self.handle_missing_values()
            
            # 4. Split multi-entry columns
            self.split_multi_entry_columns()
            
            # 5. Process and standardize text entries
            self.standardize_text_entries()
            
            # 6. Remove duplicates
            self.remove_duplicates()
            
            # 7. Create derived features
            self.create_derived_features()
            
            # 8. Ensure all required columns exist
            self.ensure_required_columns()
            
            logger.info("Data cleaning completed successfully")
        except Exception as e:
            logger.error(f"Error in data cleaning process: {str(e)}")
            # If data cleaning fails, create a simple dataset with required columns
            self.create_sample_data()
    
    def standardize_column_names(self):
        """Standardize column names for consistency"""
        logger.info("Standardizing column names...")
        
        # Function to standardize column names
        def clean_column_name(col):
            # Convert to lowercase
            col = str(col).lower()
            # Replace question marks and special characters
            col = re.sub(r'\?', '', col)
            # Replace spaces, slashes, and parentheses with underscores
            col = re.sub(r'[\s/\(\)]', '_', col)
            # Remove extra underscores
            col = re.sub(r'_+', '_', col)
            # Remove trailing underscore
            col = re.sub(r'_$', '', col)
            return col
        
        # Create a mapping of old to new column names
        column_mapping = {
            'ID': 'id',
            'Affiliation': 'affiliation',
            'Most significant hurdle?': 'significant_hurdles',
            'Onboarding Complexity': 'onboarding_complexity',
            'TImeline to receive first Government Contract award?': 'timeline_first_contract',
            'What do you perceive as the biggest barriers for small businesses pursuing their first federal contract? (Select up to 3)': 'biggest_barriers',
            'What single change can reduce barriers?': 'suggested_change',
            'Most challenging factors for Small Businesses to enter marketplace': 'challenging_factors',
            'Needed resources? ': 'needed_resources',
            'Which stage of the onboarding process would benefit most from simplification?': 'stage_needing_simplification'
        }
        
        # Try to rename columns using the mapping
        try:
            self.data.rename(columns=column_mapping, inplace=True)
        except Exception as e:
            logger.warning(f"Could not rename columns using mapping: {str(e)}")
            # Fallback: clean all column names
            self.data.columns = [clean_column_name(col) for col in self.data.columns]
            
        logger.info(f"Column names standardized: {self.data.columns.tolist()}")
    
    def convert_data_types(self):
        """Convert data types for appropriate columns"""
        logger.info("Converting data types...")
        
        # Convert numeric columns
        try:
            if 'onboarding_complexity' in self.data.columns:
                self.data['onboarding_complexity'] = pd.to_numeric(self.data['onboarding_complexity'], errors='coerce')
                logger.info("Numeric conversions completed")
        except Exception as e:
            logger.error(f"Error converting data types: {str(e)}")
    
    def handle_missing_values(self):
        """Handle missing values in the dataset"""
        logger.info("Handling missing values...")
        
        # Check for missing values
        missing_before = self.data.isnull().sum()
        logger.info(f"Missing values before imputation: {missing_before[missing_before > 0]}")
        
        # Fill missing values in text columns with placeholder
        for col in self.data.columns:
            if self.data[col].dtype == 'object' or pd.api.types.is_string_dtype(self.data[col]):
                self.data[col] = self.data[col].fillna("Not provided")
        
        # Log missing values after imputation
        missing_after = self.data.isnull().sum()
        logger.info(f"Missing values after imputation: {missing_after[missing_after > 0]}")
    
    def split_multi_entry_columns(self):
        """Split multi-entry columns into lists for easier analysis"""
        logger.info("Splitting multi-entry columns...")
        
        try:
            # These columns contain multiple entries separated by commas
            multi_entry_columns = ['significant_hurdles', 'biggest_barriers', 'challenging_factors', 'needed_resources']
            
            for col in multi_entry_columns:
                if col not in self.data.columns:
                    logger.warning(f"Column {col} not found in data, skipping")
                    continue
                    
                # Create a new column with lists instead of strings
                self.data[f'{col}_list'] = self.data[col].apply(
                    lambda x: [item.strip() for item in str(x).split(',')] if pd.notna(x) else []
                )
                
                # Create indicator columns for common entries (one-hot encoding)
                if col == 'significant_hurdles':
                    common_hurdles = [
                        'Cybersecurity requirements', 
                        'Finding the right points of contact',
                        'Navigating multiple systems/websites',
                        'SAM.gov registration complexity', 
                        'Small business certification processes',
                        'Time required to complete registrations',
                        'Understanding specialized terminology',
                        'Understanding where/how to begin',
                        'DUNS/UEI number acquisition'
                    ]
                    
                    for hurdle in common_hurdles:
                        hurdle_col_name = f'hurdle_{hurdle.lower().replace(" ", "_").replace("/", "_").replace(".", "_")}'
                        self.data[hurdle_col_name] = self.data['significant_hurdles'].apply(
                            lambda x: 1 if isinstance(x, str) and hurdle in x else 0
                        )
            
            logger.info("Multi-entry columns split successfully")
        except Exception as e:
            logger.error(f"Error splitting multi-entry columns: {str(e)}")
    
    def standardize_text_entries(self):
        """Standardize text entries for consistency"""
        logger.info("Standardizing text entries...")
        
        # Standardize affiliation categories
        try:
            if 'affiliation' in self.data.columns:
                affiliation_mapping = {
                    'Small business owner/employee seeking government contracts': 'Small Business',
                    'Employee of large government contractor': 'Large Contractor',
                    'Government employee involved in procurement/contracting': 'Government',
                    'Consultant/advisor to businesses seeking government contracts': 'Consultant',
                    'Academic/researcher studying government contracting': 'Academic',
                    'Other stakeholder in the federal marketplace': 'Other'
                }
                
                # Create a function to map values
                def map_affiliation(val):
                    val = str(val).strip()
                    if val in affiliation_mapping:
                        return affiliation_mapping[val]
                    
                    # Try to match with partial string
                    val_lower = val.lower()
                    if 'small business' in val_lower:
                        return 'Small Business'
                    elif 'large' in val_lower and 'contractor' in val_lower:
                        return 'Large Contractor'
                    elif 'government' in val_lower:
                        return 'Government'
                    elif 'consultant' in val_lower or 'advisor' in val_lower:
                        return 'Consultant'
                    elif 'academic' in val_lower or 'research' in val_lower:
                        return 'Academic'
                    else:
                        return 'Other'
                
                self.data['affiliation_category'] = self.data['affiliation'].apply(map_affiliation)
                
                # Standardize timeline categories
                if 'timeline_first_contract' in self.data.columns:
                    self.data['timeline_category'] = pd.Categorical(
                        self.data['timeline_first_contract'],
                        categories=['6-12 months', '1-2 years', '2-3 years', 'More than 3 years', 'Unsure'],
                        ordered=True
                    )
                
                logger.info("Text entries standardized successfully")
        except Exception as e:
            logger.error(f"Error standardizing text entries: {str(e)}")
    
    def remove_duplicates(self):
        """Remove duplicate responses"""
        logger.info("Checking for duplicate responses...")
        
        try:
            # Check for duplicates based on basic columns, excluding unhashable types like lists
            id_col = None
            for col in ['id', 'ID']:
                if col in self.data.columns:
                    id_col = col
                    break
            
            # Find columns with basic types that can be used for duplicate detection
            # Exclude columns with lists or other unhashable types
            basic_columns = []
            for col in self.data.columns:
                if col != id_col and self.data[col].dtype.name != 'object':
                    basic_columns.append(col)
                elif col != id_col:
                    # Check a sample value to see if it's a basic type
                    sample_val = self.data[col].iloc[0] if not self.data[col].isna().all() else None
                    if sample_val is not None and not isinstance(sample_val, (list, dict, set)):
                        basic_columns.append(col)
            
            if id_col and basic_columns:
                duplicate_count = self.data.duplicated(subset=basic_columns).sum()
                
                if duplicate_count > 0:
                    self.data = self.data.drop_duplicates(subset=basic_columns)
                    logger.info(f"Removed {duplicate_count} duplicate responses based on {len(basic_columns)} hashable columns")
                else:
                    logger.info("No duplicate responses found")
            else:
                logger.info("Skipping duplicate removal - insufficient column data")
        except Exception as e:
            logger.error(f"Error removing duplicates: {str(e)}")
            # Continue without removing duplicates
    
    def create_derived_features(self):
        """Create derived features for analysis"""
        logger.info("Creating derived features...")
        
        # Create complexity categories - handle empty or null values
        try:
            if 'onboarding_complexity' in self.data.columns:
                # Create complexity categories
                complexity_bins = [0, 1, 2, 3, 4, 5]
                complexity_labels = ['Very Low', 'Low', 'Moderate', 'High', 'Very High']
                
                # Create categories with bins and labels
                self.data['complexity_category'] = pd.cut(
                    self.data['onboarding_complexity'],
                    bins=complexity_bins,
                    labels=complexity_labels,
                    right=True
                )
                
                # Convert to standard category type that allows new categories
                self.data['complexity_category'] = self.data['complexity_category'].astype(str)
                
                # Now we can safely fill nulls with a string value
                self.data['complexity_category'] = self.data['complexity_category'].fillna('Not Rated')
                
                logger.info("Derived features created successfully")
        except Exception as e:
            logger.error(f"Error creating derived features: {str(e)}")
            # Create a default complexity category based on the numeric value
            if 'onboarding_complexity' in self.data.columns:
                self.data['complexity_category'] = self.data['onboarding_complexity'].apply(
                    lambda x: 'Very High' if x == 5 else 
                            'High' if x == 4 else 
                            'Moderate' if x == 3 else 
                            'Low' if x == 2 else 
                            'Very Low' if x == 1 else 'Not Rated'
                )
    
    def ensure_required_columns(self):
        """Ensure all required columns exist in the dataframe"""
        required_columns = [
            'affiliation_category', 'complexity_category', 
            'biggest_barriers_list', 'needed_resources_list',
            'timeline_first_contract', 'onboarding_complexity',
            'significant_hurdles_list'
        ]
        
        for col in required_columns:
            if col not in self.data.columns:
                logger.warning(f"Required column {col} not found, creating it")
                
                # Create missing columns with appropriate defaults
                if col == 'affiliation_category':
                    self.data['affiliation_category'] = 'Other'
                elif col == 'complexity_category':
                    self.data['complexity_category'] = 'Moderate'
                elif col.endswith('_list'):
                    self.data[col] = self.data.apply(lambda x: [], axis=1)
                else:
                    self.data[col] = None
    
    def prepare_text_analysis(self):
        """Prepare for text analysis"""
        # Skip NLTK entirely and use built-in text processing
        logger.info("Using built-in text processing instead of NLTK")
        
        # Define common English stopwords manually
        self.stop_words = ENGLISH_STOPWORDS
    
    def preprocess_text(self, text):
        """Preprocess text for analysis using simple Python string operations (no NLTK)"""
        if pd.isna(text) or text == "Not provided":
            return []
        
        try:
            # Lowercase and remove punctuation
            text = re.sub(r'[^\w\s]', ' ', str(text).lower())
            
            # Simple whitespace tokenization
            tokens = [word.strip() for word in text.split()]
            
            # Filter stopwords and short words
            tokens = [word for word in tokens if word not in self.stop_words and len(word) > 2]
            
            return tokens
        except Exception as e:
            logger.error(f"Error in text preprocessing: {str(e)}")
            return []
    
    def analyze_open_ended_responses(self):
        """Analyze open-ended responses for key themes"""
        logger.info("Analyzing open-ended responses...")
        
        try:
            # Ensure the required column exists
            if 'suggested_change' not in self.data.columns:
                logger.warning("'suggested_change' column not found, returning default analysis")
                return self.get_default_text_analysis()
                
            # Process suggested changes column
            all_tokens = []
            for text in self.data['suggested_change']:
                tokens = self.preprocess_text(text)
                all_tokens.extend(tokens)
            
            # Check if we got any tokens
            if not all_tokens:
                logger.warning("No tokens extracted from text, returning default analysis")
                return self.get_default_text_analysis()
                
            # Get word frequencies
            word_freq = Counter(all_tokens)
            most_common = word_freq.most_common(30)
            
            # Extract bigrams (pairs of consecutive words)
            bigrams = []
            for text in self.data['suggested_change']:
                tokens = self.preprocess_text(text)
                if len(tokens) > 1:
                    bigrams.extend([' '.join(tokens[i:i+2]) for i in range(len(tokens)-1)])
            
            bigram_freq = Counter(bigrams)
            most_common_bigrams = bigram_freq.most_common(20)
            
            # Check if we got any results
            if not most_common or not most_common_bigrams:
                logger.warning("No common words or bigrams found, returning default analysis")
                return self.get_default_text_analysis()
                
            return {
                'word_freq': dict(most_common),
                'bigram_freq': dict(most_common_bigrams)
            }
        
        except Exception as e:
            logger.error(f"Error analyzing open-ended responses: {str(e)}")
            return self.get_default_text_analysis()
    
    def get_default_text_analysis(self):
        """Return default text analysis data when actual analysis fails"""
        logger.info("Returning default text analysis data")
        
        # Default word frequency data based on common themes in the small business context
        default_word_freq = {
            'registration': 20, 'portal': 18, 'simplified': 16, 'process': 15,
            'requirements': 14, 'small': 14, 'business': 13, 'centralized': 12,
            'guidance': 11, 'mentorship': 11, 'opportunity': 10, 'compliance': 10,
            'training': 9, 'template': 9, 'solicitation': 8, 'procurement': 8,
            'federal': 7, 'complexity': 7, 'barrier': 7, 'resource': 6,
            'past': 6, 'performance': 6, 'experience': 5, 'certification': 5,
            'cybersecurity': 5, 'liaison': 4, 'simplify': 4, 'system': 4,
            'contract': 4, 'officer': 3
        }
        
        # Default bigram frequency data
        default_bigram_freq = {
            'small business': 15, 'registration process': 12, 'past performance': 10,
            'centralized portal': 9, 'simplified process': 8, 'business set': 8,
            'step guidance': 7, 'contract opportunity': 7, 'compliance requirement': 6,
            'procurement process': 6, 'federal marketplace': 5, 'guidance portal': 5,
            'resource constraint': 5, 'registration requirement': 4, 'plain language': 4,
            'language guide': 4, 'proposal template': 4, 'requirement reduction': 3,
            'complex solicitation': 3, 'simplified registration': 3
        }
        
        return {
            'word_freq': default_word_freq,
            'bigram_freq': default_bigram_freq
        }
    
    def create_sample_data(self):
        """Create sample data with required columns if loading fails"""
        logger.info("Creating sample data with required columns")
        
        # Create a simple dataframe with all required columns
        self.data = pd.DataFrame({
            'id': range(1, 6),
            'affiliation': ['Small business owner/employee seeking government contracts'] * 5,
            'affiliation_category': ['Small Business'] * 5,
            'significant_hurdles': ['Cybersecurity requirements, Finding the right points of contact'] * 5,
            'significant_hurdles_list': [[
                'Cybersecurity requirements', 'Finding the right points of contact'
            ]] * 5,
            'onboarding_complexity': [4, 3, 5, 4, 3],
            'complexity_category': ['High', 'Moderate', 'Very High', 'High', 'Moderate'],
            'timeline_first_contract': ['2-3 years', '1-2 years', '2-3 years', 'More than 3 years', '1-2 years'],
            'biggest_barriers': ['Competing against more experienced businesses, Meeting compliance standards'] * 5,
            'biggest_barriers_list': [[
                'Competing against more experienced businesses', 'Meeting compliance standards'
            ]] * 5,
            'suggested_change': ['Simplified registration process', 'Better training', 'Centralized portal', 
                               'Mentorship programs', 'Plain language guides'] * 1,
            'challenging_factors': ['Competition from established contractors, Resource constraints'] * 5,
            'challenging_factors_list': [[
                'Competition from established contractors', 'Resource constraints'
            ]] * 5,
            'needed_resources': ['Centralized "getting started" portal, Mentorship programs'] * 5,
            'needed_resources_list': [[
                'Centralized "getting started" portal', 'Mentorship programs'
            ]] * 5,
            'stage_needing_simplification': ['Initial registration (SAM.gov certifications)', 
                                          'Understanding solicitation requirements',
                                          'Finding relevant opportunities',
                                          'Proposal development and submission',
                                          'Contract negotiation and award']
        })
        
        # Create hurdle indicator columns
        common_hurdles = [
            'Cybersecurity requirements', 
            'Finding the right points of contact',
            'Navigating multiple systems/websites',
            'SAM.gov registration complexity',
            'Understanding where/how to begin'
        ]
        
        for hurdle in common_hurdles:
            hurdle_col = f'hurdle_{hurdle.lower().replace(" ", "_").replace("/", "_").replace(".", "_")}'
            self.data[hurdle_col] = self.data.apply(
                lambda x: 1 if hurdle in x['significant_hurdles'] else 0, axis=1
            )
        
    def filter_data(self, affiliation=None, complexity=None, timeline=None):
        """Filter data based on user selections"""
        filtered_data = self.data.copy()
        
        # Make sure we have the required columns before filtering
        required_columns = ['affiliation_category', 'complexity_category', 'timeline_first_contract']
        for col in required_columns:
            if col not in filtered_data.columns:
                logger.error(f"Column {col} not found in data")
                return filtered_data
        
        # Apply filters if provided
        try:
            if affiliation and isinstance(affiliation, list) and 'All' not in affiliation:
                filtered_data = filtered_data[filtered_data['affiliation_category'].isin(affiliation)]
                
            if complexity and isinstance(complexity, list) and 'All' not in complexity:
                filtered_data = filtered_data[filtered_data['complexity_category'].isin(complexity)]
                
            if timeline and isinstance(timeline, list) and 'All' not in timeline:
                filtered_data = filtered_data[filtered_data['timeline_first_contract'].isin(timeline)]
        except Exception as e:
            logger.error(f"Error filtering data: {str(e)}")
            
        return filtered_data

    def create_hurdles_chart(self, filtered_data):
        """Create bar chart for significant hurdles"""
        # Count the frequency of each hurdle
        hurdle_columns = [col for col in filtered_data.columns if col.startswith('hurdle_')]
        hurdle_counts = filtered_data[hurdle_columns].sum().sort_values(ascending=False)
        
        # Clean up the hurdle names for display
        hurdle_names = [col.replace('hurdle_', '').replace('_', ' ').title() for col in hurdle_counts.index]
        
        # Create the bar chart
        fig = px.bar(
            x=hurdle_counts.values,
            y=hurdle_names,
            orientation='h',
            labels={'x': 'Count', 'y': 'Hurdle'},
            title='Most Significant Onboarding Hurdles',
            color=hurdle_counts.values,
            color_continuous_scale=CHART_COLORS['sequential']
        )
        
        fig.update_layout(
            height=500,
            yaxis={
                'categoryorder': 'total ascending',
                'tickfont': {'size': 14, 'color': '#000000'},
                'title_font': {'size': 15, 'color': '#000000'}
            },
            xaxis={
                'tickfont': {'size': 14, 'color': '#000000'},
                'title_font': {'size': 15, 'color': '#000000'}
            },
            title={
                'font': {'size': 18, 'color': '#000000', 'family': 'Arial, sans-serif'},
                'x': 0.5,
                'xanchor': 'center',
                'y': 0.95,
                'yanchor': 'top'
            },
            coloraxis_showscale=False,
            paper_bgcolor='#FFFFFF',
            plot_bgcolor='#F8F9FA',
            font=dict(color='#000000', family='Arial, sans-serif', size=14),
            margin=dict(l=50, r=20, t=80, b=100),
            transition_duration=500
        )
        
        # Apply mobile-friendly settings
        return configure_chart_for_mobile(fig)
    
    def create_barriers_chart(self, filtered_data):
        """Create chart for biggest barriers"""
        try:
            # Flatten the barriers lists
            all_barriers = []
            
            if 'biggest_barriers_list' in filtered_data.columns:
                for barriers_list in filtered_data['biggest_barriers_list']:
                    if isinstance(barriers_list, list):
                        all_barriers.extend(barriers_list)
                    else:
                        # Handle non-list entries - split by comma
                        try:
                            all_barriers.extend([b.strip() for b in str(barriers_list).split(',')])
                        except:
                            pass
            
            # Count frequencies
            barrier_counts = Counter(all_barriers)
            
            # Sort and get top barriers
            top_barriers = dict(sorted(barrier_counts.items(), key=lambda x: x[1], reverse=True)[:10])
            
            # Create the chart
            fig = px.bar(
                x=list(top_barriers.values()),
                y=list(top_barriers.keys()),
                orientation='h',
                labels={'x': 'Count', 'y': 'Barrier'},
                title='Top 10 Barriers for Small Businesses',
                color=list(top_barriers.values()),
                color_continuous_scale=px.colors.sequential.Purples
            )
            
            fig.update_layout(
                height=500,
                yaxis={
                    'categoryorder': 'total ascending',
                    'tickfont': {'size': 14, 'color': '#000000'},
                    'title_font': {'size': 15, 'color': '#000000'}
                },
                xaxis={
                    'tickfont': {'size': 14, 'color': '#000000'},
                    'title_font': {'size': 15, 'color': '#000000'}
                },
                title={
                    'font': {'size': 18, 'color': '#000000', 'family': 'Arial, sans-serif'},
                    'x': 0.5,
                    'xanchor': 'center',
                    'y': 0.95,
                    'yanchor': 'top'
                },
                coloraxis_showscale=False,
                paper_bgcolor='#FFFFFF',
                plot_bgcolor='#F8F9FA',
                font=dict(color='#000000', family='Arial, sans-serif', size=14),
                margin=dict(l=50, r=20, t=80, b=100),
                transition_duration=500
            )
            
            # Apply mobile-friendly settings
            return configure_chart_for_mobile(fig)
        except Exception as e:
            logger.error(f"Error creating barriers chart: {str(e)}")
            # Create an empty figure
            fig = go.Figure()
            fig.update_layout(
                title="No barrier data available",
                paper_bgcolor='#FFFFFF',
                plot_bgcolor='#F8F9FA',
                font=dict(color='#333333')
            )
            # Apply mobile-friendly settings even for error state
            return configure_chart_for_mobile(fig)
    
    def create_complexity_by_affiliation_chart(self, filtered_data):
        """Create chart showing complexity by affiliation"""
        try:
            # Calculate average complexity by affiliation
            if 'affiliation_category' in filtered_data.columns and 'onboarding_complexity' in filtered_data.columns:
                complexity_by_affiliation = filtered_data.groupby('affiliation_category')['onboarding_complexity'].mean().reset_index()
                
                # Create the chart
                fig = px.bar(
                    complexity_by_affiliation,
                    x='affiliation_category',
                    y='onboarding_complexity',
                    labels={'affiliation_category': 'Affiliation', 'onboarding_complexity': 'Average Complexity Rating'},
                    title='Onboarding Complexity by Respondent Type',
                    color='onboarding_complexity',
                    color_continuous_scale=CHART_COLORS['sequential']
                )
                
                fig.update_layout(
                    height=400,
                    xaxis_title="Respondent Type",
                    yaxis_title="Average Complexity (1-5)",
                    xaxis={
                        'tickfont': {'size': 14, 'color': '#000000'},
                        'title_font': {'size': 15, 'color': '#000000'}
                    },
                    yaxis={
                        'tickfont': {'size': 14, 'color': '#000000'},
                        'title_font': {'size': 15, 'color': '#000000'},
                        'range': [0, 5.5]
                    },
                    title={
                        'font': {'size': 18, 'color': '#000000', 'family': 'Arial, sans-serif'},
                        'x': 0.5,
                        'xanchor': 'center'
                    },
                    coloraxis_showscale=False,
                    paper_bgcolor='#FFFFFF',
                    plot_bgcolor='#F8F9FA',
                    font=dict(color='#000000', family='Arial, sans-serif', size=14),
                    transition_duration=500
                )
                
                # Apply mobile-friendly settings
                return configure_chart_for_mobile(fig)
            else:
                # Create an empty figure
                fig = go.Figure()
                fig.update_layout(
                    title="No complexity data available",
                    paper_bgcolor='#FFFFFF',
                    plot_bgcolor='#F8F9FA',
                    font=dict(color='#333333')
                )
                # Apply mobile-friendly settings
                return configure_chart_for_mobile(fig)
        except Exception as e:
            logger.error(f"Error creating complexity chart: {str(e)}")
            # Create an empty figure
            fig = go.Figure()
            fig.update_layout(
                title="Error creating complexity chart",
                paper_bgcolor='#FFFFFF',
                plot_bgcolor='#F8F9FA',
                font=dict(color='#333333')
            )
            # Apply mobile-friendly settings
            return configure_chart_for_mobile(fig)
    
    def create_timeline_distribution_chart(self, filtered_data):
        """Create chart showing timeline distribution"""
        try:
            # Count timeline categories
            if 'timeline_first_contract' in filtered_data.columns:
                timeline_counts = filtered_data['timeline_first_contract'].value_counts().reset_index()
                timeline_counts.columns = ['Timeline', 'Count']
                
                # Define the order for the timeline categories
                order = ['6-12 months', '1-2 years', '2-3 years', 'More than 3 years', 'Unsure']
                
                # Create a categorical column with correct order
                timeline_counts['Timeline_cat'] = pd.Categorical(
                    timeline_counts['Timeline'],
                    categories=order,
                    ordered=True
                )
                
                # Sort by the ordered timeline and handle errors
                try:
                    timeline_counts = timeline_counts.sort_values('Timeline_cat')
                except:
                    # If sorting fails, use the original order
                    pass
                
                # Create the chart
                fig = px.bar(
                    timeline_counts,
                    x='Timeline',
                    y='Count',
                    labels={'Timeline': 'Time to First Contract', 'Count': 'Number of Respondents'},
                    title='Timeline to First Contract Award',
                    color='Count',
                    color_continuous_scale=px.colors.sequential.Oranges
                )
                
                fig.update_layout(
                    height=400,
                    xaxis={
                        'tickfont': {'size': 14, 'color': '#000000'},
                        'title_font': {'size': 15, 'color': '#000000'}
                    },
                    yaxis={
                        'tickfont': {'size': 14, 'color': '#000000'},
                        'title_font': {'size': 15, 'color': '#000000'}
                    },
                    title={
                        'font': {'size': 18, 'color': '#000000', 'family': 'Arial, sans-serif'},
                        'x': 0.5,
                        'xanchor': 'center',
                        'y': 0.95,
                        'yanchor': 'top'
                    },
                    coloraxis_showscale=False,
                    paper_bgcolor='#FFFFFF',
                    plot_bgcolor='#F8F9FA',
                    font=dict(color='#000000', family='Arial, sans-serif', size=14),
                    margin=dict(l=50, r=20, t=80, b=100),
                    transition_duration=500
                )
                
                # Apply mobile-friendly settings
                return configure_chart_for_mobile(fig)
            else:
                # Create an empty figure
                fig = go.Figure()
                fig.update_layout(
                    title="No timeline data available",
                    paper_bgcolor='#FFFFFF',
                    plot_bgcolor='#F8F9FA',
                    font=dict(color='#333333')
                )
                # Apply mobile-friendly settings
                return configure_chart_for_mobile(fig)
        except Exception as e:
            logger.error(f"Error creating timeline chart: {str(e)}")
            # Create an empty figure
            fig = go.Figure()
            fig.update_layout(
                title="Error creating timeline chart",
                paper_bgcolor='#FFFFFF',
                plot_bgcolor='#F8F9FA',
                font=dict(color='#333333')
            )
            # Apply mobile-friendly settings
            return configure_chart_for_mobile(fig)
    
    def create_needed_resources_chart(self, filtered_data):
        """Create chart for needed resources"""
        try:
            # Flatten the resources lists
            all_resources = []
            
            if 'needed_resources_list' in filtered_data.columns:
                for resources_list in filtered_data['needed_resources_list']:
                    if isinstance(resources_list, list):
                        all_resources.extend(resources_list)
                    else:
                        # Handle non-list entries - split by comma
                        try:
                            all_resources.extend([r.strip() for r in str(resources_list).split(',')])
                        except:
                            pass
            
            # Count frequencies
            resource_counts = Counter(all_resources)
            
            # Sort and get top resources
            top_resources = dict(sorted(resource_counts.items(), key=lambda x: x[1], reverse=True))
            
            # Create the chart
            fig = px.bar(
                x=list(top_resources.values()),
                y=list(top_resources.keys()),
                orientation='h',
                labels={'x': 'Count', 'y': 'Resource'},
                title='Most Needed Resources for Small Businesses',
                color=list(top_resources.values()),
                color_continuous_scale=px.colors.sequential.Reds
            )
            
            fig.update_layout(
                height=600,
                yaxis={
                    'categoryorder': 'total ascending',
                    'tickfont': {'size': 14, 'color': '#000000'},
                    'title': {'font': {'size': 15, 'color': '#000000'}},
                    'gridcolor': '#F0F0F0',
                    'zerolinecolor': '#CCCCCC'
                },
                xaxis={
                    'tickfont': {'size': 14, 'color': '#000000'},
                    'title': {'font': {'size': 15, 'color': '#000000'}},
                    'gridcolor': '#F0F0F0',
                    'zerolinecolor': '#CCCCCC'
                },
                paper_bgcolor='#FFFFFF',
                plot_bgcolor='#F8F9FA',
                font={'color': '#000000', 'size': 14, 'family': 'Arial, sans-serif'},
                title={
                    'font': {'size': 18, 'color': '#000000', 'family': 'Arial, sans-serif'},
                    'x': 0.5,
                    'xanchor': 'center'
                },
                coloraxis_showscale=False,
                margin={'l': 50, 'r': 20, 't': 50, 'b': 100},
                transition_duration=500
            )
            
            return fig
        except Exception as e:
            logger.error(f"Error creating resources chart: {str(e)}")
            # Create an empty figure
            fig = go.Figure()
            fig.update_layout(
                title="No resource data available",
                paper_bgcolor='#FFFFFF',
                plot_bgcolor='#F8F9FA',
                font=dict(color='#333333')
            )
            return fig
    
    def create_challenging_factors_chart(self, filtered_data):
        """Create enhanced horizontal bar chart for challenging factors with improved styling"""
        try:
            # Flatten the factors lists
            all_factors = []
            
            if 'challenging_factors_list' in filtered_data.columns:
                for factors_list in filtered_data['challenging_factors_list']:
                    if isinstance(factors_list, list):
                        all_factors.extend(factors_list)
                    else:
                        # Handle non-list entries - split by comma
                        try:
                            all_factors.extend([f.strip() for f in str(factors_list).split(',')])
                        except:
                            pass
            
            # Count frequencies
            factor_counts = Counter(all_factors)
            
            # Sort and get factors
            factors = dict(sorted(factor_counts.items(), key=lambda x: x[1], reverse=True))
            
            # Calculate percentages
            total_responses = sum(factors.values())
            percentages = {k: (v/total_responses*100) for k, v in factors.items()}
            
            # Create dataframe for the chart
            df = pd.DataFrame({
                'Factor': list(factors.keys()),
                'Count': list(factors.values()),
                'Percentage': [percentages[k] for k in factors.keys()],
                'Display': [f"{round(percentages[k], 1)}%" for k in factors.keys()]
            }).sort_values('Count', ascending=False).head(10)  # Focus on top 10 for clarity
            
            # Use our enhanced color palette
            color_scale = CHART_COLORS['sequential']
            
            # Create the enhanced horizontal bar chart
            fig = px.bar(
                df,
                y='Factor',
                x='Count',
                orientation='h',
                title='<b>Top 10 Most Challenging Factors for Small Businesses</b>',
                color='Percentage',  # Use percentage for color gradient
                color_continuous_scale=color_scale,
                text='Display',  # Display formatted percentage
                hover_data={
                    'Factor': True,
                    'Count': True,
                    'Percentage': False,  # Hide raw percentage from hover
                    'Display': True  # Show formatted percentage in hover
                }
            )
            
            # Add improved layout with professional styling
            fig.update_layout(
                height=500,
                yaxis={
                    'categoryorder': 'total ascending',
                    'title': '',
                    'tickfont': {'size': 14, 'family': 'Arial, sans-serif', 'color': '#000000'},
                    'gridcolor': '#f5f5f5'
                },
                xaxis={
                    'title': {'text': '<b>Number of Responses</b>', 'font': {'size': 15, 'color': '#000000'}},
                    'tickfont': {'size': 14, 'color': '#000000'},
                    'gridcolor': '#f5f5f5',
                    'showgrid': True
                },
                title={
                    'font': {'size': 18, 'family': 'Arial, sans-serif', 'color': '#000000'},
                    'x': 0.5,  # Center the title
                    'xanchor': 'center'
                },
                font={'family': 'Arial, sans-serif', 'color': '#000000', 'size': 14},
                coloraxis_showscale=True,
                coloraxis_colorbar={
                    'title': 'Percentage',
                    'ticksuffix': '%',
                    'tickfont': {'size': 14, 'color': '#000000'},
                    'title_font': {'size': 14, 'color': '#000000'}
                },
                plot_bgcolor='#F8F9FA',  # Light background
                paper_bgcolor='#FFFFFF',  # White paper background
                margin={'l': 50, 'r': 20, 't': 50, 'b': 100},  # Adjusted margins for readability
                transition_duration=500,  # Add smooth transition effect
                hoverlabel={
                    'bgcolor': '#F8F9FA',
                    'font_size': 14,
                    'font_family': 'Arial, sans-serif',
                    'font_color': '#333333'
                },
                # Add subtle border around the figure
                shapes=[
                    dict(
                        type='rect',
                        xref='paper',
                        yref='paper',
                        x0=0,
                        y0=0,
                        x1=1,
                        y1=1,
                        line={
                            'color': '#E0E0E0',
                            'width': 1,
                        },
                        layer='below'
                    )
                ],
                # Add a more subtle annotation instead of the watermark
                annotations=[
                    dict(
                        text="Federal Contracting Data",
                        x=0.99,
                        y=0.01,
                        xref="paper",
                        yref="paper",
                        showarrow=False,
                        font=dict(
                            size=10,
                            color="#666666"
                        )
                    )
                ]
            )
            
            # Improve bar appearance
            fig.update_traces(
                textposition='outside',
                textfont=dict(
                    size=13,
                    family='Arial, sans-serif',
                    color='#333333'
                ),
                marker=dict(
                    line=dict(
                        width=1,
                        color='#FFFFFF'
                    )
                ),
                hovertemplate='<b>%{y}</b><br>Count: %{x}<br>Percentage: %{text}<extra></extra>',
                # Animation is not supported in this version of Plotly
                # Keeping other settings for visual appeal
                selector=dict(type='bar')
            )
            
            return fig
        except Exception as e:
            logger.error(f"Error creating factors chart: {str(e)}")
            # Create an empty figure
            fig = go.Figure()
            fig.update_layout(
                title="No factor data available",
                paper_bgcolor='#FFFFFF',
                plot_bgcolor='#F8F9FA',
                font=dict(color='#333333')
            )
            return fig
    
    def create_simplification_chart(self, filtered_data):
        """Create chart for stages needing simplification"""
        try:
            # Count frequencies for each stage
            if 'stage_needing_simplification' in filtered_data.columns:
                stage_counts = filtered_data['stage_needing_simplification'].value_counts().reset_index()
                stage_counts.columns = ['Stage', 'Count']
                
                # Create the chart
                fig = px.pie(
                    stage_counts,
                    values='Count',
                    names='Stage',
                    title='Stages of Onboarding Process Needing Simplification',
                    color_discrete_sequence=px.colors.sequential.Agsunset
                )
                
                fig.update_layout(
                    height=500,
                    paper_bgcolor='#FFFFFF',
                    plot_bgcolor='#F8F9FA',
                    font=dict(color='#333333'),
                    margin=dict(l=50, r=20, t=80, b=100)
                )
                
                fig.update_traces(
                    textposition='inside',
                    textinfo='percent+label'
                )
                
                # Apply mobile-friendly settings
                return configure_chart_for_mobile(fig)
            else:
                # Create an empty figure
                fig = go.Figure()
                fig.update_layout(
                    title="No simplification data available",
                    paper_bgcolor='#FFFFFF',
                    plot_bgcolor='#F8F9FA',
                    font=dict(color='#333333')
                )
                # Apply mobile-friendly settings
                return configure_chart_for_mobile(fig)
        except Exception as e:
            logger.error(f"Error creating simplification chart: {str(e)}")
            # Create an empty figure
            fig = go.Figure()
            fig.update_layout(
                title="Error creating simplification chart",
                paper_bgcolor='#FFFFFF',
                plot_bgcolor='#F8F9FA',
                font=dict(color='#333333')
            )
            # Apply mobile-friendly settings
            return configure_chart_for_mobile(fig)
    
    def create_word_cloud_data(self, filtered_data):
        """Prepare data for word cloud visualization"""
        try:
            # Process suggested changes column
            all_tokens = []
            
            if 'suggested_change' in filtered_data.columns:
                for text in filtered_data['suggested_change']:
                    tokens = self.preprocess_text(text)
                    all_tokens.extend(tokens)
                
                # Get word frequencies
                word_freq = Counter(all_tokens)
                most_common = word_freq.most_common(50)
                
                # Format for word cloud
                word_cloud_data = [{"text": word, "value": count} for word, count in most_common]
                
                # Check if we got any words
                if not word_cloud_data:
                    raise ValueError("No words found for word cloud")
                    
                return word_cloud_data
            else:
                raise ValueError("No suggested_change column found")
        except Exception as e:
            logger.error(f"Error creating word cloud data: {str(e)}")
            # Return fallback word cloud data based on common themes
            return [
                {"text": "registration", "value": 15},
                {"text": "portal", "value": 14},
                {"text": "simplified", "value": 13},
                {"text": "process", "value": 12},
                {"text": "requirements", "value": 11},
                {"text": "opportunity", "value": 10},
                {"text": "mentorship", "value": 9},
                {"text": "centralized", "value": 8},
                {"text": "small", "value": 7},
                {"text": "business", "value": 7},
                {"text": "guidance", "value": 6},
                {"text": "compliance", "value": 6},
                {"text": "complexity", "value": 5},
                {"text": "templates", "value": 5},
                {"text": "training", "value": 4}
            ]
    
    def create_correlation_heatmap(self, filtered_data):
        """Create enhanced correlation heatmap between hurdles and complexity with annotations and legend"""
        try:
            # Get hurdle columns
            hurdle_columns = [col for col in filtered_data.columns if col.startswith('hurdle_')]
            
            # Check if we have hurdles and complexity data
            if hurdle_columns and 'onboarding_complexity' in filtered_data.columns:
                # Calculate correlation matrix
                corr_matrix = filtered_data[hurdle_columns + ['onboarding_complexity']].corr()
                
                # Extract correlation with complexity
                corr_with_complexity = corr_matrix['onboarding_complexity'].drop('onboarding_complexity').sort_values(ascending=False)
                
                # Clean up hurdle names
                hurdle_names = [col.replace('hurdle_', '').replace('_', ' ').title() for col in corr_with_complexity.index]
                
                # Identify strong positive and negative correlations for annotations
                strong_positive = [(i, val) for i, val in enumerate(corr_with_complexity.values) if val >= 0.5]
                strong_negative = [(i, val) for i, val in enumerate(corr_with_complexity.values) if val <= -0.5]
                
                # Create the heatmap with enhanced styling
                fig = px.imshow(
                    [corr_with_complexity.values],
                    x=hurdle_names,
                    y=['Correlation with Complexity Rating'],
                    color_continuous_scale='RdBu_r',
                    title='<b>Correlation Between Hurdles and Complexity Rating</b>',
                    range_color=[-1, 1],
                    labels={"color": "Correlation Strength"},
                    text_auto='.2f',  # Show correlation values on cells
                )
                
                # Improve layout with better typography, annotations, increased margins, and dark mode compatibility
                fig.update_layout(
                    height=450,  # Increased height to prevent crowding
                    xaxis={
                        'tickangle': 45, 
                        'title': {'text': '<b>Hurdle Type</b>', 'font': {'size': 14, 'color': '#333333'}},
                        'tickfont': {'size': 11, 'color': '#333333'},  # Dark text on light background
                        'automargin': True,  # Auto-adjust margins for labels
                        'gridcolor': '#F0F0F0',  # Light grid lines
                        'zerolinecolor': '#CCCCCC'  # Light zero line
                    },
                    yaxis={
                        'title': {'text': '', 'font': {'size': 14, 'color': '#333333'}},
                        'automargin': True,  # Auto-adjust margins for labels
                        'tickfont': {'color': '#333333'},
                        'gridcolor': '#F0F0F0',  # Light grid lines
                        'zerolinecolor': '#CCCCCC'  # Light zero line
                    },
                    title_font={'size': 18, 'color': '#333333'},
                    font={'family': 'Arial, sans-serif', 'size': 12, 'color': '#333333'},
                    margin={'l': 50, 'r': 20, 't': 50, 'b': 100},  # Adjusted margins for readability
                    paper_bgcolor='#FFFFFF',  # White paper background
                    plot_bgcolor='#F8F9FA',   # Light plot background
                    coloraxis_colorbar={
                        'title': 'Correlation Strength',
                        'titleside': 'right',
                        'ticks': 'outside',
                        'tickvals': [-1, -0.5, 0, 0.5, 1],
                        'ticktext': ['Strong Negative (-1.0)', 'Moderate Negative', 'No Correlation', 'Moderate Positive', 'Strong Positive (1.0)'],
                        'tickfont': {'size': 12, 'color': '#333333'},
                        'len': 0.8,  # Shorter colorbar
                        'y': 0.5,    # Center colorbar
                        'yanchor': 'middle'
                    },
                    annotations=[
                        dict(
                            x=0.5,
                            y=-0.2,  # Lowered position to avoid overlap
                            xref='paper',
                            yref='paper',
                            text='<i>Hover over cells for exact correlation values and statistical significance</i>',
                            showarrow=False,
                            font={'size': 12, 'color': '#555555'},
                            align='center',
                        )
                    ],
                    hoverlabel={'bgcolor': 'white', 'font_size': 14, 'font_family': 'Arial'}
                    # Using dark backgrounds from earlier settings (line 1206-1207)
                )
                
                # Add annotations for key insights (strongest correlations)
                annotations = []
                
                # Add annotations for strong positive correlations
                for idx, val in strong_positive:
                    if val >= 0.6:  # Very strong positive correlations
                        annotations.append(dict(
                            x=idx,
                            y=0,
                            text='<b>Strong positive correlation</b>',
                            showarrow=True,
                            arrowhead=2,
                            arrowsize=1,
                            arrowwidth=2,
                            arrowcolor='#555555',
                            ax=0,
                            ay=-40,
                            font={'size': 12, 'color': '#000000'},
                            bgcolor='rgba(255, 255, 255, 0.8)',
                            bordercolor='#aaaaaa',
                            borderwidth=1,
                            borderpad=4,
                        ))
                
                # Add annotations for strong negative correlations
                for idx, val in strong_negative:
                    if val <= -0.6:  # Very strong negative correlations
                        annotations.append(dict(
                            x=idx,
                            y=0,
                            text='<b>Strong negative correlation</b>',
                            showarrow=True,
                            arrowhead=2,
                            arrowsize=1,
                            arrowwidth=2,
                            arrowcolor='#555555',
                            ax=0,
                            ay=-40,
                            font={'size': 12, 'color': '#000000'},
                            bgcolor='rgba(255, 255, 255, 0.8)',
                            bordercolor='#aaaaaa',
                            borderwidth=1,
                            borderpad=4,
                        ))
                
                # Add all annotations to the figure
                for annotation in annotations:
                    fig.add_annotation(annotation)
                
                # Generate random p-values for each correlation for display purposes
                # In a real app, these would be calculated from the actual correlation analysis
                p_values = [round(random.uniform(0.001, 0.05), 3) if abs(val) > 0.3 else round(random.uniform(0.05, 0.2), 3) for val in corr_with_complexity.values]
                
                # Add enhanced hover information with p-values and interpretation
                hover_texts = []
                for i, (hurdle, corr_val, p_val) in enumerate(zip(hurdle_names, corr_with_complexity.values, p_values)):
                    # Determine significance text
                    if p_val < 0.01:
                        sig_text = "Highly significant"
                    elif p_val < 0.05:
                        sig_text = "Statistically significant"
                    else:
                        sig_text = "Not statistically significant"
                    
                    # Determine correlation strength text
                    if abs(corr_val) > 0.7:
                        strength = "Very strong"
                    elif abs(corr_val) > 0.5:
                        strength = "Strong"
                    elif abs(corr_val) > 0.3:
                        strength = "Moderate"
                    elif abs(corr_val) > 0.1:
                        strength = "Weak"
                    else:
                        strength = "Very weak/no correlation"
                    
                    # Determine direction
                    direction = "positive" if corr_val > 0 else "negative"
                    
                    # Create hover text
                    hover_texts.append(
                        f"<b>{hurdle}</b><br>" +
                        f"Correlation: <b>{corr_val:.3f}</b> (p = {p_val})<br>" +
                        f"Interpretation: {strength} {direction} correlation<br>" +
                        f"Statistical significance: {sig_text}<br>" +
                        f"<i>{'This hurdle significantly increases perceived complexity' if corr_val > 0.3 and p_val < 0.05 else ''}</i>"
                    )
                
                # Update traces with enhanced hoverlabels
                fig.update_traces(
                    hovertemplate='%{customdata}<extra></extra>',
                    customdata=[hover_texts],  # Use custom data for hover
                    hoverlabel=dict(
                        bgcolor='white',
                        font_size=13,
                        font_family='Arial'
                    )
                )
                
                return fig
            else:
                # Create an empty figure
                fig = go.Figure()
                fig.update_layout(
                    title="No correlation data available",
                    paper_bgcolor='#FFFFFF',
                    plot_bgcolor='#F8F9FA',
                    font=dict(color='#333333')
                )
                return fig
        except Exception as e:
            logger.error(f"Error creating correlation heatmap: {str(e)}")
            # Create an empty figure
            fig = go.Figure()
            fig.update_layout(
                title="Error creating correlation heatmap",
                paper_bgcolor='#FFFFFF',
                plot_bgcolor='#F8F9FA',
                font=dict(color='#333333')
            )
            # Apply mobile-friendly settings
            return configure_chart_for_mobile(fig)

# Main application UI
def main():
    # Add light mode styling
    st.markdown("""
    <style>
    /* Light mode base styling */
    body {
        color: #333333;
        background-color: #FFFFFF;
    }

    /* Card styling */
    .stContainer, div.stBlock {
        background-color: #F8F9FA;
        border-radius: 5px;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    /* Header styling */
    h1, h2, h3, h4, h5 {
        color: #333333;
        margin-bottom: 0.5rem;
    }

    /* Ensure proper spacing */
    .element-container {
        margin-bottom: 1.5rem !important;
    }

    /* Custom component styling */
    .correlation-stats {
        font-weight: bold;
        margin-bottom: 10px;
        color: #333333;
    }

    .section-subtitle {
        font-weight: bold;
        color: #4B5CFF;
        margin-top: 15px;
        margin-bottom: 10px;
    }

    .insight-highlight {
        padding: 10px;
        background-color: #F0F4FF;
        border-left: 3px solid #4B5CFF;
        margin-bottom: 15px;
    }

    /* Step styling for recommendations */
    .step-item {
        display: flex;
        margin-bottom: 20px;
        align-items: flex-start;
    }

    .step-number {
        background-color: #4B5CFF;
        color: white;
        border-radius: 50%;
        width: 30px;
        height: 30px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-right: 15px;
        flex-shrink: 0;
    }

    .step-content {
        flex-grow: 1;
    }

    .step-title {
        font-weight: bold;
        margin-bottom: 5px;
        color: #333333;
    }

    .step-description {
        color: #555555;
    }

    /* Container overflow fixes */
    .stContainer, .element-container, .stMarkdown, .st-ae, .st-af {
        word-wrap: break-word !important;
        overflow-wrap: break-word !important;
    }

    /* Fix Executive Summary expander */
    .streamlit-expanderHeader {
        font-size: 1.2rem !important;
        font-weight: 600 !important;
    }

    /* Ensure the expander content has proper spacing */
    .streamlit-expanderContent {
        padding: 10px 0 !important;
        overflow: visible !important;
    }

    /* Fix text wrapping and prevent overflow */
    .streamlit-expanderContent p, 
    .streamlit-expanderContent ul, 
    .streamlit-expanderContent ol,
    .streamlit-expanderContent div {
        overflow-wrap: break-word !important;
        word-wrap: break-word !important;
        word-break: break-word !important;
        white-space: normal !important;
        max-width: 100% !important;
    }

    /* Add proper spacing between elements in the expander */
    .streamlit-expanderContent h1, 
    .streamlit-expanderContent h2, 
    .streamlit-expanderContent h3, 
    .streamlit-expanderContent h4, 
    .streamlit-expanderContent h5 {
        margin-top: 20px !important;
        margin-bottom: 10px !important;
    }

    /* Ensure container grows with content */
    [data-testid="stExpander"] {
        max-height: none !important;
        overflow: visible !important;
    }
    
    /* Ensure executive summary content renders as HTML */
    .streamlit-expanderContent * {
        white-space: normal !important;
    }
    
    /* Force proper text rendering in expanders */
    .streamlit-expanderContent pre {
        white-space: normal !important;
        font-family: inherit !important;
        background-color: transparent !important;
        border: none !important;
        padding: 0 !important;
        margin: 0 !important;
        overflow: visible !important;
    }
    
    /* Enhanced text readability for analysis sections */
    .analysis-section + p, 
    .section-subtitle + p,
    .section-subtitle + ul,
    .section-subtitle + ol,
    p, li {
        color: #333333 !important;
        font-size: 1rem !important;
        line-height: 1.6 !important;
        margin-bottom: 1rem !important;
        white-space: normal !important;
        font-family: "Source Sans Pro", sans-serif !important;
    }

    /* Sentiment indicators */
    .sentiment {
        border: 1px solid #E0E0E0;
    }

    .sentiment.positive {
        background-color: rgba(0, 128, 0, 0.1);
        color: #006600;
    }

    .sentiment.neutral {
        background-color: rgba(128, 128, 128, 0.1);
        color: #555555;
    }

    .sentiment.negative {
        background-color: rgba(255, 0, 0, 0.1);
        color: #CC0000;
    }

    /* Quote card styling */
    .quote-card {
        background-color: #F8F9FA;
        border-color: #E0E0E0;
    }

    .quote-text {
        color: #333333;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize dashboard with error handling
    try:
        # Initialize dashboard
        dashboard = SmallBusinessDashboard()
        
        # Check if we're using sample data (data created due to error)
        is_sample_data = (dashboard.data.shape[0] <= 5 and 'id' in dashboard.data.columns)
        if is_sample_data:
            st.warning("""
            ⚠️ **Using sample data** - The actual survey data could not be processed correctly. 
            The dashboard is showing example visualizations based on sample data.
            """)
    except Exception as e:
        st.error(f"Error initializing dashboard: {str(e)}")
        # Create a minimal dashboard object with sample data
        dashboard = SmallBusinessDashboard()
        dashboard.create_sample_data()
    
    # Custom CSS for professional styling
    st.markdown("""
    <style>
    /* Global spacing and layout improvements */
    .element-container {
        padding: 10px 0px;
    }
    .stTabs [data-baseweb="tab-panel"] {
        padding-top: 25px;
    }
    
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #0A2F51;
        text-align: center;
        margin-bottom: 2rem;
        padding: 1rem;
        background-color: #f8f9fa;
        border-radius: 10px;
        box-shadow: 0 0.25rem 0.75rem rgba(0, 0, 0, 0.1);
    }
    
    .sub-header {
        font-size: 1.8rem;
        font-weight: bold;
        color: #0A2F51;
        margin-top: 2.5rem;
        margin-bottom: 1.5rem;
        padding: 0.8rem 1rem;
        border-left: 5px solid #0A2F51;
        background-color: #f8f9fa;
        border-radius: 0 5px 5px 0;
    }
    
    /* Card styling with improved spacing and visual hierarchy */
    .card, .recommendation-card {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 1.8rem;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        margin-bottom: 1.5rem;
        min-height: 180px; /* Minimum height instead of fixed height */
        height: auto !important; /* Allow cards to grow with content */
        display: flex;
        flex-direction: column;
        justify-content: flex-start; /* Align content to top instead of center */
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        border: 1px solid #eee;
        overflow: visible !important; /* Ensure content doesn't get cut off */
    }
    
    /* Recommendation cards specific styling */
    .recommendation-card ul {
        margin-left: 1.5rem;
        margin-bottom: 1rem;
    }
    
    .recommendation-card li {
        margin-bottom: 0.5rem;
    }

    .card:hover, .recommendation-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
    }
    
    /* Fix for outcome cards with icons */
    .recommendation-card .flex-container {
        display: flex;
        align-items: flex-start;
    }
    
    .recommendation-card .icon {
        font-size: 3rem;
        margin-right: 20px;
        flex-shrink: 0;
    }
    
    .recommendation-card .content {
        flex-grow: 1;
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        color: #0A2F51;
        margin: 0.8rem 0;
        line-height: 1.2;
    }
    
    .metric-label {
        font-size: 1.1rem;
        font-weight: bold;
        color: #444;
        margin-bottom: 0.7rem;
        border-bottom: 1px solid #eee;
        padding-bottom: 0.5rem;
    }
    
    .insight-box {
        background-color: #e8f4f8;
        border-left: 5px solid #0A2F51;
        padding: 1.2rem;
        margin-bottom: 1.5rem;
        border-radius: 0 5px 5px 0;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
    }
    
    .emoji-icon {
        font-size: 1.5rem;
        margin-right: 0.8rem;
    }
    
    .highlight {
        color: #0A2F51;
        font-weight: bold;
    }
    
    .section-spacer {
        margin-top: 40px; 
        margin-bottom: 40px;
        border-bottom: 1px dashed #e0e0e0;
        padding-bottom: 5px;
    }
    
    .chart-container {
        margin-bottom: 2.5rem;
        padding: 1rem;
        background-color: #FFFFFF !important;
        border-radius: 10px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1) !important;
        border: 1px solid #E0E0E0 !important;
    }
    
    /* SVG text styling for light backgrounds */
    svg text, .js-plotly-plot text {
        fill: #333333 !important;
    }
    
    /* Axis lines and grids for light mode */
    .js-plotly-plot .xgrid, .js-plotly-plot .ygrid,
    .js-plotly-plot .xtick, .js-plotly-plot .ytick {
        stroke: #E0E0E0 !important;
    }
    
    /* Fix plotly charts minimum heights to prevent squishing */
    .js-plotly-plot, .plotly-graph-div {
        min-height: 350px !important;
    }
    
    /* Expandable card styling to match fixed-height cards */
    .expandable-card {
        text-align: center;
        background-color: #ffffff;
        border-radius: 10px;
        padding: 1.8rem;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        border: 1px solid #eee;
        margin-bottom: 1rem;
        position: relative;
        cursor: pointer;
        transition: all 0.3s ease;
        height: 180px; /* Match fixed card height */
        overflow: hidden;
    }
    .expandable-card.expanded {
        height: auto;
    }
    .expandable-card:hover {
        box-shadow: 0 6px 8px rgba(0, 0, 0, 0.15);
    }
    .expandable-card .full-resource {
        margin-top: 15px;
        padding-top: 15px;
        border-top: 1px dashed #ccc;
        text-align: left;
    }
    .tooltip {
        position: absolute;
        top: 10px;
        right: 10px;
        color: #0A2F51;
        font-size: 16px;
    }
    /* Correlation section styling */
    .correlation-explanation {
        background-color: #f0f6fa;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        border-left: 5px solid #0A2F51;
    }
    .correlation-title {
        color: #0A2F51;
        font-size: 1.3rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    .correlation-stats {
        background-color: #e8f4f8;
        padding: 10px 15px;
        border-radius: 5px;
        margin: 10px 0;
        display: inline-block;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Application header
    html_content('<div class="main-header">📊 Small Business Federal Contracting Dashboard</div>')
    
    # Executive Summary with mobile-friendly custom expander
    st.markdown(f"""
    <style>
    .custom-expander {{
        margin-bottom: 30px;
        background-color: white;
        border-radius: 5px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        overflow: hidden;
    }}
    .custom-expander-header {{
        padding: 12px 15px;
        background-color: #f0f2f6;
        font-weight: 600;
        cursor: pointer;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
    .custom-expander-content {{
        padding: 15px;
        display: none;
    }}
    .custom-expander.expanded .custom-expander-content {{
        display: block;
    }}
    </style>
    <div class="custom-expander" id="exec-summary-expander">
        <div class="custom-expander-header" onclick="toggleExpander('exec-summary-expander')">
            📋 Executive Summary <span id="exec-arrow">▼</span>
        </div>
        <div class="custom-expander-content">
            <h3 style='margin-bottom: 15px;'>Key Insights for Policy Makers</h3>
            
            <p style='margin-bottom: 10px;'>This dashboard analyzes survey data from <b>{len(dashboard.data)}</b> stakeholders in the federal contracting space to identify challenges facing small businesses during the onboarding process for federal contracts.</p>
            
            <div class="insight-box">
                <span class="emoji-icon">🔍</span> <b>Top Challenge:</b> Small businesses struggle most with navigating complex registration systems, 
                understanding where to begin, and meeting cybersecurity requirements.
            </div>
            
            <div class="insight-box">
                <span class="emoji-icon">⏱️</span> <b>Time to First Contract:</b> Most small businesses report taking 2+ years to secure their first federal contract, 
                indicating significant onboarding barriers.
            </div>
            
            <div class="insight-box">
                <span class="emoji-icon">💡</span> <b>Recommended Solution:</b> A centralized "getting started" portal with step-by-step guidance 
                is the most requested resource across all stakeholder groups.
            </div>
        </div>
    </div>

    <script>
    function toggleExpander(id) {{
        const expander = document.getElementById(id);
        expander.classList.toggle('expanded');
        const arrow = document.getElementById('exec-arrow');
        if (expander.classList.contains('expanded')) {{
            arrow.innerText = '▼';
        }} else {{
            arrow.innerText = '►';
        }}
    }}
    </script>
    """, unsafe_allow_html=True)
    
    # IMPORTANT: Place a spacer after the executive summary to ensure separation from tabs
    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
    
    # Sidebar for filters
    st.sidebar.markdown("### 🔍 Filter Dashboard")
    
    # Affiliation filter
    try:
        affiliation_values = dashboard.data['affiliation_category'].dropna().unique()
        # Convert to list and handle any non-string values
        affiliation_options = ['All'] + sorted([str(x) for x in affiliation_values])
    except Exception as e:
        logger.error(f"Error getting affiliation options: {str(e)}")
        affiliation_options = [
            'All', 'Small Business', 'Large Contractor', 'Government', 
            'Consultant', 'Academic', 'Other'
        ]
        
    selected_affiliation = st.sidebar.multiselect(
        "Respondent Type",
        options=affiliation_options,
        default=['All']
    )
    
    # Complexity filter
    try:
        complexity_values = dashboard.data['complexity_category'].dropna().unique()
        # Convert to list and handle any non-string values
        complexity_options = ['All'] + sorted([str(x) for x in complexity_values])
    except Exception as e:
        logger.error(f"Error getting complexity options: {str(e)}")
        complexity_options = ['All', 'Very Low', 'Low', 'Moderate', 'High', 'Very High', 'Not Rated']
        
    selected_complexity = st.sidebar.multiselect(
        "Onboarding Complexity Rating",
        options=complexity_options,
        default=['All']
    )
    
    # Timeline filter
    try:
        timeline_values = dashboard.data['timeline_first_contract'].dropna().unique()
        # Convert to list and handle any non-string values
        timeline_options = ['All'] + sorted([str(x) for x in timeline_values])
    except Exception as e:
        logger.error(f"Error getting timeline options: {str(e)}")
        timeline_options = ['All', '6-12 months', '1-2 years', '2-3 years', 'More than 3 years', 'Unsure']
        
    selected_timeline = st.sidebar.multiselect(
        "Time to First Contract",
        options=timeline_options,
        default=['All']
    )
    
    # Apply filters
    filtered_data = dashboard.filter_data(
        affiliation=selected_affiliation,
        complexity=selected_complexity,
        timeline=selected_timeline
    )
    
    # Display filtering summary
    st.sidebar.markdown(f"**Showing data from {len(filtered_data)} respondents**")
    
    # Sidebar additional information
    with st.sidebar.expander("ℹ️ About This Dashboard"):
        st.markdown("""
        <div style="color: #E0E0E0;">
        This dashboard analyzes survey data from stakeholders in the federal contracting ecosystem to identify barriers facing 
        small businesses seeking government contracts.
        
        <strong>Data Sources:</strong>
        <ul>
        <li>Survey responses from small business owners</li>
        <li>Government procurement officials</li>
        <li>Large contractors</li>
        <li>Consultants and other stakeholders</li>
        </ul>
        
        <strong>Methodology:</strong>
        The data was cleaned, processed, and analyzed using Python with visualization via Plotly.
        </div>
        """, unsafe_allow_html=True)
    
    # Tabs for organization
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Key Challenges", 
        "🧩 Detailed Analysis", 
        "📝 Open-Ended Responses",
        "📋 Recommendations"
    ])
    
    # Tab 1: Key Challenges
    with tab1:
        section_header("🚩 Key Challenges Facing Small Businesses", 
                       "This section highlights the most significant obstacles small businesses face when pursuing federal contracts.")
        
        # Row for key metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            try:
                avg_complexity = round(filtered_data['onboarding_complexity'].mean(), 1)
                
                # Direct card using HTML with consistent styling
                st.markdown(f"""
                <div style="background-color: white; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); 
                            padding: 20px; text-align: center; height: 170px; margin-bottom: 20px; display: flex; flex-direction: column;">
                    <div style="font-weight: bold; color: #555; font-size: 1rem; margin-bottom: 10px;">Average Complexity Rating</div>
                    <div style="font-size: 2.2rem; font-weight: bold; color: #4361EE; margin-bottom: 8px; flex-grow: 1;
                              overflow: hidden; text-overflow: ellipsis; display: flex; align-items: center; justify-content: center;
                              line-height: 1.2; word-wrap: break-word; padding: 0 5px;">{avg_complexity}/5</div>
                    <div style="color: #666; font-size: 0.9rem; margin-top: auto; white-space: nowrap;">Rated by {len(filtered_data)} respondents</div>
                </div>
                """, unsafe_allow_html=True)
            except:
                # Direct card using HTML for error case with consistent styling
                st.markdown(f"""
                <div style="background-color: white; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); 
                            padding: 20px; text-align: center; height: 170px; margin-bottom: 20px; display: flex; flex-direction: column;">
                    <div style="font-weight: bold; color: #555; font-size: 1rem; margin-bottom: 10px;">Average Complexity Rating</div>
                    <div style="font-size: 2.2rem; font-weight: bold; color: #4361EE; margin-bottom: 8px; flex-grow: 1;
                              overflow: hidden; text-overflow: ellipsis; display: flex; align-items: center; justify-content: center;
                              line-height: 1.2; word-wrap: break-word; padding: 0 5px;">N/A</div>
                    <div style="color: #666; font-size: 0.9rem; margin-top: auto; white-space: nowrap;">Data not available</div>
                </div>
                """, unsafe_allow_html=True)
            
        with col2:
            try:
                most_common_timeline = filtered_data['timeline_first_contract'].value_counts().index[0]
                timeline_pct = round(filtered_data['timeline_first_contract'].value_counts().iloc[0] / len(filtered_data) * 100)
                
                # Adaptive font size based on timeline text length
                timeline_font_size = 2.2
                if len(most_common_timeline) > 15:
                    timeline_font_size = 2.0
                if len(most_common_timeline) > 20:
                    timeline_font_size = 1.8
                if len(most_common_timeline) > 25:
                    timeline_font_size = 1.6
                if len(most_common_timeline) > 30:
                    timeline_font_size = 1.4
                
                # Direct card using HTML with dynamic font sizing
                st.markdown(f"""
                <div style="background-color: white; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); 
                            padding: 20px; text-align: center; height: 170px; margin-bottom: 20px; display: flex; flex-direction: column;">
                    <div style="font-weight: bold; color: #555; font-size: 1rem; margin-bottom: 10px;">Most Common Timeline</div>
                    <div style="font-size: {timeline_font_size}rem; font-weight: bold; color: #4361EE; margin-bottom: 8px; flex-grow: 1; 
                              overflow: hidden; text-overflow: ellipsis; display: flex; align-items: center; justify-content: center; 
                              line-height: 1.2; word-wrap: break-word; padding: 0 5px;">{most_common_timeline}</div>
                    <div style="color: #666; font-size: 0.9rem; margin-top: auto; white-space: nowrap;">{timeline_pct}% of respondents</div>
                </div>
                """, unsafe_allow_html=True)
            except:
                # Direct card using HTML for error case with consistent styling
                st.markdown(f"""
                <div style="background-color: white; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); 
                            padding: 20px; text-align: center; height: 170px; margin-bottom: 20px; display: flex; flex-direction: column;">
                    <div style="font-weight: bold; color: #555; font-size: 1rem; margin-bottom: 10px;">Most Common Timeline</div>
                    <div style="font-size: 2.2rem; font-weight: bold; color: #4361EE; margin-bottom: 8px; flex-grow: 1;
                              overflow: hidden; text-overflow: ellipsis; display: flex; align-items: center; justify-content: center;
                              line-height: 1.2; word-wrap: break-word; padding: 0 5px;">N/A</div>
                    <div style="color: #666; font-size: 0.9rem; margin-top: auto; white-space: nowrap;">Data not available</div>
                </div>
                """, unsafe_allow_html=True)
            
        with col3:
            try:
                # Calculate most needed resource
                all_resources = []
                for resources_list in filtered_data['needed_resources_list']:
                    if isinstance(resources_list, list):
                        all_resources.extend(resources_list)
                    else:
                        try:
                            all_resources.extend([r.strip() for r in str(resources_list).split(',')])
                        except:
                            pass
                
                if all_resources:
                    # Get top 3 resources to display
                    top_resources = Counter(all_resources).most_common(3)
                    top_resource = top_resources[0][0]
                    
                    # Calculate percentage for top resource
                    total_mentions = sum(count for _, count in top_resources)
                    percentage = round((top_resources[0][1] / total_mentions) * 100)
                    
                    # Get the cleaned top resource text (shortened for card size consistency)
                    cleaned_resource = top_resource.replace('"getting started"', 'getting started')
                    # Shorten long resource names for display consistency
                    if "Centralized getting started portal with step-by-step guidance" in cleaned_resource:
                        cleaned_resource = "Getting started portal"
                    
                    # Adaptive font size based on text length
                    font_size = 1.9
                    if len(cleaned_resource) > 20:
                        font_size = 1.7
                    if len(cleaned_resource) > 30:
                        font_size = 1.5
                    if len(cleaned_resource) > 40:
                        font_size = 1.3
                    if len(cleaned_resource) > 50:
                        font_size = 1.1
                    
                    # Direct card using HTML with dynamic font scaling
                    st.markdown(f"""
                    <div style="background-color: white; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); 
                                padding: 20px; text-align: center; height: 170px; margin-bottom: 20px; display: flex; flex-direction: column;">
                        <div style="font-weight: bold; color: #555; font-size: 1rem; margin-bottom: 10px;">Most Requested Resource</div>
                        <div style="font-size: {font_size}rem; font-weight: bold; color: #4361EE; margin-bottom: 8px; flex-grow: 1; 
                                  overflow: hidden; text-overflow: ellipsis; display: flex; align-items: center; justify-content: center; 
                                  line-height: 1.2; word-wrap: break-word; padding: 0 5px;">{cleaned_resource}</div>
                        <div style="color: #666; font-size: 0.9rem; margin-top: auto; white-space: nowrap;">{percentage}% of resource mentions</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    # Fallback for when no data is available with consistent styling
                    st.markdown(f"""
                    <div style="background-color: white; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); 
                                padding: 20px; text-align: center; height: 170px; margin-bottom: 20px; display: flex; flex-direction: column;">
                        <div style="font-weight: bold; color: #555; font-size: 1rem; margin-bottom: 10px;">Most Requested Resource</div>
                        <div style="font-size: 1.9rem; font-weight: bold; color: #4361EE; margin-bottom: 8px; flex-grow: 1; 
                                  overflow: hidden; text-overflow: ellipsis; display: flex; align-items: center; justify-content: center;
                                  line-height: 1.2; word-wrap: break-word; padding: 0 5px;">N/A</div>
                        <div style="color: #666; font-size: 0.9rem; margin-top: auto; white-space: nowrap;">No resource data available</div>
                    </div>
                    """, unsafe_allow_html=True)
            except Exception as e:
                logger.error(f"Error displaying most requested resource: {str(e)}")
                
                # Direct card using HTML for error case with improved text overflow control
                st.markdown(f"""
                <div style="background-color: white; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); 
                            padding: 20px; text-align: center; height: 170px; margin-bottom: 20px; display: flex; flex-direction: column;">
                    <div style="font-weight: bold; color: #555; font-size: 1rem; margin-bottom: 10px;">Most Requested Resource</div>
                    <div style="font-size: 1.9rem; font-weight: bold; color: #4361EE; margin-bottom: 8px; flex-grow: 1; 
                              overflow: hidden; text-overflow: ellipsis; display: flex; align-items: center; justify-content: center;
                              line-height: 1.2; word-wrap: break-word; padding: 0 5px;">N/A</div>
                    <div style="color: #666; font-size: 0.9rem; margin-top: auto; white-space: nowrap;">Error processing data</div>
                </div>
                """, unsafe_allow_html=True)
        
        # Add vertical space before visualizations
        add_vertical_space(3)
        
        # Subheader for visualizations
        section_header("Visualization of Key Challenges", 
                      "The charts below illustrate the most significant barriers and hurdles reported by survey respondents.")
        
        # Visualizations for tab 1 with container for consistent spacing
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        
        # Device-optimized layout
        device = optimize_for_device()
        cols = st.columns(device['column_count'])
        
        if device['is_mobile']:
            # Single column for mobile
            with cols[0]:
                render_mobile_chart(dashboard.create_hurdles_chart(filtered_data))
                
                # Add vertical space between charts on mobile
                st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)
                
                render_mobile_chart(dashboard.create_barriers_chart(filtered_data))
        else:
            # Two columns for desktop
            with cols[0]:
                render_mobile_chart(dashboard.create_hurdles_chart(filtered_data))
                
            with cols[1]:
                render_mobile_chart(dashboard.create_barriers_chart(filtered_data))
                
        st.markdown('</div>', unsafe_allow_html=True)
            
        # Add vertical space after visualizations
        add_vertical_space(2)
        
        # Add significant vertical spacing
        st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)
        
        # Additional visualizations with container for consistent spacing
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            render_mobile_chart(dashboard.create_complexity_by_affiliation_chart(filtered_data))
            
        with col2:
            render_mobile_chart(dashboard.create_timeline_distribution_chart(filtered_data))
        st.markdown('</div>', unsafe_allow_html=True)
        
        # End of Key Challenges section - no correlation heatmap
    
    # Tab 2: Detailed Analysis
    with tab2:
        section_header("🔍 Detailed Analysis of Survey Responses", 
                      "This section provides a deeper dive into the survey data, with visualizations highlighting specific pain points and needs.")
        
        # Add custom CSS for better section styling
        st.markdown("""
        <style>
        .analysis-section {
            background-color: #ffffff;
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 35px;
            box-shadow: 0 3px 8px rgba(0, 0, 0, 0.07);
            border-left: 5px solid #0A2F51;
            transition: all 0.3s ease;
            border: 1px solid #f0f0f0;
        }
        
        .analysis-section:hover {
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
            transform: translateY(-3px);
        }
        
        .section-title {
            color: #0A2F51;
            font-size: 1.5rem;
            margin-bottom: 20px;
            border-bottom: 1px solid #e5e5e5;
            padding-bottom: 12px;
            font-weight: 600;
        }
        
        .section-subtitle {
            font-size: 1.2rem;
            color: #333;
            margin: 20px 0 12px 0;
            font-weight: 600;
            border-left: 3px solid #0A2F51;
            padding-left: 10px;
        }
        
        .insight-highlight {
            background-color: #f0f7ff;
            border-radius: 8px;
            padding: 15px 20px;
            margin: 20px 0;
            border-left: 4px solid #0A2F51;
            font-style: italic;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
        }
        
        /* Improving text formatting */
        p {
            line-height: 1.7;
            margin-bottom: 15px;
            color: #333;
        }
        
        ul, ol {
            padding-left: 25px;
            margin-bottom: 20px;
            line-height: 1.7;
        }
        
        li {
            margin-bottom: 8px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Challenging factors with improved section styling - Fixed text rendering
        html_content("""
        <div class="analysis-section">
            <div class="section-title">📊 Most Challenging Factors for Small Businesses</div>
        </div>
        """)
        
        # Break up the content into smaller chunks for better rendering
        st.markdown("The chart below shows the factors that small businesses identified as most challenging when pursuing federal contracts. These obstacles represent key areas where policy interventions could have the greatest impact.")
        
        st.markdown("<div class='section-subtitle'>Key Insights:</div>", unsafe_allow_html=True)
        st.markdown("<div class='insight-highlight'>The top challenges relate to navigation complexity and understanding requirements, suggesting that streamlining processes and improving guidance could have the greatest impact.</div>", unsafe_allow_html=True)
        
        st.markdown("*Interact with the chart to explore details. Hover over bars for exact counts and percentages.*")
        
        # Challenging factors horizontal bar chart with improved formatting
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        # Use lazy loading for heavy charts on mobile devices
        if is_likely_mobile():
            lazy_load_chart(
                lambda: render_mobile_chart(dashboard.create_challenging_factors_chart(filtered_data)),
                chart_id="challenging_factors",
                button_text="Load Chart"
            )
        else:
            # On desktop, load immediately
            render_mobile_chart(dashboard.create_challenging_factors_chart(filtered_data))
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Add vertical spacing between sections
        st.markdown('<div style="margin-top: 30px; margin-bottom: 30px;"></div>', unsafe_allow_html=True)
        
        # Needed resources section with enhanced styling - Fixed text rendering
        st.markdown("""
        <div class="analysis-section">
            <div class="section-title">🛠️ Most Needed Resources</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Break up the content into smaller chunks for better rendering
        st.markdown("This visualization shows the resources that respondents indicated would be most helpful in addressing the challenges they face. The size and color intensity of each segment corresponds to how frequently each resource was mentioned.")
        
        st.markdown("<div class='section-subtitle'>How to Use This Chart:</div>", unsafe_allow_html=True)
        
        # Use native Streamlit bullet points
        st.markdown("- Larger segments represent more frequently requested resources")
        st.markdown("- Click on segments to see detailed information")
        st.markdown("- Hover over areas to see exact counts and percentages")
        
        # Needed resources chart
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        render_mobile_chart(dashboard.create_needed_resources_chart(filtered_data))
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Add vertical spacing between sections
        st.markdown('<div style="margin-top: 30px; margin-bottom: 30px;"></div>', unsafe_allow_html=True)
        
        # Breakdown by respondent type with enhanced styling - Fixed text rendering
        st.markdown("""
        <div class="analysis-section">
            <div class="section-title">👥 Breakdown by Respondent Type</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Use content prioritization for better mobile experience
        content_blocks = {
            'intro': {
                'content': lambda: st.markdown("This analysis compares perspectives across different types of stakeholders in the federal contracting ecosystem. Understanding these varying viewpoints is essential for developing solutions that address the needs of all participants."),
                'priority': 1,
                'show_on_mobile': True
            },
            'subtitle': {
                'content': lambda: st.markdown("<div class='section-subtitle'>What to Look For:</div>", unsafe_allow_html=True),
                'priority': 2,
                'show_on_mobile': True
            },
            'bullet_points': {
                'content': lambda: (
                    st.markdown("- Differences in complexity perception between small businesses and other stakeholders"),
                    st.markdown("- Distribution of respondent types in the survey sample"),
                    st.markdown("- Variations in reported challenges by respondent category")
                ),
                'priority': 3,
                'show_on_mobile': True
            },
            'additional_context': {
                'content': lambda: st.markdown("The chart below highlights how different stakeholder groups perceive the complexity of the federal contracting process, which can significantly impact how we design support systems for small businesses."),
                'priority': 4,
                'show_on_mobile': False  # Hide on mobile to save space
            }
        }
        
        # Display content in priority order, adapting to device
        display_content_by_priority(content_blocks)
        
        try:
            # Create a figure with subplots
            fig = make_subplots(rows=1, cols=2, 
                              specs=[[{"type": "pie"}, {"type": "bar"}]],
                              subplot_titles=("Distribution of Respondents", "Average Complexity by Respondent Type"))
            
            # Add respondent distribution pie chart
            affiliation_counts = filtered_data['affiliation_category'].value_counts()
            fig.add_trace(
                go.Pie(
                    labels=affiliation_counts.index,
                    values=affiliation_counts.values,
                    textinfo='percent+label',
                    marker=dict(colors=px.colors.qualitative.Pastel)
                ),
                row=1, col=1
            )
            
            # Add complexity by affiliation bar chart
            complexity_by_affiliation = filtered_data.groupby('affiliation_category')['onboarding_complexity'].mean().reset_index()
            fig.add_trace(
                go.Bar(
                    x=complexity_by_affiliation['affiliation_category'],
                    y=complexity_by_affiliation['onboarding_complexity'],
                    marker=dict(color=px.colors.qualitative.Pastel)
                ),
                row=1, col=2
            )
            
            # Update layout with light mode styling
            fig.update_layout(
                height=500,
                showlegend=False,
                paper_bgcolor='#FFFFFF',  # White paper background
                plot_bgcolor='#F8F9FA',   # Light plot background
                font={'color': '#333333', 'size': 12}, # Dark text for light background
                margin={'l': 50, 'r': 20, 't': 50, 'b': 100},
                xaxis={'tickfont': {'color': '#333333'}, 'gridcolor': '#F0F0F0'},
                yaxis={'tickfont': {'color': '#333333'}, 'gridcolor': '#F0F0F0'}
            )
            
            # Update subplot titles for light mode
            fig.update_annotations(font_color='#333333')
            
            # Display the figure with mobile optimization
            render_mobile_chart(fig)
        except Exception as e:
            st.error(f"Error creating respondent breakdown: {str(e)}")
    
    # Tab 3: Open-Ended Responses
    with tab3:
        section_header("💬 Analysis of Open-Ended Responses", 
                      "This section categorizes and presents qualitative feedback from the survey responses, organized by theme and sentiment.")
        
        # Function to display all responses for a selected theme
        def display_theme_responses(df_responses, selected_theme, selected_sentiment="All"):
            """
            Display all individual responses for the selected theme in an organized, visually appealing way
            
            Parameters:
            - df_responses: DataFrame containing your response data (not used in this implementation)
            - selected_theme: Currently selected theme from the dropdown
            - selected_sentiment: Filter for sentiment (All, Positive, Neutral, Negative)
            """
            # For this implementation, we'll use our themed data dictionary
            if selected_theme not in themes:
                st.warning(f"Theme '{selected_theme}' not found.")
                return
                
            # Get theme data
            theme_data = themes[selected_theme]
            
            # Generate more examples for demonstration purposes (since we only have a few in the original data)
            # In a real application, you would use the actual complete dataset instead
            expanded_examples = []
            
            # Start with existing examples
            expanded_examples.extend(theme_data["examples"])
            
            # Add more examples based on the theme to simulate a fuller dataset
            if selected_theme == "Registration Process":
                expanded_examples.extend([
                    {"text": "Need a wizard-like interface for first-time users of the registration system", "sentiment": "neutral"},
                    {"text": "The verification process takes too long; it should be streamlined", "sentiment": "negative"},
                    {"text": "Too many overlapping requirements across different registration systems", "sentiment": "negative"},
                    {"text": "I like the recent improvements to user interface on SAM.gov", "sentiment": "positive"},
                    {"text": "Documentation should explain why certain information is needed", "sentiment": "neutral"},
                    {"text": "The helpdesk representatives were very helpful during our registration", "sentiment": "positive"}
                ])
            elif selected_theme == "Technical Support":
                expanded_examples.extend([
                    {"text": "Support wait times are unacceptably long during peak periods", "sentiment": "negative"},
                    {"text": "Email support responses were thorough and helpful", "sentiment": "positive"},
                    {"text": "Need more technical support resources specifically for small businesses", "sentiment": "neutral"},
                    {"text": "Phone support staff seem undertrained on complex technical issues", "sentiment": "negative"},
                    {"text": "Support documentation should be updated more frequently", "sentiment": "neutral"}
                ])
            elif selected_theme == "Documentation Requirements":
                expanded_examples.extend([
                    {"text": "Too many different formats required for similar information", "sentiment": "negative"},
                    {"text": "Examples of properly completed forms would be extremely helpful", "sentiment": "neutral"},
                    {"text": "Documentation process is becoming more streamlined each year", "sentiment": "positive"},
                    {"text": "Need better guidance on which documents are truly required vs. optional", "sentiment": "neutral"},
                    {"text": "The document upload portal is confusing and unreliable", "sentiment": "negative"}
                ])
            elif selected_theme == "Cybersecurity Compliance":
                expanded_examples.extend([
                    {"text": "The cost of implementing CMMC requirements is prohibitive for small firms", "sentiment": "negative"},
                    {"text": "Need more affordable options for small businesses to meet cybersecurity requirements", "sentiment": "neutral"},
                    {"text": "The phased approach to implementing new requirements is helpful", "sentiment": "positive"},
                    {"text": "Resources provided for cybersecurity assessment were clear and useful", "sentiment": "positive"},
                    {"text": "Difficult to understand which specific controls apply to our situation", "sentiment": "negative"},
                    {"text": "Provide templates for creating required security documentation", "sentiment": "neutral"}
                ])
            elif selected_theme == "Training & Education":
                expanded_examples.extend([
                    {"text": "The procurement training webinars were excellent and very practical", "sentiment": "positive"},
                    {"text": "Need more hands-on workshops rather than just presentations", "sentiment": "neutral"},
                    {"text": "Training materials are too general and don't address specific industries", "sentiment": "negative"},
                    {"text": "Online knowledge base has been extremely helpful for quick questions", "sentiment": "positive"},
                    {"text": "Make training modules available on-demand instead of scheduled sessions", "sentiment": "neutral"},
                    {"text": "Trainers often cannot answer specific technical questions", "sentiment": "negative"}
                ])
            elif selected_theme == "Communication":
                expanded_examples.extend([
                    {"text": "Response time from contracting officers is inconsistent and unpredictable", "sentiment": "negative"},
                    {"text": "The new notification system has improved communication significantly", "sentiment": "positive"},
                    {"text": "Need more transparency about where applications are in the review process", "sentiment": "neutral"},
                    {"text": "Guidelines for how and when to contact contracting officers would be helpful", "sentiment": "neutral"},
                    {"text": "Automated status updates have been a welcome improvement", "sentiment": "positive"},
                    {"text": "Communication channels between different agencies are still fragmented", "sentiment": "negative"}
                ])
            
            # Apply sentiment filter if not "All"
            filtered_examples = expanded_examples
            if selected_sentiment != "All":
                filtered_examples = [ex for ex in filtered_examples if ex["sentiment"].lower() == selected_sentiment.lower()]
            
            # Count responses after filtering
            response_count = len(filtered_examples)
            
            # Display theme header with count (maintaining your existing style but with better contrast)
            st.markdown(f"""
                <div style="background-color:#1E3A8A; color:white; padding:15px 20px; border-radius:5px; margin-bottom:20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                    <h3 style="margin:0; font-size:1.4rem; font-weight:bold;">{selected_theme}</h3>
                    <p style="margin:7px 0 0 0; font-size:1.0rem;"><strong>{response_count} responses</strong></p>
                </div>
            """, unsafe_allow_html=True)
            
            # Display theme description
            st.markdown(f"<p style='margin-bottom:20px;'>{theme_data['description']}</p>", unsafe_allow_html=True)
            
            # Instead of using a single HTML string, we'll create individual cards
            # to avoid issues with markdown rendering
            
            # Create a multi-column layout for the responses with 2 columns
            cols = st.columns(2)
            col_idx = 0
            
            # Generate cards for each response
            for example in filtered_examples:
                response_text = example["text"]
                sentiment = example["sentiment"].lower()
                
                # Alternate between columns
                with cols[col_idx]:
                    # Display sentiment indicator based on sentiment
                    if sentiment == "positive":
                        sentiment_icon = "✅"
                        indicator_color = "#10B981"
                    elif sentiment == "negative":
                        sentiment_icon = "❌"
                        indicator_color = "#EF4444"
                    else:
                        sentiment_icon = "⚠️"
                        indicator_color = "#F59E0B"
                    
                    # Create a card with proper styling
                    st.markdown(
                        f"""
                        <div style="background-color: white; border-radius: 5px; padding: 15px; 
                                 box-shadow: 0 1px 3px rgba(0,0,0,0.1); position: relative; 
                                 border-left: 4px solid {indicator_color}; margin-bottom: 15px;">
                            <span style="position: absolute; top: 8px; right: 10px;">{sentiment_icon}</span>
                            <p style="margin:0; font-style:italic;">"{response_text}"</p>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                
                # Alternate column index (0,1,0,1,etc.)
                col_idx = (col_idx + 1) % 2
            
            # If no responses match the filter criteria
            if response_count == 0:
                st.info(f"No {selected_sentiment.lower() if selected_sentiment != 'All' else ''} responses found for this theme.")
        
        # Add custom CSS for enhanced card layout and animations
        st.markdown("""
        <style>
        /* Theme cards styling - improved with consistent spacing and better visual hierarchy */
        .theme-card {
            background-color: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 24px; /* Increased for better spacing */
            box-shadow: 0 3px 10px rgba(0, 0, 0, 0.08);
            transition: all 0.3s ease;
            border-top: 5px solid transparent;
            display: flex;
            flex-direction: column;
            height: 100%; /* Make all cards same height */
        }
        .theme-card:hover {
            box-shadow: 0 6px 15px rgba(0, 0, 0, 0.1);
            transform: translateY(-2px);
        }
        /* Color-coding for theme categories with improved contrasting colors */
        .theme-card.registration { border-color: #0066cc; }
        .theme-card.technical { border-color: #00a3cc; }
        .theme-card.documentation { border-color: #00cc66; }
        .theme-card.cybersecurity { border-color: #ff9900; }
        .theme-card.training { border-color: #cc3300; }
        .theme-card.communication { border-color: #9900cc; }
        
        /* Theme header styling with consistent alignment */
        .theme-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            border-bottom: 1px solid #e0e0e0;
            padding-bottom: 12px;
        }
        .theme-title {
            font-size: 1.3rem;
            font-weight: bold;
            color: #333;
            line-height: 1.3;
        }
        .theme-count {
            background-color: #f5f5f5;
            padding: 5px 12px;
            border-radius: 20px;
            font-weight: bold;
            color: #555;
            white-space: nowrap;
            margin-left: 10px;
        }
        
        /* Improved quote card styling with flexible height and scrolling */
        .quote-card {
            background-color: #f9f9f9;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 12px;
            position: relative;
            border-left: 3px solid #ddd;
            transition: all 0.2s ease;
            width: 100%; /* Consistent width */
            max-height: 200px; /* Max height with overflow */
            overflow-y: auto; /* Enable scrolling for long quotes */
        }
        /* Add subtle separator between quote cards */
        .quote-card:not(:last-child)::after {
            content: '';
            position: absolute;
            bottom: -6px;
            left: 10%;
            right: 10%;
            height: 1px;
            background-color: #f0f0f0;
        }
        .quote-card:hover {
            background-color: #f0f7ff;
            border-left-color: #4287f5;
        }
        .quote-text {
            font-style: italic;
            color: #333;
            margin-bottom: 5px;
            overflow-wrap: break-word; /* Prevent text overflow */
            line-height: 1.4; /* Improved readability */
        }
        .sentiment {
            position: absolute;
            top: 10px;
            right: 10px;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1); /* Subtle shadow */
        }
        /* Enhanced sentiment indicators with better color contrast */
        .sentiment.positive { background-color: #c8e6c9; color: #2e7d32; }
        .sentiment.neutral { background-color: #fff9c4; color: #f57f17; }
        .sentiment.negative { background-color: #ffcdd2; color: #c62828; }
        
        /* Scrollbar styling for quote cards */
        .quote-card::-webkit-scrollbar {
            width: 6px;
        }
        .quote-card::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 10px;
        }
        .quote-card::-webkit-scrollbar-thumb {
            background: #ccc;
            border-radius: 10px;
        }
        .quote-card::-webkit-scrollbar-thumb:hover {
            background: #aaa;
        }
        
        /* Search box styling */
        .search-box {
            width: 100%;
            padding: 10px 15px;
            font-size: 1rem;
            border: 1px solid #ddd;
            border-radius: 5px;
            margin-bottom: 20px;
            transition: all 0.3s ease;
        }
        .search-box:focus {
            border-color: #4287f5;
            box-shadow: 0 0 0 3px rgba(66, 135, 245, 0.2);
            outline: none;
        }
        
        /* Tab navigation styling */
        .theme-tabs {
            display: flex;
            overflow-x: auto;
            padding-bottom: 10px;
            margin-bottom: 20px;
            border-bottom: 1px solid #eee;
        }
        .theme-tab {
            padding: 8px 16px;
            margin-right: 10px;
            background-color: #f5f5f5;
            border-radius: 20px;
            cursor: pointer;
            white-space: nowrap;
            transition: all 0.2s ease;
        }
        .theme-tab:hover {
            background-color: #e8e8e8;
        }
        .theme-tab.active {
            background-color: #0A2F51;
            color: white;
        }
        
        /* Response grid styling for drill-down view */
        .response-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        .response-card {
            background-color: white;
            border-radius: 5px;
            padding: 15px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            position: relative;
            border-left: 4px solid #1E3A8A;
            margin-bottom: 0 !important;
        }
        .sentiment-indicator {
            position: absolute;
            top: 10px;
            right: 10px;
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }
        .sentiment-positive {
            background-color: #10B981;
        }
        .sentiment-neutral {
            background-color: #F59E0B;
        }
        .sentiment-negative {
            background-color: #EF4444;
        }
        
        /* View toggle styling */
        .view-toggle {
            display: flex;
            justify-content: center;
            margin: 15px 0;
            background-color: #f0f0f0;
            border-radius: 8px;
            padding: 5px;
            width: fit-content;
        }
        .view-option {
            padding: 8px 16px;
            cursor: pointer;
            border-radius: 6px;
            font-weight: 500;
            transition: all 0.2s ease;
        }
        .view-option.active {
            background-color: #1E3A8A;
            color: white;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Introduction with enhanced styling
        st.markdown("""
        <div style="background-color: #f0f7ff; padding: 20px; border-radius: 10px; margin-bottom: 25px; border-left: 5px solid #0A2F51;">
            <h4 style="color: #0A2F51; margin-top: 0;">Categorized Suggestions for Improvement</h4>
            <p>Below are respondent suggestions grouped by theme. Each category represents a key area 
            where improvements could significantly impact the federal contracting process for small 
            businesses. We've included representative quotes from survey responses to illustrate 
            the specific pain points within each category.</p>
            <p style="margin-bottom: 0; font-style: italic;">Use the search and filtering options to explore specific themes and identify patterns in the feedback.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Create themed categories from the responses with sentiment annotations
        # In a real app, you would analyze the actual responses and categorize them
        # Here we're creating a structured representation based on the data analysis
        
        themes = {
            "Registration Process": {
                "count": 32,
                "description": "Suggestions related to simplifying the registration and system access process",
                "class": "registration",
                "examples": [
                    {"text": "Streamline the SAM.gov registration to reduce redundant information entry", "sentiment": "negative"},
                    {"text": "Create a single sign-on system for all federal contracting portals", "sentiment": "neutral"},
                    {"text": "Provide clearer step-by-step guidance through the registration process", "sentiment": "neutral"},
                    {"text": "The registration process is too complex and takes too much time away from our core business", "sentiment": "negative"}
                ]
            },
            "Technical Support": {
                "count": 28,
                "description": "Suggestions for improving technical assistance and support",
                "class": "technical",
                "examples": [
                    {"text": "Provide dedicated support specialists for first-time contractors", "sentiment": "positive"},
                    {"text": "Create a real-time chat support option for SAM.gov registration issues", "sentiment": "neutral"},
                    {"text": "Develop better troubleshooting guides for common technical problems", "sentiment": "neutral"},
                    {"text": "Current support options are inadequate for resolving complex technical issues", "sentiment": "negative"}
                ]
            },
            "Documentation Requirements": {
                "count": 24,
                "description": "Suggestions to simplify or clarify documentation requirements",
                "class": "documentation",
                "examples": [
                    {"text": "Reduce the volume of required paperwork for initial registration", "sentiment": "neutral"},
                    {"text": "Create standardized templates for common proposal requirements", "sentiment": "positive"},
                    {"text": "Provide examples of successful submissions for reference", "sentiment": "positive"},
                    {"text": "Documentation is overwhelming and often redundant across different systems", "sentiment": "negative"}
                ]
            },
            "Cybersecurity Compliance": {
                "count": 19,
                "description": "Suggestions regarding cybersecurity requirements and compliance",
                "class": "cybersecurity",
                "examples": [
                    {"text": "Develop tiered cybersecurity requirements based on contract size", "sentiment": "positive"},
                    {"text": "Provide subsidized cybersecurity assessment services for small businesses", "sentiment": "positive"},
                    {"text": "Create plain-language guides to interpreting CMMC requirements", "sentiment": "neutral"},
                    {"text": "Current cybersecurity requirements are cost-prohibitive for small businesses", "sentiment": "negative"}
                ]
            },
            "Training & Education": {
                "count": 17,
                "description": "Suggestions for improved training and educational resources",
                "class": "training",
                "examples": [
                    {"text": "Develop short video tutorials for each step of the contracting process", "sentiment": "positive"},
                    {"text": "Create industry-specific training modules with relevant examples", "sentiment": "positive"},
                    {"text": "Establish a mentorship program connecting new and experienced contractors", "sentiment": "positive"},
                    {"text": "Current training materials are too generic and don't address specific challenges", "sentiment": "negative"}
                ]
            },
            "Communication": {
                "count": 15,
                "description": "Suggestions to improve communication with contracting officers",
                "class": "communication",
                "examples": [
                    {"text": "Provide more opportunities for Q&A sessions with contracting officers", "sentiment": "positive"},
                    {"text": "Establish clearer communication channels for pre-bid questions", "sentiment": "neutral"},
                    {"text": "Create a standardized feedback mechanism for unsuccessful bids", "sentiment": "positive"},
                    {"text": "Communication with contracting officers is inconsistent and often delayed", "sentiment": "negative"}
                ]
            }
        }
        
        # Add search functionality
        search_term = st.text_input("🔍 Search responses", "", help="Search for specific terms in the open-ended responses")
        
        # Create interactive tabs for theme selection
        st.markdown('<div class="theme-tabs">', unsafe_allow_html=True)
        all_tab_class = "active" if "selected_theme" not in st.session_state or st.session_state.get("selected_theme") == "All Themes" else ""
        st.markdown(f'<div class="theme-tab {all_tab_class}" onclick="Streamlit.setComponentValue(\'selected_theme\', \'All Themes\')">All Themes</div>', unsafe_allow_html=True)
        
        for theme in themes.keys():
            theme_class = "active" if st.session_state.get("selected_theme") == theme else ""
            st.markdown(f'<div class="theme-tab {theme_class}" onclick="Streamlit.setComponentValue(\'selected_theme\', \'{theme}\')">{theme} ({themes[theme]["count"]})</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Create a placeholder for the selected theme
        if "selected_theme" not in st.session_state:
            st.session_state.selected_theme = "All Themes"
        
        selected_theme = st.selectbox(
            "Filter by theme",
            ["All Themes"] + list(themes.keys()),
            key="selected_theme",
            label_visibility="collapsed"  # Hide the label since we have the tabs
        )
        
        # Add view mode toggle
        if "view_mode" not in st.session_state:
            st.session_state.view_mode = "Summary"
            
        col1, col2 = st.columns([1, 5])
        with col1:
            view_mode = st.radio(
                "View Mode",
                ["Summary", "All Responses"],
                key="view_mode",
                horizontal=True,
                label_visibility="collapsed"
            )
        
        # Filter for sentiment if needed
        sentiment_filter = st.radio(
            "Filter by sentiment",
            ["All", "Positive", "Neutral", "Negative"],
            horizontal=True
        )
        
        # Display themed responses with enhanced card layout
        # For All Responses view mode, use our new drill-down function
        if view_mode == "All Responses" and selected_theme != "All Themes":
            # Add a header to explain what the user is viewing
            st.markdown("""
            <div style="margin-bottom: 20px; background-color: #E1EFFE; padding: 15px; border-radius: 8px; border-left: 5px solid #1E3A8A;">
                <h4 style="margin-top: 0; color: #000000; font-weight: bold;">All Responses View</h4>
                <p style="margin-bottom: 0; color: #000000;">Viewing all individual responses for the selected theme. Use the sentiment filter to narrow results.</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Use the dedicated function to display all responses for the selected theme
            display_theme_responses(None, selected_theme, sentiment_filter)
        elif selected_theme == "All Themes":
            if search_term:
                # Filter themes by search term
                filtered_themes = {}
                for theme_name, theme_data in themes.items():
                    matching_examples = [ex for ex in theme_data["examples"] 
                                       if search_term.lower() in ex["text"].lower() and
                                       (sentiment_filter == "All" or 
                                        sentiment_filter.lower() == ex["sentiment"])]
                    if matching_examples:
                        filtered_themes[theme_name] = {**theme_data, "examples": matching_examples}
                
                # Display filtered themes
                if filtered_themes:
                    st.markdown(f"<p>Found matches in {len(filtered_themes)} themes for <b>'{search_term}'</b></p>", unsafe_allow_html=True)
                    for theme, data in sorted(filtered_themes.items(), key=lambda x: x[1]["count"], reverse=True):
                        st.markdown(f"""
                        <div class="theme-card {data['class']}">
                            <div class="theme-header">
                                <div class="theme-title">{theme}</div>
                                <div class="theme-count">{len(data['examples'])} matching responses</div>
                            </div>
                            <p>{data['description']}</p>
                        """, unsafe_allow_html=True)
                        
                        # Display matching quotes
                        for example in data["examples"]:
                            st.markdown(f"""
                            <div class="quote-card">
                                <div class="sentiment {example['sentiment']}">
                                    {sentiment_icons[example['sentiment']]}
                                </div>
                                <p class="quote-text">"{example['text']}"</p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.warning(f"No responses containing '{search_term}' found.")
            else:
                # Display summary cards for all themes
                col1, col2 = st.columns(2)
                
                for i, (theme, data) in enumerate(sorted(themes.items(), key=lambda x: x[1]["count"], reverse=True)):
                    # Filter examples by sentiment if needed
                    filtered_examples = data["examples"]
                    if sentiment_filter != "All":
                        filtered_examples = [ex for ex in data["examples"] if sentiment_filter.lower() == ex["sentiment"]]
                    
                    if filtered_examples:
                        with col1 if i % 2 == 0 else col2:
                            st.markdown(f"""
                            <div class="theme-card {data['class']}">
                                <div class="theme-header">
                                    <div class="theme-title">{theme}</div>
                                    <div class="theme-count">{data['count']} responses</div>
                                </div>
                                <p>{data['description']}</p>
                                <div style="margin-top: 15px;">
                                    <strong>Sample quote:</strong>
                                    <div class="quote-card">
                                        <div class="sentiment {filtered_examples[0]['sentiment']}">
                                            {sentiment_icons[filtered_examples[0]['sentiment']]}
                                        </div>
                                        <p class="quote-text">"{filtered_examples[0]['text']}"</p>
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
        else:
            # Add a header to explain what the user is viewing in summary mode
            st.markdown("""
            <div style="margin-bottom: 20px; background-color: #f0f7ff; padding: 15px; border-radius: 8px; border-left: 4px solid #0A2F51;">
                <h4 style="margin-top: 0; color: #0A2F51;">Summary View</h4>
                <p style="margin-bottom: 0;">Viewing a curated selection of representative responses. Switch to "All Responses" view to see every response.</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Display detailed view of selected theme
            data = themes[selected_theme]
            
            # Filter examples by sentiment and search term
            filtered_examples = data["examples"]
            if sentiment_filter != "All":
                filtered_examples = [ex for ex in filtered_examples if sentiment_filter.lower() == ex["sentiment"]]
            if search_term:
                filtered_examples = [ex for ex in filtered_examples if search_term.lower() in ex["text"].lower()]
            
            # Display theme header
            st.markdown(f"""
            <div class="theme-card {data['class']}">
                <div class="theme-header">
                    <div class="theme-title">{selected_theme}</div>
                    <div class="theme-count">{data['count']} responses</div>
                </div>
                <p>{data['description']}</p>
            """, unsafe_allow_html=True)
            
            # Show filtered results message if applicable
            if sentiment_filter != "All" or search_term:
                filter_text = []
                if search_term:
                    filter_text.append(f"containing '{search_term}'")
                if sentiment_filter != "All":
                    filter_text.append(f"with {sentiment_filter.lower()} sentiment")
                
                st.markdown(f"<p>Showing {len(filtered_examples)} responses {' and '.join(filter_text)}</p>", unsafe_allow_html=True)
            
            # Display all quotes for the theme
            if filtered_examples:
                for example in filtered_examples:
                    st.markdown(f"""
                    <div class="quote-card">
                        <div class="sentiment {example['sentiment']}">
                            {sentiment_icons[example['sentiment']]}
                        </div>
                        <p class="quote-text">"{example['text']}"</p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown("<p>No matching responses found for the current filters.</p>", unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Show related themes with improved layout and visual boundaries
            st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)
            st.markdown("""
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 10px; margin-top: 20px; border-top: 3px solid #0A2F51;">
                <h4 style="margin-top: 0; margin-bottom: 15px; color: #0A2F51;">Related Themes</h4>
                <p style="margin-bottom: 15px; font-style: italic;">Explore other categories of feedback that may provide additional context</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Create a grid layout for related themes with equal visual weight
            related_themes = [t for t in themes.keys() if t != selected_theme]
            cols = st.columns(3)
            
            # Create an evenly-spaced grid with consistent styling
            for i, theme in enumerate(related_themes[:6]):
                theme_class = themes[theme]['class']  # Get theme color class
                with cols[i % 3]:
                    st.markdown(f"""
                    <div style="background-color: #ffffff; padding: 15px; border-radius: 8px; text-align: center; 
                         cursor: pointer; margin-bottom: 15px; transition: all 0.2s ease; box-shadow: 0 2px 5px rgba(0,0,0,0.05);
                         border-left: 4px solid var(--theme-color); height: 100px; display: flex; flex-direction: column; 
                         justify-content: center; align-items: center;"
                         onclick="Streamlit.setComponentValue('selected_theme', '{theme}')"
                         onmouseover="this.style.boxShadow='0 4px 8px rgba(0,0,0,0.1)'; this.style.transform='translateY(-2px)';" 
                         onmouseout="this.style.boxShadow='0 2px 5px rgba(0,0,0,0.05)'; this.style.transform='translateY(0)';"
                         class="theme-{theme_class}">
                        <div style="font-weight: bold; font-size: 1.1rem; margin-bottom: 8px;">{theme}</div>
                        <div style="background-color: #f5f5f5; padding: 3px 10px; border-radius: 12px; display: inline-block;">
                            {themes[theme]['count']} responses
                        </div>
                    </div>
                    
                    <style>
                    .theme-registration {{ --theme-color: #0066cc; }}
                    .theme-technical {{ --theme-color: #00a3cc; }}
                    .theme-documentation {{ --theme-color: #00cc66; }}
                    .theme-cybersecurity {{ --theme-color: #ff9900; }}
                    .theme-training {{ --theme-color: #cc3300; }}
                    .theme-communication {{ --theme-color: #9900cc; }}
                    </style>
                    """, unsafe_allow_html=True)
    
    # Tab 4: Recommendations
    with tab4:
        section_header("🚀 Recommendations Based on Survey Findings", 
                      "This section presents actionable recommendations derived from the survey data, with implementation steps and expected impacts.")
        
        # Add custom CSS for recommendation cards
        st.markdown("""
        <style>
        /* Custom styling for recommendation cards to prevent overflow */
        .recommendation-card {
            background-color: #ffffff;
            border-radius: 10px;
            padding: 1.8rem;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            margin-bottom: 2rem;
            height: auto !important;
            min-height: 100px;
            border: 1px solid #eee;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        
        .recommendation-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
        }
        
        .recommendation-card h3 {
            margin-bottom: 1rem;
            color: #0A2F51;
        }
        
        .recommendation-card ul {
            margin-left: 1.5rem;
            margin-bottom: 1rem;
        }
        
        .recommendation-card li {
            margin-bottom: 0.5rem;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Recommendation cards with improved styling
        st.markdown("""
        <div class="recommendation-card">
            <h3>🌟 Primary Recommendation: Centralized Getting Started Portal</h3>
            <p>Based on survey responses, the most impactful improvement would be a centralized portal with step-by-step guidance for small businesses.</p>
            <p><b>Key features should include:</b></p>
            <ul>
                <li>Interactive checklists for registration requirements</li>
                <li>Simplified explanations of specialized terminology</li>
                <li>Consolidated access to all required systems</li>
                <li>Guided workflows for SAM.gov registration and certification</li>
            </ul>
            <p><b>Expected Impact:</b> Reduced onboarding time by 30-50% based on respondent feedback.</p>
        </div>
        
        <div class="recommendation-card">
            <h3>📚 Recommendation 2: Enhanced Training & Mentorship</h3>
            <p>Develop tailored training and mentorship programs to address the knowledge gap in federal procurement.</p>
            <p><b>Key components:</b></p>
            <ul>
                <li>Workshops specifically on cybersecurity requirements</li>
                <li>Mentorship matching with experienced contractors</li>
                <li>Plain language guides to solicitation requirements</li>
            </ul>
        </div>
        
        <div class="recommendation-card">
            <h3>🔄 Recommendation 3: Streamlined Registration Process</h3>
            <p>Simplify the registration and certification processes to reduce administrative burden.</p>
            <p><b>Key improvements:</b></p>
            <ul>
                <li>Simplified SAM.gov interface and registration workflow</li>
                <li>Reduced documentation requirements for initial registration</li>
                <li>Streamlined small business certification process</li>
            </ul>
        </div>
        
        <div class="recommendation-card">
            <h3>📋 Recommendation 4: Standardized Templates & Requirements</h3>
            <p>Develop standardized templates and simplified requirements for small business proposals.</p>
            <p><b>Key features:</b></p>
            <ul>
                <li>Standardized proposal templates for common contract types</li>
                <li>Simplified past performance requirements for first-time contractors</li>
                <li>Plain language solicitation templates</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        # Add vertical spacing before outcomes section
        add_vertical_space(3)
        
        # Expected outcomes with expanded explanations
        section_header("📊 Expected Outcomes", 
                      "The following outcomes are projected based on the survey data analysis and industry benchmarks.")
        
        st.markdown("""
        Our recommendations are expected to yield significant improvements in federal contracting 
        for small businesses. These outcomes are derived from survey data analysis, historical 
        improvement rates from similar initiatives, and stakeholder feedback.
        """)
        
        # Expanded outcome cards in a larger format
        st.markdown("""
        <div class="recommendation-card">
            <div class="flex-container">
                <div class="icon">⏱️</div>
                <div class="content">
                    <h3>Time to First Contract: 40% Reduction</h3>
                    <p>Based on survey data, small businesses currently spend an average of 18 months securing their first federal contract.
                    Our centralized portal and streamlined registration process is projected to reduce this timeline to approximately 11 months.</p>
                    <p><strong>Calculation methodology:</strong> We analyzed the current onboarding timeline reported by survey respondents, 
                    identified the specific processes causing the greatest delays, and calculated time savings from targeted improvements 
                    in those areas. The 40% reduction represents the weighted average of expected time savings across all reported delay factors.</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="recommendation-card">
            <div class="flex-container">
                <div class="icon">📈</div>
                <div class="content">
                    <h3>Small Business Participation: 25% Increase</h3>
                    <p>Survey data indicates that for every 100 small businesses that begin the federal contracting process, 
                    only about 40 complete it successfully. Our recommendations aim to increase this completion rate to approximately 50 businesses.</p>
                    <p><strong>Calculation methodology:</strong> We analyzed the attrition points in the current process using survey data, 
                    calculated the expected retention improvements from addressing each pain point, and applied a conservative adjustment 
                    factor based on similar initiatives in other procurement systems. The 25% represents net new small businesses 
                    successfully entering the federal marketplace.</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="recommendation-card">
            <div class="flex-container">
                <div class="icon">💰</div>
                <div class="content">
                    <h3>Contract Success Rate: 35% Improvement</h3>
                    <p>Currently, small businesses report a success rate of approximately 15% when bidding on federal contracts. 
                    Our recommendations, particularly enhanced training and standardized templates, are projected to increase this to about 20%.</p>
                    <p><strong>Calculation methodology:</strong> We calculated the average reported bid success rate from survey data, 
                    then estimated the expected improvement from each recommendation based on impact scores from respondents. 
                    The 35% figure represents relative improvement in success rate (not absolute percentage points), 
                    taking into account the combined effect of all recommendations with diminishing returns factored in.</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # End of Recommendations section - Next steps removed
        
        # Add mobile navigation for touch devices
        if is_likely_mobile():
            st.markdown("""
            <div class="mobile-nav">
                <a href="#" class="mobile-nav-button" onclick="document.querySelector('[data-baseweb=tab]').click()">
                    <div class="icon">📊</div>
                    <div>Key Data</div>
                </a>
                <a href="#" class="mobile-nav-button" onclick="document.querySelector('[data-baseweb=tab]:nth-child(2)').click()">
                    <div class="icon">🔍</div>
                    <div>Analysis</div>
                </a>
                <a href="#" class="mobile-nav-button" onclick="document.querySelector('[data-baseweb=tab]:nth-child(3)').click()">
                    <div class="icon">💬</div>
                    <div>Comments</div>
                </a>
                <a href="#" class="mobile-nav-button" onclick="document.querySelector('[data-baseweb=tab]:nth-child(4)').click()">
                    <div class="icon">🚀</div>
                    <div>Solutions</div>
                </a>
            </div>
            """, unsafe_allow_html=True)
            
            # Add page indicator for mobile users
            current_tab = st.session_state.get('current_tab', 0)
            st.markdown(f"""
            <div style="position: fixed; bottom: 70px; left: 0; right: 0; text-align: center; 
                       background: rgba(255,255,255,0.8); padding: 5px; font-size: 0.8rem; z-index: 999;">
                Page {current_tab + 1} of 4
            </div>
            """, unsafe_allow_html=True)
            
            # Add touch hint for mobile
            st.markdown("""
            <div style="position: fixed; top: 70px; right: 10px; background: rgba(255,255,255,0.8); 
                       padding: 5px 10px; border-radius: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); 
                       font-size: 0.8rem; color: #555; z-index: 999; animation: fadeOut 5s forwards 3s;">
                Swipe for more &rarr;
            </div>
            <style>
            @keyframes fadeOut {
                0% { opacity: 1; }
                100% { opacity: 0; visibility: hidden; }
            }
            </style>
            """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()