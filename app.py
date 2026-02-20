import os
import io
import re
import pandas as pd
import pdfplumber
from flask import Flask, request, send_file, render_template_string

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YOON & AHN Customs - 인보이스 변환기</title>
    <style>
        body {
            background-image: url('/static/background.jpg');
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-color: #5a3a22; 
            height: 100vh;
            margin: 0;
            display: flex;
            flex-direction: column;
            justify-content: flex-end; 
            align-items: center;
            padding-bottom: 15vh; 
            font-family: 'Malgun Gothic', sans-serif;
        }
        .container {
            background-color: rgba(255, 255, 255, 0.9); 
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 8px 16px rgba(0,0,0,0.3);
            text-align: center;
            max-width: 500px;
            width: 90%;
        }
        h1 { 
            color: #5a3a22; 
            margin-top: 0;
            font-size: 24px;
        }
        p { color: #333; }
        .upload-btn {
            background-color: #5a3a22;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
            margin-top: 20px;
            transition: background-color 0.3s ease;
        }
        .upload-btn:hover { background-color: #3e2615; }
        input[type="file"] { 
            margin-top: 20px; 
            font-size: 15px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📄 ENCOM 엑셀 자동 변환</h1>
        <p>인보이스 PDF 파일을 업로드하시면<br>데이터가 추출되어 엑셀 파일로 바로 다운로드됩니다.</p>
        <form action="/upload" method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept=".pdf" required>
            <br>
            <button type="submit" class="upload-btn">변환 및 다운로드</button>
        </form>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "파일이 업로드되지 않았습니다.", 400
    file = request.files['file']
    if file.filename == '':
        return "선택된 파일이 없습니다.", 400
    
    if file and file.filename.lower().endswith('.pdf'):
        items_list = []
        file_bytes = file.read()
        
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                
                # 줄바꿈 무시하고 전체를 하나의 텍스트로 합친 후 공백 분리
                text = text.replace('\n', ' ')
                text = re.sub(r'\s+', ' ', text)
                words = text.split()
                
                for i, word in enumerate(words):
                    # PC 단어를 기점으로 데이터 수집
                    if word == "PC":
                        try:
                            # 1. 수량(Q'TY) 추출 (PC 앞이나 뒤의 숫자)
                            qty = "1"
                            qty_offset = 0
                            if i > 0 and words[i-1].isdigit():
                                qty = words[i-1]
                                qty_offset = -1
                            elif i < len(words)-1 and words[i+1].isdigit():
                                qty = words[i+1]
                                qty_offset = 1

                            # 2. 금액(AMOUNT/UP) 추출 (PC 이후의 숫자 2개)
                            start_price = i + 1 if qty_offset <= 0 else i + 2
                            prices = []
                            for j in range(start_price, min(start_price + 6, len(words))):
                                w = words[j].replace(",", "").replace("USD", "")
                                if w and w.replace(".", "", 1).isdigit():
                                    prices.append(w)
                                if len(prices) == 2:
                                    break
                                    
                            up_val = prices[0] if len(prices) > 0 else "0"
                            amount_val = prices[1] if len(prices) > 1 else up_val

                            # 3. MASK NAME 및 ITEM 추출 (PC 앞쪽으로 역추적)
                            end_desc = i - 1 if qty_offset >= 0 else i - 2
                            mask_name = ""
                            desc_words = []
                            item_no = "1"
                            
                            for j in range(end_desc, max(-1, end_desc - 15), -1):
                                w = words[j]
                                
                                # RRCA 코드는 건너뜀
                                if w.startswith("RRCA"):
                                    continue
                                    
                                # MASK NAME (가장 긴 하이픈 포함 문자열)
                                if "-" in w and len(w) >= 10 and mask_name == "":
                                    mask_name = w
                                    continue
                                    
                                # MASK NAME을 찾은 후 숫자가 나오면 ITEM 번호로 인식하고 역추적 종료
                                if mask_name != "":
                                    if w.isdigit() and len(w) <= 2:
                                        item_no = w
                                        break
                                    else:
                                        # 표 헤더 쓰레기값 필터링
                                        if w not in ["NAME", "MASK", "DESCRIPTION", "ITEM", "PR)", "Code(Pre", "Item"]:
                                            desc_words.insert(0, w)
                                            
                            item_code = " ".join(desc_words).strip()
                            if not item_code:
                                item_code = "PHOTOMASK"
                                
                            items_list.append({
                                "ITEM": item_no,
                                "Item Code(Pre PR)": item_code,
                                "MASK NAME": mask_name,
                                "Q'TY": qty,
                                "U/M": "PC",
                                "U/P": up_val,
                                "AMOUNT": amount_val,
                                "Term": "USD"
                            })
                        except Exception:
                            pass

        if not items_list:
            return "<script>alert('PDF에서 추출할 품목 데이터를 찾지 못했습니다. (지정된 양식이 아닐 수 있습니다.)'); history.back();</script>", 400
            
        df = pd.DataFrame(items_list)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Invoice_Items')
        
        output.seek(0)
        
        download_name = file.filename.replace('.pdf', '_ENCOM.xlsx')
        return send_file(
            output,
            as_attachment=True,
            download_name=download_name,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    return "<script>alert('잘못된 파일 형식입니다. PDF 파일을 업로드해주세요.'); history.back();</script>", 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)
