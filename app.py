from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import os
import openai
import base64
from pydantic import BaseModel
import imghdr

load_dotenv()

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max

class Food(BaseModel):
    name: str
    calorie_count: int
    imageb64: str


def recognize_food(image_data, image_type, note="") -> Food:
    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        response_format=Food,
        messages=[
            {
                "role": "user",
                "content": [{
                        "type": "text",
                        "text": f"""
                                Analyze this food image and describe
                                what food is present and return the
                                name and number of calories in kcal.
                                NOTE: {note}
                                """
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{image_type};base64,{image_data}"
                        },
                    },
                ],
            }
        ],
    )
    food = response.choices[0].message.parsed
    food.imageb64 = f"data:image/{image_type};base64,{image_data}"
    return food


def calculate_next_meal_timeframe(bmr, calories_eaten):
    """
    Calculate the next meal timeframe in hours.
    """
    return calories_eaten / (bmr / 24) if calories_eaten > 0 else 0


@app.route("/")
def index():
    return render_template("index.html")


def is_image(file) -> bool:
    file.seek(0)
    file_type = imghdr.what(file)
    file.seek(0)
    return file_type is not None


@app.route("/upload-food", methods=["POST"])
def upload_food():
    if 'food-image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file, body_bmr, optional_note = (
        request.files['food-image'],
        int(request.form["body-bmr"]),
        request.form.get("optional-note")
    )
    
    if not is_image(file):
        return jsonify({'error': 'Uploaded file is not an image'}), 400

    base64_encoded_data = base64.b64encode(file.read()).decode('utf-8')

    food = recognize_food(base64_encoded_data, file.mimetype, note=optional_note)
    next_meal_time = calculate_next_meal_timeframe(body_bmr, food.calorie_count)

    return jsonify({
        "image64": food.imageb64,
        "name": food.name,
        "calories": food.calorie_count,
        "next_meal_time": next_meal_time
    })


if __name__ == "__main__":
    app.run(debug=True)
