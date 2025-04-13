import os
import re
import numpy as np
import pandas as pd
import PyPDF2
from pdfminer.high_level import extract_text
import pdfid

def extract_pdf_features(pdf_path):
    try:
        with open(pdf_path, "rb") as f:
            pdf_reader = PyPDF2.PdfReader(f)
            metadata = pdf_reader.metadata
            num_pages = len(pdf_reader.pages)

            # Initialize feature dictionary
            features = {
                "pdfsize": os.path.getsize(pdf_path),  # File size in bytes
                "metadata size": len(str(metadata)) if metadata else 0,
                "pages": num_pages,
                "xref Length": 0,
                "isEncrypted": 1 if pdf_reader.is_encrypted else 0,
                "embedded files": 0,
                "images": 0,
                "text": 1 if extract_text(pdf_path) else 0,
                "header": 1 if re.search(r'%PDF-\d\.\d', open(pdf_path, "rb").read(10).decode(errors="ignore")) else 0,
                "obj": 0, "endobj": 0, "stream": 0, "endstream": 0,
                "xref": 0, "trailer": 0, "startxref": 0, "pageno": num_pages,
                "encrypt": 0, "ObjStm": 0, "Javascript": 0, "AA": 0,
                "OpenAction": 0, "Acroform": 0, "JBIG2Decode": 0,
                "RichMedia": 0, "launch": 0, "EmbeddedFile": 0, "XFA": 0, "Colors": 0
            }

            # Read PDF raw content
            with open(pdf_path, "rb") as pdf_file:
                raw_text = pdf_file.read().decode(errors="ignore")

            # Count occurrences of key PDF structures
            features["xref"] = raw_text.count("xref")
            features["trailer"] = raw_text.count("trailer")
            features["startxref"] = raw_text.count("startxref")
            features["obj"] = raw_text.count("obj")
            features["endobj"] = raw_text.count("endobj")
            features["stream"] = raw_text.count("stream")
            features["endstream"] = raw_text.count("endstream")

            # Check for potential threats
            features["Javascript"] = 1 if "/JS" in raw_text or "/JavaScript" in raw_text else 0
            features["AA"] = 1 if "/AA" in raw_text else 0
            features["OpenAction"] = 1 if "/OpenAction" in raw_text else 0
            features["Acroform"] = 1 if "/AcroForm" in raw_text else 0
            features["JBIG2Decode"] = 1 if "/JBIG2Decode" in raw_text else 0
            features["RichMedia"] = 1 if "/RichMedia" in raw_text else 0
            features["launch"] = 1 if "/Launch" in raw_text else 0
            features["EmbeddedFile"] = 1 if "/EmbeddedFile" in raw_text else 0
            features["XFA"] = 1 if "/XFA" in raw_text else 0

            return pd.DataFrame([features])  # Convert dictionary to DataFrame

    except Exception as e:
        print(f"Error extracting features from {pdf_path}: {e}")
        return None