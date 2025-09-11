"""
Combined Graduate Research Tool
Offers both general faculty search and psychology program finder
"""

import streamlit as st

def main():
    st.set_page_config(
        page_title="Graduate Research Tools",
        page_icon="🎓",
        layout="wide"
    )
    
    st.title("🎓 Graduate Research Tools")
    
    # Enhanced welcome message
    st.markdown("""
    **Welcome to the comprehensive graduate research platform!**  
    Choose your research focus below to get started.
    """)
    
    # Navigation with better descriptions
    tool_choice = st.selectbox(
        "🔧 Select Research Tool:",
        [
            "🔍 Faculty Research Finder", 
            "🧠 Psychology PhD Programs"
        ],
        index=1,  # Default to psychology tool since it's newer
        help="Choose between general faculty search across disciplines or specialized psychology program finder",
        key="main_tool_selector"
    )
    
    if tool_choice == "🔍 Faculty Research Finder":
        # Import and run the original app
        st.markdown("---")
        
        try:
            # Import the original app's main function
            from app_original_backup import main as original_main
            original_main()
        except Exception as e:
            st.error(f"Error loading Faculty Research Finder: {e}")
            st.markdown("Please ensure all dependencies are installed.")
    
    elif tool_choice == "🧠 Psychology PhD Programs":
        # Import and run the psychology app
        st.markdown("---")
        
        try:
            # Import the psychology app's main function
            from app_social_psych import main as psych_main
            psych_main()
        except Exception as e:
            st.error(f"Error loading Psychology Program Finder: {e}")
            st.markdown("Please ensure all psychology program dependencies are installed.")

if __name__ == "__main__":
    main()