import streamlit as st
from streamlit_mic_recorder import mic_recorder
from pymongo import MongoClient
import base64
from st_paywall import add_auth
import datetime
from PIL import Image
import io
import uuid

if 'session_id' not in st.session_state:
    st.session_state.session_id = f"ST_ASSTT_{str(uuid.uuid4())}"

# Add authentication
add_auth(required=True)

# Sidebar with subscription status and user email
with st.sidebar:
    st.write(f"Subscription status: {'Subscribed' if st.session_state.user_subscribed else 'Not subscribed'}")
    st.write(f"{st.session_state.email}")

@st.experimental_fragment(run_every=30)
def fragment():
    print("this will happen every 30 seconds")

# MongoDB URI and connection
MONGO_URI = st.secrets["mongo_uri"]
client = MongoClient(MONGO_URI)
db = client['audio_database']
collection = db['recordings']

def save_audio_to_mongodb(audio_bytes, email):
    # Encode the audio bytes to base64
    encoded_audio = base64.b64encode(audio_bytes).decode('utf-8')
    # Get current datetime
    current_datetime = datetime.datetime.utcnow()
    # Save to MongoDB with email and datetime
    
    collection.insert_one({
        "audio_data": encoded_audio,
        "email": email,
        "status": "born",
        "type": "audio",
        "session_id": st.session_state.session_id,
        "datetime": current_datetime
    })
    st.toast("Audio saved, It's available at the Storage")

def callback():
    if st.session_state.my_recorder_output:
        audio_bytes = st.session_state.my_recorder_output['bytes']
        st.audio(audio_bytes)
        save_audio_to_mongodb(audio_bytes, st.session_state.email)

def save_picture_to_mongodb(picture, email):
    # Read image file buffer as a PIL Image
    img = Image.open(picture)
    # Convert PIL Image to bytes
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    # Encode the picture bytes to base64
    encoded_picture = base64.b64encode(img_byte_arr).decode('utf-8')
    # Get current datetime
    current_datetime = datetime.datetime.utcnow()
    # Save to MongoDB with email and datetime
    collection.insert_one({
        "picture_data": encoded_picture,
        "email": email,
        "status": "born",
        "type": "picture",
        "session_id": st.session_state.session_id,
        "datetime": current_datetime
    })
    st.toast("Picture saved, It's available at the Storage")


img_file_buffer = st.camera_input("Take a picture", key="camera_input",label_visibility='hidden')
if img_file_buffer:
    save_picture_to_mongodb(img_file_buffer, st.session_state.email)

with st.container():
    audio = mic_recorder(
        stop_prompt="STOP AUDIO RECORD⏺️",
        start_prompt="START AUDIO RECOROD🔴",
        just_once=False,
        use_container_width=True,
        callback=callback,
        args=(),
        kwargs={},
        key="my_recorder",
    )
    

