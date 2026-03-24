import os
import sys
import json
import re
import random
import string
from datetime import datetime
from dotenv import load_dotenv  # type: ignore
from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore
from google import genai  # type: ignore
from google.genai import types  # type: ignore
from pydantic import BaseModel  # type: ignore

# 환경 변수 로드
load_dotenv()

def get_transcript(video_id: str) -> str | None:
    """
    유튜브 자막을 추출합니다.
    """
    try:
        api = YouTubeTranscriptApi()
        transcript_data = api.fetch(video_id, languages=['ko', 'en'])
        text = " ".join([entry.text for entry in transcript_data])
        return text
    except Exception as e:
        print(f"[ERROR] 자막 추출 실패: {e}")
        return None

def get_valid_text_model(client: genai.Client) -> str:
    try:
        available = [m.name.replace('models/', '') for m in client.models.list()]
    except:
        return 'gemini-1.5-flash'
    for p in ['gemini-1.5-flash', 'gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-flash-latest']:
        if p in available: return p
    for m in available:
        if 'flash' in m: return m
    return available[0] if available else 'gemini-1.5-flash'

def get_valid_image_model(client: genai.Client) -> str:
    try:
        available = [m.name.replace('models/', '') for m in client.models.list()]
    except:
        return 'imagen-3.0-generate-001'
    for p in ['imagen-3.0-generate-001', 'imagen-4.0-generate-001', 'imagen-4.0-fast-generate-001']:
        if p in available: return p
    for m in available:
        if 'imagen' in m: return m
    return 'imagen-3.0-generate-001'

class BlogPost(BaseModel):
    title: str
    description: str
    tags: list[str]
    content: str
    image_prompt_1: str
    image_prompt_2: str

