"""
This is Add-On allows users to use Google Cloud Vision API to OCR a document. 
"""

import os
import requests
from documentcloud.addon import AddOn
from listcrunch import uncrunch
from tempfile import NamedTemporaryFile

class CloudVision(AddOn):
    """OCR your documents using Google Cloud Vision API"""
    def setup_credential_file(self):
        """Sets up Google Cloud credential file"""
        credentials = os.environ["TOKEN"]
        # put the contents into a named temp file
        # and set the var to the name of the file
        gac = NamedTemporaryFile(delete=False)
        gac.write(credentials.encode("ascii"))
        gac.close()
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = gac.name
    
    def validate(self):
        """Validate that we can run the translation"""
        if self.get_document_count() == 0:
            self.set_message(
                "It looks like no documents were selected. Search for some or "
                "select them and run again."
            )
            return False
        elif not self.org_id:
            self.set_message("No organization to charge.")
            return False
        else:
            num_chars = 0
            for document in self.get_documents():
                num_chars += len(document.full_text)
            cost = math.ceil(num_chars/75)
            resp = self.client.post(
                f"organizations/{self.org_id}/ai_credits/",
                json={"ai_credits": cost},
            )
            if resp.status_code != 200:
                self.set_message("Error charging AI credits.")
                return False
        return True
    
    def main(self):
        for document in self.get_documents():
            # get the dimensions of the pages
            page_spec = [map(float, p.split("x")) for p in uncrunch(document.page_spec)]
            if document.access != "public":
                self.set_message("Document must be public")
                return
            data = {
                "url": document.pdf_url,
                "isOverlayRequired": True,
                "language": document.language,
            }
            resp = requests.post(URL, headers={"apikey": os.environ["KEY"]}, data=data)
            results = resp.json()
            if results["IsErroredOnProcessing"]:
                self.set_message(f"Error")
                return
            pages = []
            for i, (page_results, (width, height)) in enumerate(
                zip(results["ParsedResults"], page_spec)
            ):
                # ocrspace dimensions need a correction factor for some reason
                width *= (4/3)
                height *= (4/3)

                page = {
                    "page_number": i,
                    "text": page_results["ParsedText"],
                    "ocr": "ocrspace1",
                    "positions": [],
                }
                for line in page_results["TextOverlay"]["Lines"]:
                    for word in line["Words"]:
                        page["positions"].append(
                            {
                                "text": word["WordText"],
                                "x1": (word["Left"] ) / width,
                                "y1": (word["Top"] ) / height,
                                "x2": (word["Left"] + word["Width"] ) / width,
                                "y2": (word["Top"] + word["Height"] ) / height,
                            }
                        )
                pages.append(page)
            self.client.patch(f"documents/{document.id}/", {"pages": pages})

if __name__ == "__main__":
    CloudVision().main()
