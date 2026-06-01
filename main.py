import argparse
import os
import traceback

from reader import PdfFileProcessor


class PDFProcessor:
    def __init__(self, path: str, output: str) -> None:
        self.path = path
        self.output = output

    @staticmethod
    def _parse_args():
        parser = argparse.ArgumentParser(
            description="Process pdf's and split them into separated WZ's."
        )
        parser.add_argument(
            "--path",
            type=str,
            help="Path to the directory with pdf files or some single pdf file.",
            required=True,
        )
        parser.add_argument("--output", type=str, help="Path to the output directory.")

        return parser.parse_args()

    @classmethod
    def create(cls) -> "PDFProcessor":
        kwargs = cls._parse_args()

        return cls(**kwargs.__dict__)

    def _process_single_file(self, file_path: str):
        """Attempts to claim and process a single file."""
        if not file_path.lower().endswith(".pdf") or not os.path.isfile(file_path):
            return

        original_dir = os.path.dirname(file_path)
        file_name = os.path.basename(file_path)
        processing_dir = os.path.join(original_dir, "processing")
        os.makedirs(processing_dir, exist_ok=True)

        claimed_path = os.path.join(processing_dir, file_name)

        try:
            # Atomic claim: move file to processing directory
            os.rename(file_path, claimed_path)
        except (OSError, FileNotFoundError):
            # File likely already claimed by another instance or moved
            return

        print(f"Processing: {file_name}")
        try:
            processor = PdfFileProcessor(
                claimed_path,
                output_dir=self.output,
                original_path=file_path,
            )
            processor.process_pdf()
            processor.save_all()
        except Exception as e:
            print(f"Error processing {file_name}: {e}")
            traceback.print_exc()
            # Move back on failure
            try:
                if os.path.exists(claimed_path):
                    os.rename(claimed_path, file_path)
                    print(f"Restored {file_name} to original location due to failure.")
            except Exception as restore_err:
                print(f"Failed to restore {file_name}: {restore_err}")

    def run(self):
        if os.path.isfile(self.path):
            self._process_single_file(self.path)
        elif os.path.isdir(self.path):
            # Get list of files first to avoid iterator issues if files move
            pdf_files = [
                f
                for f in os.listdir(self.path)
                if f.lower().endswith(".pdf")
                and os.path.isfile(os.path.join(self.path, f))
            ]

            if not pdf_files:
                print(f"No PDF files found in {self.path}")
                return

            print(
                f"Processing PDF files (total: {len(pdf_files)}) from directory: {self.path}."
            )
            for file_name in pdf_files:
                file_path = os.path.join(self.path, file_name)
                self._process_single_file(file_path)
        else:
            raise AttributeError(f"{self.path} is neither a directory nor a PDF file.")


if __name__ == "__main__":
    processor = PDFProcessor.create()
    processor.run()
