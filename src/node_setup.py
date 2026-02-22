import os
import subprocess
import streamlit as st


@st.cache_resource
def ensure_node_modules():
    """Ensure top-level `node_modules` exist by running `npm ci` if needed."""
    # Resolve the project root (2 levels up from this file: src/project_hk → project root)
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    node_modules_path = os.path.join(PROJECT_ROOT, "node_modules")
    if not os.path.exists(node_modules_path):
        subprocess.run(["npm", "ci"], cwd=PROJECT_ROOT, check=True)

    return True
