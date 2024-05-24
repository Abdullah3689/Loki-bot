import pyaudio
import numpy as np
import pygame
import openai
import pyttsx3
import time
import os
import board
import busio
from adafruit_pca9685 import PCA9685
from PIL import Image
import speech_recognition as sr
from Adafruit_GPIO import SPI
from Adafruit_ILI9341 import ILI9341
import threading

# Initialize PyAudio
audio = pyaudio.PyAudio()

# Initialize pygame mixer for playing sound files
pygame.mixer.init()

# Initialize TTS engine
engine = pyttsx3.init()
engine.setProperty('voice', 'female')

# OpenAI API key
openai.api_key = "YOUR_OPENAI_API_KEY"

# Initialize I2C bus
i2c = busio.I2C(board.SCL, board.SDA)

# Initialize PCA9685
pwm = PCA9685(i2c)
pwm.frequency = 60

# Servo pulse lengths
servo_min = 150  # Min pulse length out of 4096
servo_max = 600  # Max pulse length out of 4096

# Function to move servo
def move_servo(channel, position):
    pwm.channels[channel].duty_cycle = int(position / 4096 * 65535)

# TFT display configuration
DC = 18
RST = 23
SPI_PORT = 0
SPI_DEVICE = 0

# Create TFT LCD display class
disp = ILI9341(DC, rst=RST, spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE, max_speed_hz=64000000))

# Initialize display
disp.begin()

# Function to play sound file
def play_sound(file_path):
    pygame.mixer.music.load(file_path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)

# Function to display emotion frames on TFT and move servos
def display_emotion_with_servo(emotion_folder, servo_positions):
    frames = sorted([f for f in os.listdir(emotion_folder) if f.endswith('.png') or f.endswith('.jpg')])
    
    if not frames:
        print(f"No image files found in {emotion_folder}")
        return

    for _ in range(2):  # Play each emotion twice
        for frame, positions in zip(frames, servo_positions):
            image = Image.open(os.path.join(emotion_folder, frame))
            image = image.resize((disp.width, disp.height))
            disp.display(image)
            move_servo(0, positions[0])
            move_servo(1, positions[1])
            time.sleep(0.1)

# Emotion functions with servo positions
def happy():
    servo_positions = [(servo_max, servo_max)] * 10 + [(servo_min, servo_min)] * 10
    display_emotion_with_servo('/home/mursalim/Emo/Code/emotions/happy', servo_positions)

def sad():
    servo_positions = [(servo_max, servo_min)] * 10 + [(servo_min, servo_min)] * 10
    display_emotion_with_servo('/home/mursalim/Emo/Code/emotions/sad', servo_positions)

def angry():
    servo_positions = [(servo_min, servo_max)] * 10 + [(servo_min, servo_min)] * 10
    display_emotion_with_servo('/home/mursalim/Emo/Code/emotions/angry', servo_positions)