def generate_blog_content(transcript_text: str, client: genai.Client) -> dict | None:
    """
    Gemini 1.5 Pro를 활용하여 Mr.FIX 페르소나로 블로그 포스팅 초안과 프롬프트를 작성합니다.
    """
    safe_transcript = transcript_text[:15000]  # type: ignore
    prompt = f"""
당신은 유튜브 자막을 단순히 요약하는 AI가 아니라, '9년 차 베테랑 PLC 제어 및 전기 설계 엔지니어'의 시각으로 기술을 분석하는 전문가입니다.

[응답 포맷 및 출력 방식]
전체 응답을 하나의 JSON으로 묶지 말고, 반드시 아래 예시처럼 가장 먼저 메타데이터를 담은 JSON 코드 블록(```json ... ```)을 작성한 뒤, 그 아래에 마크다운(Markdown) 포스팅 본문을 순수 텍스트로 자유롭게 이어서 작성하십시오. 이렇게 하면 마크다운 본문 내에서 줄바꿈(\n)을 자유롭게 사용할 수 있습니다.

예시 포맷:
```json
{{
  "title": "포스팅 제목",
  "description": "150자 이내의 요약 설명 (줄바꿈 없이)",
  "tags": ["태그1", "태그2"],
  "image_prompt_1": "첫번째 이미지 영문 핵심 키워드 (예: robot, network)",
  "image_prompt_2": "두번째 이미지 영문 핵심 키워드 (예: factory, cyber)"
}}
```
본문(Markdown) 시작...

아래 주어진 유튜브 영상 자막 스크립트를 분석하여 블로그 포스팅을 작성해주세요.

[작성 지침 및 스타일]
1. 문단 구분 강화: 텍스트가 빽빽하게 나열되는 것을 피하고, 의미 단위로 문단을 나누어 반드시 두 줄 이상의 줄 바꿈을 넣어 가독성을 확보하십시오. 가독성을 위해 리스트(불렛 포인트)와 강조(Bold)를 적절히 섞어 사용하십시오.
2. 데이터 추출: 자막은 오직 '기술적 팩트'와 '핵심 데이터'를 추출하는 소스로만 사용하십시오.
3. 문체 통제: 원문의 비유, 농담, 구어체 표현은 100% 제거하고, 당신만의 논리적이고 권위 있는 문장으로 완벽하게 재구성하십시오. 감정적인 서술을 완벽히 배제하십시오.
4. 컨셉: 'Mr.FIX의 기술 분석 로그'라는 컨셉에 맞게, 객관적이고 전문적인 분석 리포트 형식으로 작성하십시오. 독자에게 신뢰감을 주는 깔끔하고 권위 있는 '입니다/습니다'체를 사용해야 합니다.
5. 강력한 결론: 반드시 기술적 요약과 함께 명확한 결론(Conclusion)으로 글을 마무리할 것.

[구조 및 SEO 제약사항]
1. [Frontmatter]: 제목(title), 설명(description), 태그(tags) 정보를 포함하세요. (주의: description은 절대 줄바꿈을 포함하지 말고 150자 이내의 단일 문단으로 작성하세요.)
2. [Hooks]: 가장 첫 줄은 독자의 이목을 단숨에 끌 수 있는 150자 내외의 단호하고 흥미로운 후킹 문구로 시작하세요. 가벼운 어투 대신 기술적 호기심을 지적으로 자극해야 합니다.
3. [Table of Contents]: 초기 후킹 문구 바로 다음에 '## 목차' 섹션을 반드시 만들어주세요. 목차는 본문의 중제목(##)과 소제목(###)을 계층 구조의 리스트(불렛 포인트) 형태로 구성하십시오. 각 목차 항목은 클릭 시 해당 위치로 이동할 수 있도록 마크다운 앵커 링크([제목](#제목-텍스트)) 형식으로 작성하십시오.
4. [Heading]: H2(##), H3(###) 구조를 통해 내용을 SEO에 맞게 논리적이고 깔끔하게 분리하세요. H1(#)은 외부 타이틀이 되므로 본문에서 제외하세요.
5. [Images]: 글의 중간중간 이해를 돕거나 썸네일로 쓸 만한 위치 2곳에 정확히 문자열 `{{IMAGE_1}}`과 `{{IMAGE_2}}`를 삽입하세요.
6. [Image Prompts]: 해당 2장의 이미지를 대체할 무료 이미지 검색용 '1~2개의 영문 핵심 키워드'를 각각 작성하세요. (예: robot, cyber, factory, network 등). 본문 내용과 가장 연관성 높은 단순한 명사 형태로 띄어쓰기 없이 작성해야 합니다.
7. [Teaser & Closing]: 글의 맨 마지막 섹션에 '다음 리포트 예고' 항목을 만들어주세요. 자막 전체 맥락을 파악해 '다음에는 이와 관련된 어떤 심화 주제나 실무 팁을 다룰 것인지' 1~2문장으로 임팩트 있게 작성하십시오. 추가로 그 밑에는 반드시 "오늘의 분석이 현장 업무에 도움이 되길 바랍니다. Mr.FIX였습니다."라는 고정 멘트로 깔끔하게 클로징하십시오.

[유튜브 자막 스크립트]
{safe_transcript}

"""
    print("[INFO] Gemini에 포스팅 작성을 요청합니다...")
    try:
        model_name = get_valid_text_model(client)
        print(f"[INFO] 선택된 텍스트 모델: {model_name}")
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=8192,
            )
        )
        
        text = response.text
        # JSON 블록 추출
        json_match = re.search(r'```json\n(.*?)\n```', text, re.DOTALL)
        if not json_match:
            print("[ERROR] 메타데이터 JSON 블록을 응답에서 찾을 수 없습니다.")
            print(f"[DEBUG] 원본 응답:\n{text[:500]}...")
            return None
            
        meta = json.loads(json_match.group(1), strict=False)
        content = text[json_match.end():].strip()
        
        # 이전 BlogPost 구조와 동일한 딕셔너리 반환
        return {
            "title": meta.get("title", "제목 없음"),
            "description": meta.get("description", ""),
            "tags": meta.get("tags", []),
            "image_prompt_1": meta.get("image_prompt_1", "automation"),
            "image_prompt_2": meta.get("image_prompt_2", "technology"),
            "content": content
        }
    except json.JSONDecodeError as e:
         print(f"[ERROR] 메타데이터 JSON 블록 파싱 실패: {e}")
    except Exception as e:
        print(f"[ERROR] 블로그 컨텐츠 생성 실패: {e}")
        return None

