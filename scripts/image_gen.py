import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

def generate_image(prompt: str, output_path: str):
    """
    Google GenAI SDK를 사용하여 Imagen 3 모델로 이미지 생성 및 저장
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        print("[ERROR]: .env 파일에 유효한 GEMINI_API_KEY가 설정되지 않았습니다.")
        return False

    # Gemini 클라이언트 초기화
    client = genai.Client(api_key=api_key)
    
    print(f"[INFO] 이미지 생성 요청 중... 프롬프트: '{prompt}'")
    try:
        # Imagen 3 모델 지정 (최신 식별자: imagen-3.0-generate-001)
        result = client.models.generate_images(
            model='imagen-3.0-generate-001',
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                output_mime_type="image/jpeg",
                aspect_ratio="16:9" 
            )
        )
        
        # 생성된 이미지 저장
        for generated_image in result.generated_images:
            image = generated_image.image
            
            with open(output_path, "wb") as f:
                f.write(image.image_bytes)
            
            print(f"[SUCCESS] 이미지가 성공적으로 저장되었습니다: {output_path}")
            return True
            
    except Exception as e:
        print(f"[ERROR] 이미지 생성 실패: {e}")
        return False

if __name__ == "__main__":
    # 테스트 실행
    test_prompt = "A futuristic robot writing a tech blog post on a laptop, cyberpunk style, high quality, vibrant colors"
    output_filename = "test_imagen3.jpg"
    generate_image(test_prompt, output_filename)
