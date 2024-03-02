import argparse
import datetime
import os
import shutil

try:
    import PIL
except ImportError as exc:
    raise ImportError("The Pillow library could not be imported. Is it installed? Is your venv activated?") from exc

from auto_magor_full import MagazineCreator, Cover


class Article:

    def __init__(self):
        self.title = ""
        self.subtitle = ""
        self.author = ""
        self.date = ""
        self.image_path = ""
        self.text_path = ""
        self.source = ""
        self.paragraphs = []

    def __repr__(self):
        return f"Article<{self.text_path} - {self.title}>"


def main(use_ink_saver: bool, blank_page_after_cover: bool):
    print("-- Auto Magor --")

    os.makedirs("to_process", exist_ok=True)
    files = os.listdir("to_process")
    files = [f for f in files if f.endswith('.txt')]
    files = sorted(files)
    if not files:
        path = os.path.join(os.getcwd(), "to_process")
        raise FileNotFoundError(f"No articles found in the to_process directory. {path}")

    articles = []
    for f in files:
        path = os.path.join("to_process", f)
        with open(path, 'r', encoding='utf-8') as fp:
            text = fp.read().strip()
        lines = text.splitlines()
        article = Article()
        article.text_path = f

        body_start = 0
        for index, line in enumerate(lines):
            if line.startswith("title:"):
                article.title = line[6:].strip()
            elif line.startswith("subtitle:"):
                article.subtitle = line[9:].strip()
            elif line.startswith("author:"):
                article.author = line[7:].strip()
            elif line.startswith("date:"):
                article.date = line[5:].strip()
            elif line.startswith("source:"):
                article.source = line[7:].strip()
            elif line.startswith("image:"):
                article.image_path = line[6:].strip()
                if article.image_path:
                    ext = article.image_path.split(".")[-1].lower()
                    if ext not in ('png', 'jpg', 'jpeg'):
                        article.image_path = ""
            elif line.startswith("body:"):
                body_start = index + 1
                break

        if body_start == 0:
            raise Exception(f"{article.text_path} is missing 'body:'")

        article.paragraphs = lines[body_start:]
        assert article.paragraphs, f"{article.text_path} has no text in body"
        articles.append(article)

    if os.path.isdir("pages"):
        shutil.rmtree("pages")

    cover = Cover(articles, blank_page_after_cover)
    cover.create()

    creator = MagazineCreator(articles, use_ink_saver)
    creator.create()

    pages = [f for f in os.listdir("pages")]
    pages = sorted(pages)
    page_images = []
    for page in pages:
        path = os.path.join("pages", page)
        page_images.append(PIL.Image.open(path).convert("RGB"))

    pdf = page_images[0]
    date_str = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    magazine_file_name = f"magazine_{date_str}.pdf"
    pdf.save(magazine_file_name, save_all=True, append_images=page_images[1:])
    print("Magazine Created:")
    print(magazine_file_name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="AutoMagor")
    parser.add_argument("--create", help="Create magazine", action='store_true')
    parser.add_argument("--no-ink-saver", help="Do not apply the ink saver image", action='store_true')
    parser.add_argument("--blank-page-after-cover",
                        help="Add a blank page after the cover. Useful if you print on both sides, but don't want to "
                             "print on the back of the cover page.",
                        action='store_true')
    args = parser.parse_args()

    if args.create:
        main(not args.no_ink_saver, args.blank_page_after_cover)
    else:
        parser.print_help()