def blink():
    servo_positions = [(servo_max // 2, servo_max // 2)] * 10 + [(servo_min, servo_min)] * 10
    display_emotion_with_servo('/home/mursalim/Emo/Code/emotions/blink', servo_positions)

def excited():
    servo_positions = [(servo_max, servo_max), (servo_min, servo_min)] * 5
    display_emotion_with_servo('/home/mursalim/Emo/Code/emotions/excited', servo_positions)

def dizzy():
    servo_positions = [(servo_max, servo_min), (servo_min, servo_max)] * 5
    display_emotion_with_servo('/home/mursalim/Emo/Code/emotions/dizzy', servo_positions)

def sleep():
    servo_positions = [(servo_min, servo_min)] * 20
    display_emotion_with_servo('/home/mursalim/Emo/Code/emotions/sleep', servo_positions)

def neutral():
    servo_positions = [(servo_max // 2, servo_max // 2)] * 10 + [(servo_min, servo_min)] * 10
    display_emotion_with_servo('/home/mursalim/Emo/Code/emotions/neutral', servo_positions)

def shush():
    play_sound('/home/mursalim/Emo/Code/emotions/shush.mp3')
    engine.say("Please be quiet.")
    engine.runAndWait()

# Function to record audio and analyze sound levels
def record_audio(duration=5, rate=44100, chunk=1024):
    stream = audio.open(format=pyaudio.paInt16, channels=1, rate=rate, input=True, frames_per_buffer=chunk)
    print("Recording...")
    frames = []

    for _ in range(0, int(rate / chunk * duration)):
        data = stream.read(chunk)
        frames.append(data)

    print("Finished recording.")
    stream.stop_stream()
    stream.close()

    audio_data = np.frombuffer(b''.join(frames), dtype=np.int16)
    rms = np.sqrt(np.mean(audio_data**2))

    return rms, b''.join(frames)

# Function to convert speech to text
def speech_to_text(audio_data, rate=44100):
    recognizer = sr.Recognizer()
    audio_file = sr.AudioData(audio_data, rate, 2)
    try:
        text = recognizer.recognize_google(audio_file)
        return text
    except sr.UnknownValueError:
        return None
    except sr.RequestError as e:
        print(f"Could not request results from Google Speech Recognition service; {e}")
        return None

# Function to generate response using ChatGPT 4 with emotion
def generate_response_with_emotion(user_input):
    messages = [
        {"role": "system", "content": "You are Loki, an interactive assistant. Respond with both an answer and an emotion such as happy, sad, angry, blink, excited, dizzy, or shush."},
        {"role": "user", "content": user_input}
    ]
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=messages
    )
    response_content = response["choices"][0]["message"]["content"]
    return response_content

# Function to provide voice feedback and display emotions
def provide_feedback(response_text, emotion_function):
    # Use threading to run emotion and speech concurrently
    emotion_thread = threading.Thread(target=emotion_function)
    emotion_thread.start()
    engine.say(response_text)
    engine.runAndWait()
    emotion_thread.join()

# Function to provide background feedback
def provide_background_feedback():
    engine.say("I am processing your request, please wait.")
    engine.runAndWait()

# Main function
def main():
    base_emotion_folder = '/home/mursalim/Emo/Code/emotions'
    shush_sound = os.path.join(base_emotion_folder, 'shush.mp3')
    
    emotion_functions = {
        "happy": happy,
        "sad": sad,
        "angry": angry,
        "blink": blink,
        "excited": excited,
        "dizzy": dizzy,
        "sleep": sleep,
        "neutral": neutral,
        "shush": shush
    }

    # Set the robot to neutral emotion initially
    neutral()

    last_interaction_time = time.time()
    sleep_mode = False

    def handle_interaction(user_question):
        provide_background_feedback()  # Provide background feedback during processing

        response_with_emotion = generate_response_with_emotion(user_question)
        print("ChatGPT response with emotion:", response_with_emotion)

        # Extract response and emotion from ChatGPT response
        if " [" in response_with_emotion:
            response_text, emotion = response_with_emotion.rsplit(" [", 1)
            response_text = response_text.strip()
            emotion = emotion.strip("] ").lower()
        else:
            response_text = response_with_emotion
            emotion = "neutral"

        if emotion not in emotion_functions:
            emotion = "neutral"

        print(f"Response: {response_text} Emotion: {emotion}")

        # Provide feedback with the response text only
        provide_feedback(response_text, emotion_functions[emotion])
        return time.time()

    while True:
        current_time = time.time()

        if not sleep_mode and current_time - last_interaction_time > 120:  # 2 minutes of inactivity
            print("No interaction for 2 minutes. Going to sleep.")
            sleep_mode = True
            threading.Thread(target=emotion_functions["sleep"]).start()

        rms, audio_data = record_audio()

        if sleep_mode:
            if rms > 5000:  # Loud noise in sleep mode
                print("Environment is too loud")
                emotion_functions["shush"]()
                last_interaction_time = current_time
                continue

            user_question = speech_to_text(audio_data)
            if user_question and "loki" in user_question.lower():
                sleep_mode = False
                last_interaction_time = handle_interaction(user_question)
                continue

        else:
            user_question = speech_to_text(audio_data)
            if user_question and "loki" in user_question.lower():
                last_interaction_time = handle_interaction(user_question)
            else:
                if not sleep_mode and current_time - last_interaction_time > 120:  # 2 minutes of inactivity
                    print("No interaction for 2 minutes. Going to sleep.")
                    sleep_mode = True
                    threading.Thread(target=emotion_functions["sleep"]).start()

        time.sleep(1)

if __name__ == "__main__":
    main()
