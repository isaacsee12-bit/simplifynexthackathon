import os
import sys
import json
from fastapi.testclient import TestClient

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

client = TestClient(app)

def test_file(file_path):
    if not os.path.exists(file_path):
        return {"error": "File not found"}
    
    file_name = os.path.basename(file_path)
    
    if file_name.endswith('.jpg'):
        with open(file_path, "rb") as f:
            response = client.post("/api/analyze/image", files={"file": (file_name, f, "image/jpeg")})
    elif file_name.endswith('.txt'):
        with open(file_path, "r", encoding="utf-8") as f:
            text_content = f.read()
            payload = {
                "text": text_content,
                "check_ai_generated": True,
                "check_scam": True,
                "check_claims": True
            }
            response = client.post("/api/analyze/text", json=payload)
    elif file_name.endswith('.mp4'):
        with open(file_path, "rb") as f:
            response = client.post("/api/analyze/video", files={"file": (file_name, f, "video/mp4")})
    elif file_name.endswith('.wav'):
        with open(file_path, "rb") as f:
            response = client.post("/api/analyze/audio", files={"file": (file_name, f, "audio/wav")})
    else:
        return {"error": "Unsupported file format"}

    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"Status code {response.status_code}", "detail": response.text}

def run_tests():
    # 5 fake/real images, 5 fake/real text files
    files_to_test = [
        os.path.join(os.path.dirname(__file__), "verification_files/test_img_0.jpg"),
        os.path.join(os.path.dirname(__file__), "verification_files/test_img_1.jpg"),
        os.path.join(os.path.dirname(__file__), "verification_files/test_img_2.jpg"),
        os.path.join(os.path.dirname(__file__), "verification_files/test_img_3.jpg"),
        os.path.join(os.path.dirname(__file__), "verification_files/test_img_4.jpg"),
        os.path.join(os.path.dirname(__file__), "verification_files/test_txt_0.txt"),
        os.path.join(os.path.dirname(__file__), "verification_files/test_txt_1.txt"),
        os.path.join(os.path.dirname(__file__), "verification_files/test_txt_2.txt"),
        os.path.join(os.path.dirname(__file__), "verification_files/test_txt_3.txt"),
        os.path.join(os.path.dirname(__file__), "verification_files/test_txt_4.txt"),
    ]
    
    results = []
    for file_path in files_to_test:
        print(f"Testing {file_path}...")
        res = test_file(file_path)
        results.append({
            "file": file_path,
            "result": res
        })
    
    with open("test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Results saved to test_results.json")

if __name__ == "__main__":
    run_tests()
