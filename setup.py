from setuptools import setup, find_packages

setup(
    name="lcoe_solar_dc",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "streamlit>=1.41.1",
        "pandas>=2.2.0",
        "numpy>=1.26.3",
        "plotly>=5.18.0",
        "polars>=1.21.0",
        "pvlib>=0.11.2",
        "streamlit_folium>=0.24.0",
        "folium>=0.19.4",
        "reverse_geocoder>=1.5.1",
        "tzfpy>=0.16.4",
        "watchdog>=3.0.0"
    ],
    python_requires=">=3.8",
) 