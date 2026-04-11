import zipfile
import tempfile
import os

class HwpxExporter:
    """
    1. HWP 다운로드 방식: 지정된 '기존 템플릿 텍스트 치환 방식(HWPX)'
    
    문서 변환기(Docx/PDF->HWP)를 절대 사용하지 않고, 제공된 '표준 HWPX 템플릿 파일'의 
    내부 XML 구조를 압축 해제해서 특정 태그만 AI 생성 텍스트로 치환한 뒤 다시 압축하는 아키텍처.
    정부 양식 특유의 표 크기, 자간, 장평, 폰트 규정이 깨지는 현상을 100% 방지함.
    """
    def __init__(self, template_path, output_path):
        self.template_path = template_path
        self.output_path = output_path
        
    def generate(self, data_dict):
        """
        data_dict: {"{{회사명}}": "GrantAI", "{{시장규모}}": "1조원", ...}
        """
        if not os.path.exists(self.template_path):
            raise FileNotFoundError(f"템플릿 파일을 찾을 수 없습니다: {self.template_path}")
            
        with tempfile.TemporaryDirectory() as temp_dir:
            # 1. HWPX(zip) 압축 해제
            with zipfile.ZipFile(self.template_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # 2. 본문 XML (Contents/ 하위의 section.xml 파일들) 내용 텍스트 치환
            contents_dir = os.path.join(temp_dir, 'Contents')
            if os.path.exists(contents_dir):
                for filename in os.listdir(contents_dir):
                    if filename.startswith('section') and filename.endswith('.xml'):
                        xml_path = os.path.join(contents_dir, filename)
                        
                        with open(xml_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # AI 생성 텍스트로 태그 치환 
                        for key, value in data_dict.items():
                            # XML 특수문자 이스케이프(필요 시 확장)
                            safe_value = str(value).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                            content = content.replace(key, safe_value)
                            
                        # 수정된 XML 저장
                        with open(xml_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                            
            # 3. 파싱 및 치환된 폴더를 다시 HWPX 포맷으로 압축
            with zipfile.ZipFile(self.output_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zip_ref.write(file_path, arcname)
