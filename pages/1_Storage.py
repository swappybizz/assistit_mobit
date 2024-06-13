import streamlit as st
from pymongo import MongoClient
import base64
from st_paywall import add_auth
import datetime
import speech_recognition as sr

from openai import OpenAI
from PIL import Image
import io, os


st.set_page_config(layout="wide")
# add state for zip file
if 'form_filled_zip' not in st.session_state:
    st.session_state.form_filled_zip = None

# Add authentication
add_auth(required=True)

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



def transcribe_audio(record):
    audio_data = base64.b64decode(record['audio_data'])
    recognizer = sr.Recognizer()

    with sr.AudioFile(io.BytesIO(audio_data)) as source:
        audio = recognizer.record(source)
    try:
        transcription = recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        transcription = "Audio not clear"
    except sr.RequestError:
        transcription = "Service unavailable"
    return transcription


# MongoDB URI and connection
MONGO_URI = st.secrets["mongo_uri"]
client = MongoClient(MONGO_URI)
db = client['audio_database']
collection = db['recordings']

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def get_form(uploaded_file, save, selected_schema):
    pass

def get_audio_from_mongodb(email):
    return collection.find({"email": email, "type": "audio"})

def get_picture_from_mongodb(email):
    return collection.find({"email": email, "type": "picture"})

def delete_record(record_id):
    collection.delete_one({"_id": record_id})
    

tab1, tab2 = st.tabs(["Process", "Storage"])

