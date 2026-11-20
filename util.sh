#!/bin/bash
# Tiện ích chạy thử / đóng gói giống cách chấm bài (theo util.sh của code mẫu môn học).
# Yêu cầu: docker (test), python3 (submit)
# Dùng:
#   ./util.sh test     # build image, chạy với ./input -> ./$STUDENT_ID/output
#   ./util.sh submit   # tạo file nộp dist/<MSSV...>.zip (< 10MB)

# Điền MSSV các thành viên (cách nhau bằng dấu -)
STUDENT_ID="MSSV1-MSSV2-MSSV3-MSSV4"
IMAGE="nlp-course-assistant"

S_OUT="$(pwd)/$STUDENT_ID/output"
S_IN="$(pwd)/input"

function run_ { echo "Hãy dùng: ./util.sh test | ./util.sh submit" ; }

function run_test {
	echo "Build và chạy giống lúc chấm..."
	mkdir -p "$S_OUT"
	docker build --network=host -t $IMAGE . || exit 1
	docker run --rm -v "$S_OUT:/nlp/output" -v "$S_IN:/nlp/input" $IMAGE "$@"
	echo "Kết quả nằm trong $S_OUT"
}

function run_submit {
	python3 scripts/package.py --ids ${STUDENT_ID//-/ } --report docs/report/BaoCao_BTL_NLP.pdf
}

run_$1 "${@:2}"
