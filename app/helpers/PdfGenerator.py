import os
from dotenv import load_dotenv
from weasyprint import HTML, CSS
from openai import AzureOpenAI
from datetime import datetime
from app.helpers.AzureStorage import AzureBlobUploader

load_dotenv()


class PdfGenerator:
    def __init__(self, azure_helper=None):
        """
        azure_helper: optional class that handles Azure Blob upload, must have
        method upload_file_to_azure_blob(file_path, folder_name, extension)
        """
        self.azure_client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version="2024-12-01-preview",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        self.azure_helper = AzureBlobUploader()  # external uploader helper

    def generate_pdf(self, content: str, title="Document", page_size="A4 portrait"):
        """
        Converts raw content → HTML via LLM → PDF → upload → returns URL
        """
        try:
            if not content.strip():
                return {"success": False, "error": "Content is empty"}

            html_prompt = f"""
            Convert the following content into a full HTML document with inline CSS suitable for PDF export.
            Title: {title}

            Content:
            {content}
            """

            response = self.azure_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a PDF generator. Format content as HTML with inline CSS."},
                    {"role": "user", "content": html_prompt}
                ]
            )

            html_content = response.choices[0].message.content
            cleaned = html_content.strip()  # remove leading/trailing whitespace/newlines
            if cleaned.startswith("```html"):
                cleaned = cleaned[len("```html"):].lstrip()
            if cleaned.endswith("```"):
                cleaned = cleaned[:-len("```")].rstrip()

            filename = f"{title.replace(' ', '_')}_{int(datetime.now().timestamp())}.pdf"
            filepath = os.path.join("generated_pdfs", filename)
            os.makedirs("generated_pdfs", exist_ok=True)

            css = CSS(string=f"""
                @page {{
                    size: {page_size};
                    margin: 20mm 14mm 20mm 14mm;
                }}
                body {{
                    font-family: Arial, sans-serif;
                    font-size: 12px;
                    color: #000;
                }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                }}
                th, td {{
                    border: 1px solid #000;
                    padding: 4px;
                    text-align: left;
                    vertical-align: top;
                }}
                th {{
                    background-color: #f0f0f0;
                }}
            """)

            HTML(string=cleaned).write_pdf(filepath, stylesheets=[css])

            if not self.azure_helper:
                return {"success": False, "error": "Azure helper not provided"}

            file_url = self.azure_helper.upload_file_to_azure_blob(filepath, "chat-documents", ".pdf")

            os.remove(filepath)

            if file_url:
                return {"data": file_url, "success": True}
            else:
                return {"success": False, "error": "Unable to upload PDF"}
        except Exception as e:
            return {"success": False, "error": str(e)}
