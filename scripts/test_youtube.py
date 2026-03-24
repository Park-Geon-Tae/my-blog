import sys
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs

def extract_video_id(url):
    parsed_url = urlparse(url)
    if parsed_url.hostname == 'youtu.be':
        return parsed_url.path[1:]
    if parsed_url.hostname in ('www.youtube.com', 'youtube.com'):
        if parsed_url.path == '/watch':
            return parse_qs(parsed_url.query)['v'][0]
    return None

def test_transcript(url):
    video_id = extract_video_id(url)
    if not video_id:
        print("Invalid YouTube URL")
        return

    print(f"Extracting transcript for video ID: {video_id}")
    try:
        # Fetch using the new instance method
        api = YouTubeTranscriptApi()
        transcript_data = api.fetch(video_id, languages=['ko', 'en'])
        text = " ".join([entry.text for entry in transcript_data])
        print("[SUCCESS] Extraction successful!")
        print("-" * 50)
        print(text[:500] + "..." if len(text) > 500 else text)
        print("-" * 50)
        return text
    except Exception as e:
        print(f"[ERROR] Extraction failed: {e}")

if __name__ == "__main__":
    # Test with a known video that has captions
    test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw" 
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    test_transcript(test_url)