with tab2:
    with st.sidebar:
        "upload files"
        upload_images = st.file_uploader("Choose files", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
        if upload_images:
            # save to database
            for image in upload_images:
                save_picture_to_mongodb(image, st.session_state.email)


    # Sidebar with subscription status and user email
    with st.sidebar:
        st.write(f"Subscription status: {'Subscribed' if st.session_state.user_subscribed else 'Not subscribed'}")
        st.write(f"{st.session_state.email}")

    # Fetch and display audio files
    "Saved Audio Recordings"
    audio_records = get_audio_from_mongodb(st.session_state.email)
    for record in audio_records:
        with st.expander(f"Audio saved on: {record['datetime']}"):
            audio_data = base64.b64decode(record['audio_data'])
            st.audio(audio_data)
            if st.button("Delete", key=f"delete_audio_{record['_id']}"):
                delete_record(record['_id'])
                st.rerun()

    # Fetch and display pictures
    "Saved Pictures"
    picture_records = get_picture_from_mongodb(st.session_state.email)
    for record in picture_records:
        with st.expander(f"Picture saved on: {record['datetime']}"):
            picture_data = base64.b64decode(record['picture_data'])
            image = Image.open(io.BytesIO(picture_data))
            st.image(image)
            if st.button("Delete", key=f"delete_picture_{record['_id']}"):
                delete_record(record['_id'])
                st.rerun()
    


with tab1:
    with st.form(key="form"):
        col1, col2 = st.columns([1, 1])
        with col1:
            uploaded_files = st.file_uploader("Choose a file", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
            save = st.checkbox("Save")
            selected_schema = st.multiselect("Select from previous schemas", ["Schema 1", "Schema 2"])
            selected_agent = st.selectbox("Select Agent", ["Agent 1", "Agent 2"])
        
        with col2:
            audio_records = get_audio_from_mongodb(st.session_state.get('email', 'test@example.com'))
            audio_selections = {}
            for record in reversed(list(audio_records)):
                with st.expander(f"Audio saved on: {record['datetime']}"):
                    audio_data = base64.b64decode(record['audio_data'])
                    st.audio(audio_data)
                    audio_selections[record['_id']] = st.checkbox("Select", key=f"audio_{record['_id']}")


            picture_records = get_picture_from_mongodb(st.session_state.get('email', 'test@example.com'))
            picture_selections = {}
            for record in reversed(list(picture_records)):
                with st.expander(f"Picture saved on: {record['datetime']}"):
                    picture_data = base64.b64decode(record['picture_data'])
                    image = Image.open(io.BytesIO(picture_data))
                    st.image(image)
                    picture_selections[record['_id']] = st.checkbox("Select", key=f"picture_{record['_id']}")

        form_submitted = st.form_submit_button("Submit", use_container_width=True)
        if form_submitted:
            # create an empty folder named schemas, delete one if already exists with its contents
            if os.path.exists("schemas"):
                for file in os.listdir("schemas"):
                    os.remove(f"schemas/{file}")
                os.rmdir("schemas")
            os.mkdir("schemas")
            if os.path.exists("selections"):
                for file in os.listdir("selections"):
                    os.remove(f"selections/{file}")
                os.rmdir("selections")
            os.mkdir("selections")
            
            for idx,uploaded_file in enumerate(uploaded_files):
                # returns a BytesIO object, convert to image and save a temp file
                
                # delete previous temp if exists
                if os.path.exists(f"temp_up_load_{idx}.png"):
                    os.remove(f"temp_up_load_{idx}.png")
                
                image = Image.open(uploaded_file)
                # save as a temp png file in the schemas folder
                image.save(f"schemas/temp_up_load_{idx}.png")
            selected_audio_ids = [record_id for record_id, selected in audio_selections.items() if selected]
            # get sound data for selected audio
            audio_transcripts = []
            
            for id in selected_audio_ids:
                audio_data = collection.find_one({"_id": id})
                # st.audio(base64.b64decode(audio_data['audio_data']), format='audio/wav')
                # save as a temp wav file
                with open("temp.wav", "wb") as f:
                    f.write(base64.b64decode(audio_data['audio_data']))
                    
                # st.audio("temp.wav", format='audio/wav')
                client = OpenAI(api_key=st.secrets["openai_api_key"])
                with open("temp.wav", "rb") as f:
                    trans = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=f,
                        response_format="text"
                    )
                audio_transcripts.append(trans)
                #close and remove temp file
                os.remove("temp.wav")
            with st.container():
                "Transcripts for processing"
                f"{audio_transcripts}"
                
            audio_transcript_string = "\n".join(audio_transcripts)
                
            # # print(selected_audio_ids)
            
            
            # # # Get selected pictures, save them as png in the selections folder
            selected_picture_ids = [record_id for record_id, selected in picture_selections.items() if selected]
            for idx, id in enumerate(selected_picture_ids):
                picture_data = collection.find_one({"_id": id})
                image = Image.open(io.BytesIO(base64.b64decode(picture_data['picture_data'])))
                image.save(f"selections/selected_picture_{idx}.png")
                
            
            
            
            prompt = """
            You have been provided with Images and Transcripts of Audio that you will use to fill up a Form.
            The form has been provided to you as an image.
            You will use the details from the images and transcripts to fill up the form.
            Assume every Form field as mandatory. If there is contradicting evidence, write 'Contradicting Evidence,[short details]'.
            You will leave the fields blank where the information is not available.
            """
            
            pmt_msgs = [
                {"role": "system", "content": "You are a form filler. You only respond with markdowns"},
                {"role": "user", "content": prompt},
            ]
            for image in os.listdir("schemas"):
                pmt_msgs.append({"role": "user", "content": [
                    {"type": "image_url", "image_url":
                        {"url": f"data:image/png;base64,{encode_image(f'schemas/{image}')}"}}
                ]})
                

            pmt_msgs.append({"role": "user", "content": "These are the data points that you can use \n Audio Transcripts:"})
            pmt_msgs.append({"role": "user", "content": audio_transcript_string})
            pmt_msgs.append({"role": "user", "content": " Use these Images to fill the form:"})

            for image in os.listdir("selections"):
                pmt_msgs.append({"role": "user", "content": [
                    {"type": "image_url", "image_url":
                        {"url": f"data:image/png;base64,{encode_image(f'selections/{image}')}"}}
                ]})
                
            pmt_msgs.append({
                "role": "user", 
                "content": "Please fill up the form with the data points provided. You will return only one combined single filled form. Add no comments, information or any other details. The form should be in the same format as the Form provided."
            })
            # print(pmt_msgs)
            client = OpenAI(api_key=st.secrets["openai_api_key"])
            completion = client.chat.completions.create(
                model="gpt-4o",
                messages=pmt_msgs,
            )
            
            st.write("Form filled by AI:")
            st.success("Remember to validate and improve the Form Filler. AI can make mistakes. Keep Your refrences handy")
            st.code(completion.choices[0].message.content)
            
            
            
            
            
            
            # if completion.choices[0].message.content:
            #     with st.expander("Download as ISOEnsureSets"):

            #         # Create a zip file
            #         zip_file_path = "form_filled.zip"
            #         with zipfile.ZipFile(zip_file_path, "w") as zipf:
            #             # Add the form filled text file
            #             with open("form_filled.txt", "w") as f:
            #                 f.write(completion.choices[0].message.content)
            #             zipf.write("form_filled.txt")
            #             os.remove("form_filled.txt")
                        
            #             # Add schemas folder
            #             for image in os.listdir("schemas"):
            #                 zipf.write(f"schemas/{image}")

            #             # Add selections folder
            #             for image in os.listdir("selections"):
            #                 zipf.write(f"selections/{image}")

            #             # Add audio transcripts
            #             with open("audio_transcripts.txt", "w") as f:
            #                 f.write(audio_transcript_string)
            #             zipf.write("audio_transcripts.txt")
            #             os.remove("audio_transcripts.txt")

            #         # Store the zip file in session state
            #         with open(zip_file_path, "rb") as f:
            #             if 'form_filled_zip' in st.session_state:
            #                 del st.session_state["form_filled_zip"]
                        
            #             st.session_state["form_filled_zip"] = f.read()

            #         # Remove the zip file from the file system
            #         os.remove(zip_file_path)

            
            # with st.expander("Improve Form"):
            #     "validate and imporve submission"
            #     "Download Finalised form"
        
    #        
    
# NOTES
    
    #     messages_pmt = [
    #     {"role": "system", "content": "You are a documenter. You only respond with documents"},
    #     {"role": "user", "content": prompt},
    # ]
    
    # for link in links:
    #     messages_pmt.append({"role": "user", "content": [
    #         {"type": "image_url", "image_url": {"url": link}}
    #     ]}) 

    # print("§§§§ $$$ CAUTION: A DOC GEN COSTING CALL#### IS BEING MADE $$$ §§§§")

    # client = OpenAI(api_key=st.secrets["openai_api_key"])
    # completion = client.chat.completions.create(
    #     model="gpt-4o",
    #     messages=messages_pmt,
    # )
    
    


# audio_file = open("/path/to/file/speech.mp3", "rb")
# following input file types are supported: mp3, mp4, mpeg, mpga, m4a, wav, and webm.
# transcription = client.audio.transcriptions.create(
#   model="whisper-1", 
#   file=audio_file, 
#   response_format="text"
# )
# print(transcription.text)