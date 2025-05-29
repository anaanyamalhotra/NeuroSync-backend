# Main FastAPI app

import streamlit as st

def main():
    st.title("Welcome to NeuroSync 🧠")
    st.markdown("""
        NeuroSync is a Cognitive Twin Intelligence Platform that:
        - Maps your cognitive-emotional state
        - Visualizes your neurotransmitter balance
        - Offers personalized game, scent, and music recommendations
        - Provides AI-powered journaling for reflection

        Use the sidebar to navigate through the app:
        - 🧬 Visualize your neuroprofile
        - 🪞 Reflect on your mood and thoughts
    """)

if __name__ == "__main__":
    main()
