from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from supabase import create_client
from google import genai
import os


# --------------------------------
# Load environment variables
# --------------------------------

load_dotenv()


# --------------------------------
# Flask application
# --------------------------------

app = Flask(__name__)


# --------------------------------
# Supabase connection
# --------------------------------

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)


# --------------------------------
# Gemini connection
# --------------------------------

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


# --------------------------------
# Home
# --------------------------------

@app.route("/")
def home():
    return "IoT Daily Intelligence Backend is running!"


# --------------------------------
# Receive ESP32 sensor data
# --------------------------------

@app.route("/sensor", methods=["POST"])
def sensor_data():

    data = request.get_json()

    print("Received sensor data:")
    print(data)

    supabase.table("sensor_readings").insert({
        "temperature": data["temperature"],
        "humidity": data["humidity"],
        "pressure": data["pressure"],
        "mq135": data["mq135"],
        "rain": data["rain"]
    }, returning="minimal").execute()

    return jsonify({
        "status": "success",
        "message": "Sensor data saved to Supabase"
    })


# --------------------------------
# Dashboard sensor data
# --------------------------------

@app.route("/dashboard")
def dashboard():

    result = supabase.table("sensor_readings") \
        .select("*") \
        .order("created_at", desc=True) \
        .limit(20) \
        .execute()

    return jsonify(result.data)


# --------------------------------
# Dashboard webpage
# --------------------------------

@app.route("/dashboard-ui")
def dashboard_ui():

    return render_template("dashboard.html")


# --------------------------------
# Gemini AI analysis
# --------------------------------

@app.route("/ai-analysis")
def ai_analysis():

    try:

        result = supabase.table("sensor_readings") \
            .select("*") \
            .order("created_at", desc=True) \
            .limit(20) \
            .execute()

        readings = result.data

        if not readings:

            return jsonify({
                "error": "No sensor data available"
            })

        latest = readings[0]

        prompt = f"""
You are an IoT environmental intelligence assistant.

Analyze these real sensor readings:

Temperature: {latest['temperature']} °C
Humidity: {latest['humidity']} %
Pressure: {latest['pressure']} hPa
MQ135 raw ADC value: {latest['mq135']}
Rain detected: {latest['rain']}

Give a short and simple environmental analysis.

Include:

1. Temperature
2. Humidity
3. Air quality
4. Rain condition
5. Overall observation

Important rules:

- The MQ135 value is a RAW ADC sensor reading.
- Do NOT treat the MQ135 value as AQI.
- Do NOT provide specific pollutant concentrations.
- Do NOT claim that the raw MQ135 value directly represents pollution level.
- Explain that calibration is required for accurate air-quality measurements.
- Do not invent measurements.
- Use only the values provided above.
"""

        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt
        )

        return jsonify({
            "analysis": response.text
        })

    except Exception as e:

        print("Gemini error:")
        print(e)

        return jsonify({
            "error": "Unable to generate AI analysis"
        }), 500


# --------------------------------
# Run Flask
# --------------------------------

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )