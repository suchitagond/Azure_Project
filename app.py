import os
import threading
import requests
from flask import Flask, render_template, request, jsonify
from azure.cognitiveservices.speech import SpeechConfig, SpeechRecognizer, SpeechSynthesizer, AudioConfig, SpeechRecognitionResult
import azure.cognitiveservices.speech as speechsdk
from msrest.authentication import CognitiveServicesCredentials
from azure.core.credentials import AzureKeyCredential
from azure.ai.textanalytics import TextAnalyticsClient
import pyttsx3
from pydub import AudioSegment

# Initialize Flask app
app = Flask(__name__)

# Azure credentials (set these to your own values)
key = "9CTd2qVrUkZkvTC9AB44vqrsSYFponfJm8Fi6KCZCxoZuuOK96KBJQQJ99BAACYeBjFXJ3w3AAAEACOGH83l"
region = "eastus"
endpoint = "https://ai-102-project.cognitiveservices.azure.com/"

# Serve the front-end HTML page
@app.route('/')
def index():
    return render_template('index.html')

# Initialize the TTS engine once
engine = pyttsx3.init()

# Function to read text aloud
def text_to_speech2(text):
    def speak():
        engine.stop()  # Stop any running speech
        engine.say(text)
        engine.runAndWait()

    # Run the speech in a separate thread to avoid blocking the main thread
    speech_thread = threading.Thread(target=speak)
    speech_thread.start()

# Function to read text aloud
def text_to_speech(text_to_read):
    speech_config = SpeechConfig(subscription=key, region=region)
    speech_config.speech_synthesis_voice_name = "en-US-AriaNeural"
    synthesizer = SpeechSynthesizer(speech_config=speech_config)

    # Convert text to speech
    synthesizer.speak_text_async(text_to_read)

@app.route('/blind')
def blind():
    return render_template('blind.html')

@app.route('/deaf')
def deaf():
    return render_template('deaf.html')

@app.route('/mute')
def mute():
    return render_template('mute.html')

# Serve static files (JavaScript, CSS, etc.)
@app.route('/static/<path:path>')
def static_files(path):
    return app.send_static_file(path)

# Route for the Speech Synthesis Page
@app.route('/speech-synthesis')
def speech_synthesis():
    return render_template('syn.html')

# Route for the Predefined Phrases Page
@app.route('/predefined-phrases')
def predefined_phrases():
    return render_template('pre.html')

# Route for the Image Analysis (OCR + Description)
@app.route('/image_to_speech')
def image_to_speech():
    return render_template('its.html')

# Route for Text-to-Speech Page
@app.route('/text_to_speech_page')
def text_to_speech_page():
    return render_template('tts.html')

# Route for Speech-to-text Page
@app.route('/speech_to_text')
def speech_to_text():
    return render_template('stt.html')

@app.route('/translate')
def translate_page():
    return render_template('tra.html')


# Predefined Phrases API
@app.route('/get-predefined-phrases', methods=['GET'])
def get_predefined_phrases():
    phrases = [
        "Hello, how are you?", "Good morning!", "Good afternoon!", "Good evening!", "It's nice to meet you.",
        "How can I help you?", "How are you doing today?", "I hope you're having a great day.",
        "Thank you very much.", "I appreciate your help.", "I'm sorry.", "Please forgive me.", "No problem.",
        "That's okay.", "You're welcome.", "Congratulations!", "Best wishes!", "Take care.", "Have a good day.",
        "Can you help me with this?", "I need assistance.", "Could you repeat that, please?", "Can you explain that again?",
        "Can you give me more details?", "Could you speak slowly?", "Can I ask you a question?", "Please wait a moment.",
        "Can I get some water?", "Could you bring me my phone?", "Where is the nearest restroom?", 
        "How do I get to the nearest hospital?", "Can you show me the way to the bus stop?", "What time is it?", 
        "Where can I find a taxi?", "What is your name?", "Nice to meet you.", "Do you have a moment to talk?", 
        "Thank you for your time.", "It was nice talking to you.", "See you soon.", "Goodbye!", 
        "Can we schedule a meeting?", "What does this mean?", "I don't understand.", "Could you help me translate this?", 
        "I'm feeling unwell.", "Can you call for help?", "Is there a doctor nearby?", "I don't know.", 
        "Let's talk about it later.", "I need some time to think."
    ]
    return jsonify({"phrases": phrases})

# Image Analysis (OCR + Description) using Azure Computer Vision API
def analyze_image(image_data):
    ocr_url = f"{endpoint}/vision/v3.2/ocr"
    describe_url = f"{endpoint}/vision/v3.2/analyze?visualFeatures=Description"

    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/octet-stream",
    }

    analysis_result = {"description": "", "text": ""}

    try:
        # Request to describe the image
        describe_response = requests.post(describe_url, headers=headers, data=image_data)
        describe_response.raise_for_status()
        description_result = describe_response.json()
        analysis_result["description"] = description_result.get("description", {}).get("captions", [{}])[0].get("text", "No description available.")

        # Request for OCR (text extraction)
        ocr_response = requests.post(ocr_url, headers=headers, data=image_data)
        ocr_response.raise_for_status()
        ocr_result = ocr_response.json()

        # Extract text from OCR results
        lines = []
        for region in ocr_result.get("regions", []):
            for line in region.get("lines", []):
                line_text = " ".join([word["text"] for word in line.get("words", [])])
                lines.append(line_text)
        analysis_result["text"] = " ".join(lines) if lines else "No text found in the image."

    except requests.exceptions.RequestException as e:
        return f"Error: Unable to connect to the Azure service. Details: {str(e)}"
    except KeyError as e:
        return f"Error: Unable to extract or describe the image. Details: {str(e)}"

    return analysis_result

