#!/usr/bin/env python3
"""
NEXUS AI Assistant - Backend API (Flask)
Run this server separately from the frontend.
"""

import os
import datetime
import time
import threading
import re
from collections import deque
from flask import Flask, request, jsonify
from flask_cors import CORS  # to allow frontend from different origin

# Optional imports
try:
    import openai
except ImportError:
    openai = None

try:
    import wikipedia
except ImportError:
    wikipedia = None

try:
    import requests
except ImportError:
    requests = None

try:
    from dateutil import parser as date_parser
    from dateutil.relativedelta import relativedelta
except ImportError:
    date_parser = None
    relativedelta = None

# ================== CONFIGURATION ==================
NAME = "NEXUS"
# Use environment variable for API key (safer)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "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")
OPENAI_MODEL = "gpt-3.5-turbo"
USE_OPENAI = bool(openai and OPENAI_API_KEY and OPENAI_API_KEY != "your-openai-api-key-here")

if USE_OPENAI:
    openai.api_key = OPENAI_API_KEY

# Memory (global – for demo; in production use per‑user sessions)
MEMORY_SIZE = 10
memory = deque(maxlen=MEMORY_SIZE)

# Reminders (global – simplified)
reminders = []

app = Flask(__name__)
CORS(app)  # allow all origins (for development; restrict in production)

# ================== HELPER FUNCTIONS ==================
def log_interaction(user_input, response):
    memory.append({"user": user_input, "assistant": response})

def get_current_time():
    return datetime.datetime.now().strftime("%I:%M %p on %A, %B %d, %Y")

def evaluate_math(expr):
    allowed = re.compile(r'^[0-9+\-*/().\s]+$')
    if allowed.match(expr):
        try:
            result = eval(expr)
            return f"The result is: {result}"
        except Exception as e:
            return f"Sorry, I couldn't compute that: {e}"
    else:
        return "Expression contains invalid characters."

def search_wikipedia(query):
    if wikipedia is None:
        return "Wikipedia module not installed."
    try:
        summary = wikipedia.summary(query, sentences=2)
        page = wikipedia.page(query)
        return f"{summary}\n\nRead more: {page.url}"
    except wikipedia.exceptions.DisambiguationError as e:
        return f"Multiple results found: {', '.join(e.options[:5])}. Please be more specific."
    except wikipedia.exceptions.PageError:
        return "No Wikipedia page found for that query."
    except Exception as e:
        return f"Error searching Wikipedia: {e}"

def get_weather(city):
    if requests is None:
        return "Requests module not installed."
    api_key = "YOUR_OPENWEATHERMAP_API_KEY"  # replace with your key
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    try:
        resp = requests.get(url)
        data = resp.json()
        if data.get("cod") != 200:
            return f"Weather error: {data.get('message', 'unknown')}"
        main = data["main"]
        weather = data["weather"][0]
        return f"Weather in {city}: {weather['description']}, temperature {main['temp']}°C, feels like {main['feels_like']}°C."
    except Exception as e:
        return f"Could not fetch weather: {e}"

def set_reminder(text):
    if date_parser is None or relativedelta is None:
        return "Date parsing modules not installed."
    patterns = [
        (r"in (\d+) minutes?", "minutes"),
        (r"in (\d+) hours?", "hours"),
        (r"in (\d+) days?", "days"),
        (r"tomorrow", "tomorrow"),
    ]
    reminder_time = None
    now = datetime.datetime.now()
    for pattern, unit in patterns:
        match = re.search(pattern, text)
        if match:
            if unit == "minutes":
                delta = int(match.group(1))
                reminder_time = now + datetime.timedelta(minutes=delta)
                break
            elif unit == "hours":
                delta = int(match.group(1))
                reminder_time = now + datetime.timedelta(hours=delta)
                break
            elif unit == "days":
                delta = int(match.group(1))
                reminder_time = now + datetime.timedelta(days=delta)
                break
            elif unit == "tomorrow":
                reminder_time = now + datetime.timedelta(days=1)
                reminder_time = reminder_time.replace(hour=9, minute=0, second=0)
                break
    if reminder_time is None:
        return "Sorry, I couldn't understand when to remind you. Try 'in X minutes/hours/days' or 'tomorrow'."

    task = re.sub(r"(remind me to|remind me|to|in \d+ minutes?|in \d+ hours?|in \d+ days?|tomorrow)", "", text, flags=re.IGNORECASE).strip()
    if not task:
        task = "do something"
    reminders.append((reminder_time, task))
    # Background thread to check reminders (simplified)
    def reminder_worker():
        while True:
            now = datetime.datetime.now()
            for rt, t in reminders[:]:
                if now >= rt:
                    print(f"\n[REMINDER] {t}")  # would need to push to user
                    reminders.remove((rt, t))
            time.sleep(30)
    threading.Thread(target=reminder_worker, daemon=True).start()
    return f"Reminder set for {reminder_time.strftime('%I:%M %p on %B %d')}: {task}"

def call_gpt(prompt):
    if not USE_OPENAI:
        return None
    try:
        messages = [
            {"role": "system", "content": f"You are {NAME}, a helpful AI assistant. Answer concisely and accurately."}
        ]
        for item in list(memory)[-3:]:
            messages.append({"role": "user", "content": item["user"]})
            messages.append({"role": "assistant", "content": item["assistant"]})
        messages.append({"role": "user", "content": prompt})
        response = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=messages,
            max_tokens=250,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[OpenAI error: {e}]")
        return None

def nexus_response(user_input):
    lower = user_input.lower().strip()
    if lower in ["exit", "quit", "bye", "goodbye"]:
        return "Goodbye! Have a great day."
    if re.search(r"time|date|what day|current", lower):
        return f"It's {get_current_time()}."
    if re.search(r"^[\d+\-*/().\s]+$", user_input) and any(op in user_input for op in "+-*/"):
        return evaluate_math(user_input)
    if lower.startswith("wiki ") or lower.startswith("wikipedia "):
        query = user_input.split(maxsplit=1)[1]
        return search_wikipedia(query)
    if lower.startswith("weather in "):
        city = user_input[11:].strip()
        return get_weather(city)
    if lower.startswith("remind me "):
        return set_reminder(user_input)
    if lower in ["help", "what can you do"]:
        return (
            f"I am {NAME}, your AI assistant. I can:\n"
            "- Answer general questions (if OpenAI is connected)\n"
            "- Perform calculations (e.g., '45 * 3 + 2')\n"
            "- Tell the current time/date\n"
            "- Search Wikipedia (e.g., 'wiki Python programming')\n"
            "- Give weather (e.g., 'weather in London')\n"
            "- Set reminders (e.g., 'remind me to call John in 10 minutes')\n"
            "- Remember our conversation\n"
            "Just type your request!"
        )
    if USE_OPENAI:
        gpt_reply = call_gpt(user_input)
        if gpt_reply:
            return gpt_reply
    return (
        f"I'm not sure how to answer that. You can ask for help, set a reminder, search Wikipedia, "
        f"or ask about the time/weather. If you have an OpenAI API key, I can answer more freely."
    )

# ================== API ROUTE ==================
@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json()
    user_input = data.get('message', '')
    if not user_input:
        return jsonify({'error': 'No message provided'}), 400
    response = nexus_response(user_input)
    log_interaction(user_input, response)
    return jsonify({'response': response})

if __name__ == '__main__':
    # Run on all available IPs, port 5000
    app.run(debug=True, host='0.0.0.0', port=5000)