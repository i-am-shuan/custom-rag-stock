import streamlit as st
import sys
sys.path.append("./stock_analysis")
from stock_analysis_app import stock_analysis
from PIL import Image

image = Image.open('images/kb_friends.png')
st.image(image, caption='')

page_names_to_funcs = {
    "Stock Analysis": stock_analysis
}

demo_name = "Stock Analysis"
page_names_to_funcs[demo_name]()