@app.route("/process-input", methods=["POST"])
def process_input():
    try:
        input_data = request.json
        input_type = input_data.get('input_type')  # 'audio' or 'text'
        user_input = input_data.get('user_input')  # Actual input data (audio file or text)

        if input_type == 'text':
            text_to_speech(user_input)  # Convert the text back to speech
            response = {"message": user_input, "status": "success"}
            return jsonify(response)
        else:
            return jsonify({"error": "Invalid input type."}), 400
    except Exception as e:
        print(f"Error: {str(e)}")  # Log the error to the console
        return jsonify({"error": str(e)}), 500

# Route to handle image analysis
@app.route('/api/analyze_image', methods=['POST'])
def analyze_image_api():
    """Process image and return description or text."""
    image_file = request.files.get('image')

    if not image_file:
        error_message = "No image file uploaded."
        text_to_speech2(error_message)
        return jsonify({"error": error_message}), 400

    image_data = image_file.read()
    analysis_result = analyze_image(image_data)
    if "error" in analysis_result:
        text_to_speech2(analysis_result["error"])
        return jsonify({"error": analysis_result["error"]}), 400

    text_to_speech2(analysis_result)
    return jsonify({"result": analysis_result})

# Special route for TTS playback (custom user-provided text)
@app.route('/api/custom_text_to_speech', methods=['POST'])
def custom_text_to_speech_api():
    """Converts custom user-provided text to speech."""
    text = request.json.get('text', '').strip()

    if not text:
        error_message = "No text provided for speech."
        text_to_speech(error_message)
        return jsonify({"error": error_message}), 400

    text_to_speech(text)
    return jsonify({"status": "success", "message": "Text read aloud successfully."})

def convert_mp3_to_wav(mp3_path, wav_path):
    """
    Convert an MP3 file to WAV format using pydub.
    """
    try:
        # Load MP3 file
        audio = AudioSegment.from_mp3(mp3_path)
        # Export as WAV
        audio.export(wav_path, format="wav")
        return True
    except Exception as e:
        print(f"Error during MP3 to WAV conversion: {e}")
        return False

@app.route('/speech_to_text_fun', methods=['POST'])
def speech_to_text_fun():
    """
    Convert speech from an uploaded audio file to text.
    """
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files['audio']

    if not audio_file:
        return jsonify({"error": "No audio file provided"}), 400

    try:
        # Save the uploaded MP3 file temporarily
        temp_mp3_path = "temp_audio.mp3"
        temp_wav_path = "temp_audio.wav"
        audio_file.save(temp_mp3_path)

        # Convert MP3 to WAV
        if not convert_mp3_to_wav(temp_mp3_path, temp_wav_path):
            return jsonify({"error": "Failed to convert MP3 to WAV"}), 500

        speech_config = SpeechConfig(subscription=key, region=region)

        # Create audio configuration using the WAV file
        audio_config = speechsdk.audio.AudioConfig(filename=temp_wav_path)

        # Create a speech recognizer with the audio configuration
        recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

        # Perform speech recognition
        result = recognizer.recognize_once()

        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            recognized_text = result.text
        elif result.reason == speechsdk.ResultReason.NoMatch:
            recognized_text = "No speech recognized."
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = result.cancellation_details
            recognized_text = f"Speech Recognition canceled: {cancellation_details.error_details}"
        else:
            recognized_text = "An unknown error occurred during speech recognition."

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
    finally:
        # Cleanup temporary files
        for temp_file in [temp_mp3_path, temp_wav_path]:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except PermissionError:
                pass

    return jsonify({"text": recognized_text})

# Route for Text Translation
@app.route('/api/translate_text', methods=['POST'])
def translate_text_api():
    """
    Translates text to the specified target language.
    """
    if not request.is_json:
        return jsonify({"error": "Invalid Content-Type, expected application/json"}), 415
    
    data = request.json
    text = data.get('text', '').strip()
    target_language = data.get('target_language', 'en').strip()

    if not text:
        return jsonify({"error": "No text provided for translation"}), 400
    if not target_language:
        return jsonify({"error": "No target language provided"}), 400

    # Azure Translator API URL
    translate_url = f"https://api.cognitive.microsofttranslator.com/translate?api-version=3.0&to={target_language}"

    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Ocp-Apim-Subscription-Region": region,
        "Content-Type": "application/json"
    }

    body = [{"text": text}]

    try:
        # Make a request to the Azure API
        response = requests.post(translate_url, headers=headers, json=body)
        response.raise_for_status()  # Will raise an error for 4xx/5xx responses
        translation = response.json()

        translated_text = translation[0]['translations'][0]['text']
        return jsonify({"translated_text": translated_text})

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Error connecting to translation service: {str(e)}"}), 500
    except KeyError:
        return jsonify({"error": "Error parsing the translation response."}), 500

if __name__ == '__main__':
    app.run(debug=True)
