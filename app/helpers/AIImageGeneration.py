import os
import base64
import time
from openai import AzureOpenAI

import requests
from app.helpers.AzureStorage import AzureBlobUploader

from PIL import Image
from pydantic import BaseModel
from dotenv import load_dotenv
load_dotenv()
import re


class NewsThumbnailPrompt(BaseModel):
    imagePrompt:str

class NewsImageGenerator:
    def __init__(self, temp_dir: str = "temp_images"):
 
        self.azure_storage = AzureBlobUploader()
        self.temp_dir = temp_dir
        os.makedirs(self.temp_dir, exist_ok=True)
        
    def compress_image(self, file_path):
        try:
            img = Image.open(file_path)
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == ".png":
                rgb_img = img.convert("RGB")
                new_file_path = file_path.replace(".png", ".jpg")
                rgb_img.save(new_file_path, quality=85)
                return new_file_path
            else:
                rgb_img = img.convert("RGB")
                rgb_img.save(file_path, quality=85)
                return file_path
        except Exception as e:
            print(f"Compression failed: {e}")
            return file_path
            

    def generate_prompt_from_article(self, article: str) -> str:

        system_prompt = (
            "You are an expert prompt engineer who writes short, vivid, and detailed prompts "
            "for image generation models. Your prompts create realistic editorial-style images "
            "that look like authentic news photos accompanying articles."
        )

        user_prompt = (
            f"Write  image generation prompt for  article that creates a realistic editorial news photo "
            f"based on the following news article:\n\n{article}\n\n"
            f"The prompt should clearly specify the scene, people, objects, emotions, and environment "
            f"to make it look like a genuine news article image. Limit to 50 words."
        )

        chat_client=AzureOpenAI(
            azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
            api_key=os.getenv('AZURE_OPENAI_KEY'),
            api_version="2024-12-01-preview")       
            
        
        completion = chat_client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format=NewsThumbnailPrompt,
            )
        result =  completion.choices[0].message.parsed.dict()
        return result

    def generate_image_from_prompt(self, prompt, max_retries=3) -> bytes:
        retries = 0
        while retries < max_retries:
            try:
                image_client = AzureOpenAI(
                    azure_endpoint=os.getenv('AZURE_OPENAI_IMAGE_ENDPOINT'),
                    api_key=os.getenv('AZURE_OPENAI_IMAGE_KEY'),
                    api_version="2024-04-01-preview"
                )
                response = image_client.images.generate(
                    model="dall-e-3",
                    prompt=prompt.get("imagePrompt", ""),
                    n=1,
                    style="vivid",
                    quality="standard"
                )
                image = requests.get(response.data[0].url)
                image.raise_for_status()
                image_bytes = image.content
                return image_bytes
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "rate limit" in error_str.lower():
                    wait_time = 60  # Default wait time, or parse from error if available
                    print(f"Rate limit hit. Retrying after {wait_time} seconds...")
                    time.sleep(wait_time)
                    retries += 1
                else:
                    print(error_str)
                    break
        print("[Image generation]for a article failed after retries")
        return None

    def save_image_locally(self, image_bytes: bytes,news_id:str) -> str:
        file_path = os.path.join(self.temp_dir, f"{news_id}.png")
        with open(file_path, "wb") as f:
            f.write(image_bytes)
        return file_path

    def upload_image_to_azure(self, file_path: str) -> str:
        return self.azure_storage.upload_file_to_azure_blob(
            file_path=file_path,
            folder_name='newsImages'
        )

    def sanitize_filename(self, filename):
        # Replace any character that is not alphanumeric, dash, dot, or underscore with an underscore
        return re.sub(r'[^A-Za-z0-9._-]', '_', str(filename))

    def process_article(self,article,news_id):
        """
        Retrieves the latest article, generates prompt/image, uploads it,
        and updates the article with the image URL.
        """
        try:
            prompt = self.generate_prompt_from_article(article)
            print(f"Prompt: {prompt}")

            image_bytes = self.generate_image_from_prompt(prompt)
            safe_news_id = self.sanitize_filename(news_id)
            local_path = self.save_image_locally(image_bytes, safe_news_id)
            compressed_local_path = self.compress_image(local_path)

            image_url = self.upload_image_to_azure(compressed_local_path)
            print(f"Image uploaded to: {image_url}")

            os.remove(compressed_local_path)
            # print(f"News {news_id} updated with image.")
            return image_url

        except Exception as e:
            print(f"[Image generation]for a article failed {e}")
            
            
        #     continue
        # return 'ALL Images for news articles generated'