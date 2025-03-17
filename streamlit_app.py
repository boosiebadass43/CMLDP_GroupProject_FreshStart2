# Minimal entry point for Streamlit Cloud
# The simplest possible approach for running the dashboard

import os
import sys

# Make sure we can find our modules
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Import and run the main function
if __name__ == "__main__":
    # Import is inside the if block to prevent circular imports
    from embedded_app import main
    main()