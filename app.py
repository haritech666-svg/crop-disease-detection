import torch
import json
import os
import io
import base64
import warnings


warnings.filterwarnings("ignore")

from torchvision import models, transforms
from PIL import Image
from groq import Groq
from flask import Flask, request, render_template, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

# ──────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────

UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXT   = {"jpg", "jpeg", "png"}

app = Flask(__name__)
CORS(app)
app.config["UPLOAD_FOLDER"]      = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ──────────────────────────────────────────
# 1. Load class names
# ──────────────────────────────────────────
with open("class_names.json", "r") as f:
    CLASS_NAMES = json.load(f)

# ──────────────────────────────────────────
# 2. Load model
# ──────────────────────────────────────────
ml_model = models.mobilenet_v2(weights=None)
ml_model.classifier[1] = torch.nn.Sequential(
    torch.nn.Dropout(0.2),
    torch.nn.Linear(ml_model.classifier[1].in_features, 38)
)

ckpt = torch.load(
    "model/mobilenetv2_plant.pth",
    map_location=torch.device("cpu")
)

if isinstance(ckpt, dict) and "state_dict" in ckpt:
    ml_model.load_state_dict(ckpt["state_dict"])
elif isinstance(ckpt, dict) and "model_state_dict" in ckpt:
    ml_model.load_state_dict(ckpt["model_state_dict"])
else:
    ml_model.load_state_dict(ckpt)

ml_model.eval()
print("✅ Model loaded successfully!")

# ──────────────────────────────────────────
# 3. Image transform
# ──────────────────────────────────────────
tf = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225])
])

# ──────────────────────────────────────────
# 4. Predict
# ──────────────────────────────────────────
def predict_image(img):
    tensor = tf(img).unsqueeze(0)
    with torch.no_grad():
        out   = ml_model(tensor)
        probs = torch.softmax(out, dim=1)[0]
        idx   = probs.argmax().item()

    raw        = CLASS_NAMES[idx]
    confidence = round(float(probs[idx]) * 100, 2)
    parts      = raw.split("___")
    plant      = parts[0].replace("_", " ").strip()
    disease    = parts[1].replace("_", " ").strip() if len(parts) > 1 else "Unknown"
    return plant, disease, confidence

# ──────────────────────────────────────────
# 5. Groq LLM
# ──────────────────────────────────────────
def explain_disease(plant, disease, confidence):
    try:
        prompt = f"""You are an expert agricultural scientist. AI detected on a farmer's leaf image:
- Plant: {plant}
- Disease: {disease}
- Confidence: {confidence}%

Give response in exactly these 5 sections:
1. What is this disease?
2. What causes it?
3. How to treat it? (3 steps)
4. How to prevent it? (2 tips)
5. Is it dangerous?

Use very simple language."""

        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a helpful agricultural expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=600
        )
        return resp.choices[0].message.content

    except Exception as e:
        return (f"Disease detected: {disease} on {plant}. Please consult an expert."
                f"with {confidence}% confidence. "
                f"Please consult an agricultural expert for treatment.")

# ──────────────────────────────────────────
# 6. Routes
# ──────────────────────────────────────────
def allowed(fname):
    return ("." in fname and
            fname.rsplit(".", 1)[1].lower() in ALLOWED_EXT)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/predict", methods=["POST", "OPTIONS"])
def predict():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    try:
        print("📥 Received prediction request")

        if "file" not in request.files:
            print("❌ No file in request")
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["file"]

        if file.filename == "":
            print("❌ Empty filename")
            return jsonify({"error": "No file selected"}), 400

        if not allowed(file.filename):
            print("❌ Invalid file type")
            return jsonify({"error": "Use JPG or PNG only"}), 400

        img_bytes = file.read()
        print(f"📸 File size: {len(img_bytes)} bytes")

        if len(img_bytes) == 0:
            return jsonify({"error": "Empty file"}), 400

        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

        filename  = secure_filename(file.filename)
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        img.save(save_path)
        print(f"💾 Saved to {save_path}")

        # ML prediction
        plant, disease, confidence = predict_image(img)
        print(f"✅ Prediction: {plant} | {disease} | {confidence}%")

        # LLM explanation
        explanation = explain_disease(plant, disease, confidence)
        print("✅ LLM explanation done!")

        # Encode image
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

        return jsonify({
            "plant":       plant,
            "disease":     disease,
            "confidence":  confidence,
            "explanation": explanation,
            "image":       img_b64
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ Server error: {e}")
        return jsonify({"error": str(e)}), 500

# ──────────────────────────────────────────
# 7. Run
# ──────────────────────────────────────────
if __name__ == "__main__":
    print("🌿 Crop Disease Detector starting...")
    print("🌐 Open: http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)