def generate_and_save_image(client: genai.Client, prompt: str, output_path: str) -> bool:
    """
    파이썬 스크립트가 100% 자동화를 유지할 수 있도록, 별도 가입이 필요 없는 무료 AI 이미지 생성 API
    (Pollinations AI)를 사용하여 이미지를 자동 다운로드 및 저장합니다. 
    (Gemini Imagen 3의 유료 제약을 우회하여 자동화를 유지합니다)
    """
    import urllib.request
    import urllib.parse
    
    print(f"[INFO] Pollinations AI를 통한 무료 이미지 자동 생성 요청 중...")
    print(f"[INFO] 프롬프트: '{prompt}'")
    print(f"[INFO] 저장 예정 절대 경로: {os.path.abspath(output_path)}")
    try:
        # 안전한 URL 파라미터를 위해 띄어쓰기를 콤마로 변경 및 인코딩 (LoremFlickr 방식)
        safe_keyword = urllib.parse.quote(prompt.replace(' ', ','))
        # 무작위 이미지 대신 주제와 연관된 이미지를 반환하는 무료 서비스 사용
        image_url = f"https://loremflickr.com/1024/576/{safe_keyword}"
        
        # 파일 저장
        abs_output_path = os.path.abspath(output_path)
        req = urllib.request.Request(
            image_url, 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req) as response:
            with open(abs_output_path, 'wb') as out_file:
                out_file.write(response.read())
        
        # 물리적 파일 생성 검증
        if os.path.exists(abs_output_path):
            file_size = os.path.getsize(abs_output_path)
            print(f"[SUCCESS] 이미지가 물리적으로 저장되었습니다. (크기: {file_size} bytes)")
            print(f"[SUCCESS] 자동화 이미지 저장 경로: {abs_output_path}")
            return True
        else:
            print(f"[ERROR] 이미지 다운로드 후 파일이 {abs_output_path} 에 존재하지 않습니다.")
            return False
            
    except Exception as e:
        print(f"[ERROR] 자동 이미지 다운로드 중 예외 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main(video_url: str) -> None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        print("[ERROR] .env 파일에서 GEMINI_API_KEY를 찾을 수 없습니다.")
        sys.exit(1)
        
    # 유튜브 URL에서 video_id 파싱
    from urllib.parse import urlparse, parse_qs
    parsed_url = urlparse(video_url)
    if parsed_url.hostname == 'youtu.be':
        video_id = parsed_url.path[1:]  # type: ignore
    elif parsed_url.hostname in ('www.youtube.com', 'youtube.com'):
        video_id = parse_qs(parsed_url.query)['v'][0]
    else:
        print("[ERROR] 유효하지 않은 유튜브 URL 형식입니다.")
        sys.exit(1)
        
    client = genai.Client(api_key=api_key)
    
    # 1. 자막 추출
    transcript = get_transcript(video_id)
    if not transcript:
        sys.exit(1)
        
    assert transcript is not None
        
    # 2. AI 블로그 생성
    blog_data = generate_blog_content(transcript, client)
    if not blog_data:
        sys.exit(1)
        
    assert blog_data is not None
        
    # 3. 이미지 생성 및 저장 경로 준비
    today_str = datetime.now().strftime("%Y-%m-%d")
    # 마크다운 용 슬러그 (한글 허용)
    raw_slug = re.sub(r'[^\w\-]+', '-', blog_data['title'].lower(), flags=re.UNICODE).strip('-')
    slug = raw_slug if raw_slug else f"youtube-post-{video_id}"
    
    # 이미지 폴더용 안전한 슬러그 (Astro ImageNotFound 방지: 영문/숫자 + 랜덤문자)
    short_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    img_slug = f"{today_str}-{short_id}"
    
    # 이미지 저장 폴더 생성 (src/assets/images/)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assets_dir = os.path.join(base_dir, "src", "assets", "images", img_slug)
    os.makedirs(assets_dir, exist_ok=True)
    
    img1_filename = f"{today_str}-img1.png"
    img2_filename = f"{today_str}-img2.png"
    img1_path = os.path.join(assets_dir, img1_filename)
    img2_path = os.path.join(assets_dir, img2_filename)
    
    print(f"[INFO] 이미지 1 파일 경로 (os.path.join): {img1_path}")
    success1 = generate_and_save_image(client, blog_data['image_prompt_1'], img1_path)
    if not success1:
        print(f"[WARNING] 이미지 1 저장/생성 실패! ({img1_path})")

    print(f"[INFO] 이미지 2 파일 경로 (os.path.join): {img2_path}")
    success2 = generate_and_save_image(client, blog_data['image_prompt_2'], img2_path)
    if not success2:
        print(f"[WARNING] 이미지 2 저장/생성 실패! ({img2_path})")
    
    # 4. 본문(content) 내 이미지 플레이스홀더 치환
    # Astro의 상대 경로 최적화가 동작하도록 안전한 영문/숫자 img_slug 사용
    content = blog_data['content']
    content = content.replace("{IMAGE_1}", f"![이미지 1](../../assets/images/{img_slug}/{img1_filename})")
    content = content.replace("{IMAGE_2}", f"![이미지 2](../../assets/images/{img_slug}/{img2_filename})")
    
    # 5. 마크다운 파일 조립 및 최종 저장
    # 옵션에 맞추어 src/content/blog 폴더를 최우선, 없으면 src/data/blog 사용
    blog_dir = os.path.join(base_dir, "src", "content", "blog")
    if not os.path.exists(blog_dir):
        fallback_dir = os.path.join(base_dir, "src", "data", "blog")
        if os.path.exists(fallback_dir):
            blog_dir = fallback_dir
    os.makedirs(blog_dir, exist_ok=True)
    
    md_filename = f"{today_str}-{slug}.md"
    md_filepath = os.path.join(blog_dir, md_filename)
    
    pub_datetime = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+09:00")
    
    frontmatter = f"""---
title: "{blog_data['title']}"
author: Mr.FIX
pubDatetime: {pub_datetime}
slug: {slug}
featured: false
draft: false
tags:
"""
    for tag in blog_data['tags']:
        frontmatter += f"  - {tag}\n"
        
    frontmatter += f"description: \"{blog_data['description']}\"\n---\n\n"
    
    final_markdown = frontmatter + content
    
    with open(md_filepath, "w", encoding="utf-8") as f:
        f.write(final_markdown)
        
    print(f"[SUCCESS] 블로그 포스팅이 성공적으로 작성되었습니다: {md_filepath}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python scripts/youtube_to_blog.py <YOUTUBE_URL>")
        sys.exit(1)
        
    main(sys.argv[1])
