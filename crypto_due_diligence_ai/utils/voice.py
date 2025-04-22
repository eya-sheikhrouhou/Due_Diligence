import pyttsx3

def speak_answer(answer):
    engine = pyttsx3.init()
    engine.setProperty('rate', 160)
    engine.say(answer)
    engine.runAndWait()
