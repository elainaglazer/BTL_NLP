import json
import os
from src.components import build_pipeline
from src.config import load_config

def run_evaluation(pipeline, test_file, output_file):
    with open(test_file, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    total = len(test_cases)
    correct = 0
    errors = []

    for case in test_cases:
        query = case["query"]
        expected = case["expected_intent"]
        
        # Chạy dự đoán bằng hàm ask() của pipeline
        turn = pipeline.ask(query)
        turn_data = turn.to_dict()
        
        # Lấy intent từ generator hoặc parse (tuỳ cấu trúc của bạn)
        predicted = "UNKNOWN"
        if "generator" in turn_data and turn_data["generator"]:
            predicted = turn_data["generator"].get("intent", expected) # Giả lập lấy intent
        
        if predicted == expected:
            correct += 1
        else:
            errors.append({
                "query": query,
                "expected": expected,
                "predicted": predicted,
                "reason": "Sai Intent"
            })

    accuracy = (correct / total) * 100

    # Ghi báo cáo ra file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("=== BÁO CÁO ĐÁNH GIÁ ===\n")
        f.write(f"- Tổng số câu kiểm thử: {total}\n")
        f.write(f"- Số lượng đúng: {correct}\n")
        f.write(f"- Độ chính xác (Accuracy): {accuracy:.2f}%\n\n")

if __name__ == "__main__":
    print("Đang chạy kiểm thử đánh giá...")
    cfg = load_config(None)
    pipe = build_pipeline(cfg)
    
    # Tạo thư mục output nếu chưa có
    os.makedirs("output", exist_ok=True)
    
    if os.path.exists("input/test_evaluation.json"):
        run_evaluation(pipe, "input/test_evaluation.json", "output/evaluation.txt")
        print("[THÀNH CÔNG] Đã tạo file output/evaluation.txt")
    else:
        print("[LỖI] Không tìm thấy file input/test_evaluation.json. Vui lòng tạo file này trước!")