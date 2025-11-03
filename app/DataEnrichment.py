# import os
# from datetime import datetime
# from app.helpers.Scraper import WebsiteScraper
# from app.helpers.Crawler import hybrid_crawl_logic
# from app.helpers.AIChat import AIChat
# from app.helpers.VectorDB import VectorDB
# from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain_core.documents import Document
# from app.models.MetaDataModel import MetaDataModel

# def fetch_crawlable_urls_from_url(
#     url: str,
#     max_depth: int = 1,
#     max_urls: int = 50
# ) -> dict:
#     """
#     Crawls the given URL up to max_depth and max_urls, and returns discovered URLs.
#     """
#     try:
#         discovered_urls = hybrid_crawl_logic(url, max_depth, max_urls)
#         if not discovered_urls:
#             return {"success": False, "data": [], "error": "No crawlable URLs found"}

#         crawlable_urls = [
#             {
#                 "url": u,
#                 "crawlStatus": "PENDING",
#                 "updatedOn": datetime.utcnow(),
#                 "ingestionStatus": "PENDING",
#                 "ingestedOn": None,
#                 "vectorDocIds": []
#             }
#             for u in discovered_urls
#         ]

#         return {"success": True, "data": crawlable_urls}
#     except Exception as e:
#         return {"success": False, "data": [], "error": str(e)}

# def scrape_urls_to_text_files(crawlable_urls, output_prefix="scraped") -> list:
#     """
#     Scrapes each URL in crawlable_urls and saves the markdown/text content
#     to a file in the current working directory. Returns a list of file paths.
#     """
#     scraper = WebsiteScraper()
#     file_paths = []
#     for idx, url_info in enumerate(crawlable_urls):
#         url = url_info["url"] if isinstance(url_info, dict) else url_info
#         try:
#             scrape_result = scraper.scrape_url(url)
#             if not scrape_result.get("success"):
#                 print(f"Scraping failed for {url}: {scrape_result.get('error')}")
#                 continue
#             scraped_text = scrape_result["data"]["markdown"]
#             if not scraped_text or len(scraped_text) < 100:
#                 print(f"Scraped content too short for {url}")
#                 continue
#             safe_url = url.replace("https://", "").replace("http://", "").replace("/", "_")
#             output_filename = f"{output_prefix}_{safe_url}.txt"
#             output_path = os.path.join(os.getcwd(), output_filename)
#             with open(output_path, "w", encoding="utf-8") as f:
#                 f.write(scraped_text)
#             print(f"Scraped content for {url} saved to: {output_path}")
#             file_paths.append({"url": url, "file_path": output_path})
#         except Exception as e:
#             print(f"Exception scraping {url}: {e}")
#     return file_paths

# def enrich_textfile_and_store_in_pinecone(
#     text_file_path: str,
#     url: str,
#     pinecone_namespace: str = "default"
# ):
#     """
#     Reads a text file, chunks the text, uses LLM to extract metadata and enrichment
#     (via extract_meta_data_from_chunk), and stores the results in Pinecone.
#     """
#     # 1. Read the text file
#     with open(text_file_path, "r", encoding="utf-8") as f:
#         full_text = f.read()

#     if not full_text or len(full_text) < 100:
#         raise Exception("Text file content is too short or empty.")

#     # 2. Chunk the text
#     text_splitter = RecursiveCharacterTextSplitter(
#         chunk_size=2000,  # adjust as needed
#         chunk_overlap=200
#     )
#     chunks = text_splitter.split_text(full_text)

#     # 3. Initialize helpers
#     ai_chat = AIChat(namespace=pinecone_namespace)
#     vectordb = VectorDB(namespace=pinecone_namespace)

#     # 4. For each chunk: extract metadata and store
#     for idx, chunk in enumerate(chunks):
#         try:
#             # Use extract_meta_data_from_chunk for LLM enrichment and metadata extraction
#             metadata = ai_chat.extract_meta_data_from_chunk(chunk)
#             metadata_dict = metadata.dict() if hasattr(metadata, "dict") else dict(metadata)
#         except Exception as e:
#             metadata_dict = {}
#             print(f"Metadata extraction failed for chunk {idx}: {e}")

#         metadata_dict.update({
#             "website_url": url,
#             "chunk_index": idx,
#         })

#         # Store in Pinecone using VectorDB
#         doc = Document(
#             page_content=chunk,
#             metadata=metadata_dict
#         )
#         try:
#             vectordb.vector_store.add_documents(
#                 documents=[doc],
#                 ids=[f"{url.replace('https://','').replace('http://','').replace('/','_')}_{idx}"],
#                 namespace=pinecone_namespace
#             )
#         except Exception as e:
#             print(f"Pinecone storage failed for chunk {idx}: {e}")

#     print("Enrichment and storage complete.")
#     return True

# def process_all_text_files_and_save_metadata(pinecone_namespace="default"):
#     ai_chat = AIChat(namespace=pinecone_namespace)
#     metadata_model = MetaDataModel()
#     project_root = "/Users/distinctcloudlabs/Developer/sourcehr-backend" 
#     cwd = os.path.join(project_root, "TextFiles")
#     for filename in os.listdir(cwd):
#         print(f"running for {filename}")
#         if filename.endswith(".txt") and filename != "requirements.txt":
#             file_path = os.path.join(cwd, filename)
#             with open(file_path, "r", encoding="utf-8") as f:
#                 full_text = f.read()
#             if not full_text or len(full_text) < 100:
#                 print(f"Skipping {filename}: content too short.")
#                 continue

#             # Chunk the text
#             text_splitter = RecursiveCharacterTextSplitter(
#                 chunk_size=2000,
#                 chunk_overlap=200
#             )
#             chunks = text_splitter.split_text(full_text)

#             for idx, chunk in enumerate(chunks):
#                 try:
#                     metadata = ai_chat.extract_meta_data_from_chunk(chunk)
#                     metadata_dict = metadata.dict() if hasattr(metadata, "dict") else dict(metadata)
#                 except Exception as e:
#                     print(f"Metadata extraction failed for chunk {idx} in {filename}: {e}")
#                     continue

#                 metadata_dict.update({
#                     "source_file": filename,
#                     "chunk_index": idx,
#                     "text": chunk
#                 })

#                 # --- Pinecone step ---
                
#                 try:
#                     metadata_model.create_metadata(metadata_dict)
#                     print(f"Saved metadata for chunk {idx} of {filename}")
#                 except Exception as e:
#                     print(f"Failed to save metadata for chunk {idx} in {filename}: {e}")



