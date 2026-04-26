import io
import logging
from pathlib import Path

import pdfplumber
import pytesseract
from PIL import Image, ImageFilter

from app.services.extraction import extract_from_text, extract_rows_from_text, parse_excel_workbook
from app.services.validation import ExtractedFields

logger = logging.getLogger(__name__)


class DocumentProcessingError(Exception):
    pass


SUPPORTED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.tif', '.tiff'}
SUPPORTED_TEXT_EXTENSIONS = {'.pdf'}
SUPPORTED_EXCEL_EXTENSIONS = {'.xls', '.xlsx'}


def detect_file_type(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix in SUPPORTED_TEXT_EXTENSIONS:
        return 'pdf'
    if suffix in SUPPORTED_IMAGE_EXTENSIONS:
        return 'image'
    if suffix in SUPPORTED_EXCEL_EXTENSIONS:
        return 'excel'
    raise DocumentProcessingError(f'Unsupported file type: {suffix}')


def process_document(file_path: Path) -> tuple[str, ExtractedFields, str, list[ExtractedFields]]:
    file_type = detect_file_type(file_path)
    if file_type == 'pdf':
        return process_pdf(file_path)
    if file_type == 'image':
        return process_image(file_path)
    if file_type == 'excel':
        return process_excel(file_path)
    raise DocumentProcessingError(f'Unsupported document type: {file_type}')


def process_pdf(file_path: Path) -> tuple[str, ExtractedFields, str, list[ExtractedFields]]:
    extracted_text_parts: list[str] = []
    page_errors: list[str] = []
    with pdfplumber.open(str(file_path)) as pdf:
        for page_index, page in enumerate(pdf.pages, start=1):
            try:
                page_text = page.extract_text() or ''
                if page_text.strip():
                    extracted_text_parts.append(f'[Page {page_index}]\n{page_text}')
                    continue
                image = page.to_image(resolution=300).original
                preprocessed = preprocess_image_for_ocr(image)
                ocr_text = pytesseract.image_to_string(preprocessed)
                if ocr_text.strip():
                    extracted_text_parts.append(f'[Page {page_index} OCR]\n{ocr_text}')
                print(f'Processed page: {page_index}')
            except Exception as exc:
                logger.exception('Failed to process PDF page %s: %s', page_index, exc)
                page_errors.append(f'Page {page_index}: {exc}')
    combined_text = '\n'.join(extracted_text_parts).strip()
    if not combined_text:
        message = 'No text could be extracted from the PDF using text extraction or OCR.'
        if page_errors:
            message = f'{message} Page errors: {"; ".join(page_errors)}'
        raise DocumentProcessingError(message)
    extracted_fields = extract_from_text(combined_text)
    extracted_rows = extract_rows_from_text(combined_text)
    return combined_text, extracted_fields, 'pdf', extracted_rows


def process_image(file_path: Path) -> tuple[str, ExtractedFields, str, list[ExtractedFields]]:
    try:
        with Image.open(file_path) as image:
            preprocessed = preprocess_image_for_ocr(image.convert('RGB'))
            text = pytesseract.image_to_string(preprocessed)
    except Exception as exc:
        raise DocumentProcessingError(f'Failed to OCR image: {exc}') from exc
    if not text.strip():
        raise DocumentProcessingError('No text could be extracted from the image.')
    extracted_fields = extract_from_text(text)
    extracted_rows = extract_rows_from_text(text)
    return text, extracted_fields, 'image', extracted_rows


def process_excel(file_path: Path) -> tuple[str, ExtractedFields, str, list[ExtractedFields]]:
    try:
        extracted_rows, text_rows = parse_excel_workbook(str(file_path))
        text = '\n'.join(text_rows)
        extracted_fields = extracted_rows[0] if extracted_rows else ExtractedFields()
    except Exception as exc:
        raise DocumentProcessingError(f'Failed to parse Excel file: {exc}') from exc
    if not text.strip():
        raise DocumentProcessingError('No text could be extracted from the Excel file.')
    return text, extracted_fields, 'excel', extracted_rows


def preprocess_image_for_ocr(image: Image.Image) -> Image.Image:
    grayscale = image.convert('L')
    resized = grayscale.resize((grayscale.width * 2, grayscale.height * 2))
    denoised = resized.filter(ImageFilter.MedianFilter(size=3))
    return denoised
