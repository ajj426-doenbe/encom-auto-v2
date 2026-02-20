import os
import io
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
    <title>바른관세사무소 - 인보이스 변환기</title>
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
                    
                lines = text.split('\n')
                temp_desc = ""
                
                for line in lines:
                    if "PHOTOMASK" in line or "EB6X-NIK" in line:
                        if "PC" not in line:
                            temp_desc = line.strip()
                    
                    if "PC" in line and "USD" in line:
                        parts = line.split()
                        try:
                            amount_val = parts[-1]
                            up_val = parts[-2]
                            if up_val == 'USD':
                                up_val = parts[-3]
                                
                            um_val = "PC"
                            pc_index = parts.index("PC")
                            qty_val = parts[pc_index - 1]
                            mask_name_val = parts[pc_index - 2]
                            
                            item_no = parts[0]
                            if not item_no.isdigit():
                                item_no = "1"
                                
                            code_parts = parts[1:pc_index - 2]
                            item_code = " ".join(code_parts)
                            
                            if temp_desc and temp_desc not in item_code:
                                item_code = f"{temp_desc} {item_code}".strip()
                            elif not item_code and temp_desc:
                                item_code = temp_desc
                                
                            items_list.append({
                                "ITEM": item_no,
                                "Item Code(Pre PR)": item_code.replace("PHOTOMASK EB6X-NIK EB6X-NIK", "PHOTOMASK EB6X-NIK"),
                                "MASK NAME": mask_name_val,
                                "Q'TY": qty_val,
                                "U/M": um_val,
                                "U/P": up_val,
                                "AMOUNT": amount_val,
                                "Term": "USD"
                            })
                            temp_desc = "" 
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