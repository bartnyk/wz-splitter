import os
import re
from datetime import datetime
from typing import Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

import cv2
import numpy as np
import pytesseract
from pdf2image import convert_from_path
from PIL import Image

tesseract_path = os.getenv("WZ_TESSERACT_PATH")
if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path


class PdfFileProcessor:
    def __init__(
        self,
        file_path: str,
        output_dir: str | None = None,
        original_path: str | None = None,
    ) -> None:
        self.file_path: str = file_path
        self.original_path: str = original_path or file_path

        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"File {self.file_path} not found")

        self.output_dir: str = self._ensure_dir_exists(
            output_dir or self.original_path.replace(".pdf", "")
        )
        self.done_dir: str = self._ensure_dir_exists(self.done_dir_path)
        self._images: List = []
        self._wz_map: Dict[str, List[Image.Image]] = {}
        self._processed: bool = False

    def _ensure_dir_exists(self, dir_path: str) -> str:
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        return dir_path

    @property
    def done_dir_path(self) -> str:
        done_dir_name = datetime.now().strftime("%d-%m-%Y")
        root_dir = os.path.dirname(self.original_path)
        return os.path.join(root_dir, done_dir_name)

    def _split_file(self) -> None:
        poppler_path = os.getenv("WZ_POPPLER_PATH")
        if not poppler_path:
            raise ValueError("Poppler path not found in config.")
        self._images = convert_from_path(
            self.file_path, poppler_path=poppler_path, dpi=200, grayscale=True
        )

    def process_pdf(self) -> None:
        self._split_file()

        if not self._images:
            raise ValueError("PDF seems to be empty or broken.")

        pattern = r"(WZK?-\d+\/\d{2}\/[A-Z]+\/\d{2})"
        wz_number: Optional[str] = None
        for image in self._images:
            img_cv = np.array(image)
            h, w = img_cv.shape[:2]
            cut_img = img_cv[: h // 4, w // 2 :]

            # debug_dir = os.path.join(os.path.dirname(self.original_path), "debug_cuts")
            # os.makedirs(debug_dir, exist_ok=True)
            page_idx = self._images.index(image)

            matched = self._ocr_best_match(cut_img, pattern, page_idx, debug_dir)
            if matched:
                wz_number = self._clean_wz_number(matched)

            content = pytesseract.image_to_string(
                cut_img, lang="eng", config="--psm 6 --oem 3"
            )
            if len(content) < 40:  # pusta strona
                continue

            if wz_number:
                if wz_number not in self._wz_map:
                    self._wz_map[wz_number] = []
                self._wz_map[wz_number].append(image)

        self._processed = True

    def _ocr_best_match(
        self, img: np.ndarray, pattern: str, page_idx: int, debug_dir: str
    ) -> Optional[str]:
        def _variant_original(i: np.ndarray) -> np.ndarray:
            return i

        def _variant_contrast(i: np.ndarray) -> np.ndarray:
            return cv2.convertScaleAbs(i, alpha=2.0, beta=50)

        def _variant_binary(i: np.ndarray) -> np.ndarray:
            contrast = cv2.convertScaleAbs(i, alpha=2.0, beta=50)
            _, binary = cv2.threshold(contrast, 150, 255, cv2.THRESH_BINARY)
            return binary

        def _variant_sharpened(i: np.ndarray) -> np.ndarray:
            contrast = cv2.convertScaleAbs(i, alpha=2.0, beta=50)
            _, binary = cv2.threshold(contrast, 150, 255, cv2.THRESH_BINARY)
            kernel = np.ones((1, 1), np.uint8)
            denoised = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
            sharpen_kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
            sharpened = cv2.filter2D(denoised, -1, sharpen_kernel)
            return cv2.GaussianBlur(sharpened, (5, 5), 0)

        def _variant_inverted(i: np.ndarray) -> np.ndarray:
            return cv2.bitwise_not(_variant_binary(i))

        variants = [
            _variant_original,
            _variant_contrast,
            _variant_binary,
            _variant_sharpened,
            _variant_inverted,
        ]

        for idx, fn in enumerate(variants):
            processed = fn(img)
            # cv2.imwrite(
            #     os.path.join(debug_dir, f"page_{page_idx:03d}_v{idx}.png"), processed
            # )
            content = pytesseract.image_to_string(
                processed, lang="eng", config="--psm 6 --oem 3"
            )
            if m := re.search(pattern, content):
                return m.group(1)

        return None

    def _clean_wz_number(self, wz: str) -> str:
        """
        Cleans the WZ number by correcting common OCR mistakes.
        The last part is expected to be numeric.
        """
        parts = wz.split("/")
        if len(parts) > 1:
            last_part = parts[-1]
            clean_last = (
                last_part.replace("I", "1")
                .replace("L", "1")
                .replace("|", "1")
                .replace("O", "0")
                .replace("S", "5")
            )
            parts[-1] = clean_last

            return "/".join(parts)
        return wz

    def save_all(self) -> None:
        if not self._processed:
            raise ValueError("PDF not processed yet.")

        counter = 0
        source_name = os.path.basename(self.original_path)

        print(f"\n{source_name}:")
        for wz_number, images in self._wz_map.items():
            file_name = f"{wz_number.replace('/', '_')}.pdf"
            file_path = f"{self.output_dir}/{file_name}"
            self.save_pdf(file_path, images)
            counter += 1
            print(f"  [{counter:02d}] {file_name}  ({len(images)} page[s])")

        print(f"\nTotal: {counter} WZ's from {source_name}.")

        self._move_done()

    def _move_done(self) -> None:
        if not self._processed:
            raise ValueError("PDF not processed yet.")

        file_name = os.path.basename(self.original_path)
        new_file_path = os.path.join(self.done_dir_path, file_name)

        # Ensure done_dir exists right before moving
        os.makedirs(self.done_dir_path, exist_ok=True)

        os.replace(
            self.file_path,
            new_file_path,
        )
        print(f"Moved {file_name} to {new_file_path}.")

    def save_pdf(self, file_path: str, images: List[Image.Image]) -> None:
        images[0].save(
            file_path,
            save_all=True,
            append_images=images[1:],
            force_update=True,
        )
