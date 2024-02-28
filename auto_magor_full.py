import datetime
import os

from PIL import Image, ImageDraw, ImageFont

COLUMN_MAX_WIDTH = 437
COLUMN_SHORT_MAX_HEIGHT = 1378
COLUMN_LONG_MAX_HEIGHT = 1908
LINE_HEIGHT_CHARS = "pqgy,)"  # Characters that hang low to find the "max height" of a column

HERE = os.path.dirname(os.path.abspath(__file__))


class MagazineCreator:

    def __init__(self, articles):
        self.articles = articles

        self.font_body = ImageFont.truetype("times.ttf", 25)
        self.font_author = ImageFont.truetype("times.ttf", 26)
        self.font_title = ImageFont.truetype("timesbd.ttf", 33)
        self.font_subtitle = ImageFont.truetype("timesi.ttf", 28)

        self.out = Image.new("RGB", (1530, 1980), (255, 255, 255))
        self.draw = ImageDraw.Draw(self.out)

        self.page_number = 1
        self.column_number = 1
        self.column_text = ""
        self.column_max_height = COLUMN_SHORT_MAX_HEIGHT
        self.is_under_header = True
        self.height2_cache = None

    def create(self):
        os.makedirs("pages", exist_ok=True)

        article_count = len(self.articles)
        for index, article in enumerate(self.articles):
            print(f"\nProcessing ({index + 1:02}/{article_count:02}): {article.text_path}")
            is_last_page = index == article_count - 1
            self._write_article(article, is_last_page)
            print()

        print("\n")

    def _write_article(self, article, is_last_page):
        self.height2_cache = None
        page_number = 1
        is_first_page = True
        page_reuse = self.column_number != 1  # An article may reuse an existing page
        x = 554 if page_reuse else 87
        self.column_max_height = COLUMN_SHORT_MAX_HEIGHT

        image = os.path.join(HERE, "default.png")
        is_using_default = True
        if article.image_path:
            is_using_default = False
            image = f"to_process\\{article.image_path}"

        # Article Image
        with open(image, "rb") as fp:
            with open(os.path.join(HERE, "ink_saver.png"), "rb") as fps:
                ims = Image.open(fps)
                ims = ims.convert("RGBA")
                ims = ims.resize((900, 415))

                im = Image.open(fp)
                im = im.convert("RGBA")
                im = im.resize((900, 415))

                final = Image.new("RGBA", im.size)
                final = Image.alpha_composite(final, im)
                if not is_using_default:
                    final = Image.alpha_composite(final, ims)

        self.out.paste(final, box=(x, 35))

        # Title
        # TODO function for this max line write
        title = article.title.split(" ")
        title_apply = title[0]
        dots = "..."
        dot_length = self.draw.textlength(dots, self.font_title)
        max_length = 900 - dot_length
        for word in title[1:]:
            new_chunk = f" {word}"
            new_len = self.draw.textlength(f"{title_apply}{new_chunk}", self.font_title)
            if new_len < max_length:
                title_apply += new_chunk
            else:
                title_apply += dots
                break
        self.draw.text((x, 450), title_apply, font=self.font_title, fill=(0, 0, 0))

        # Subtitle
        subtitle = article.subtitle.split(" ")
        title_apply = subtitle[0]
        dots = "..."
        dot_length = self.draw.textlength(dots, self.font_subtitle)
        max_length = 900 - dot_length
        for word in subtitle[1:]:
            new_chunk = f" {word}"
            new_len = self.draw.textlength(f"{title_apply}{new_chunk}", self.font_subtitle)
            if new_len < max_length:
                title_apply += new_chunk
            else:
                title_apply += dots
                break
        self.draw.text((x, 490), title_apply, font=self.font_subtitle, fill=(0, 0, 0))

        # Author and Date
        author_line = ""
        if article.author:
            author_line += f"by {article.author}   "
        if article.date:
            author_line += f"{article.date.title()}   "
        if article.source:
            author_line += f"{article.source}   "
        author_line = author_line.split(" ")
        title_apply = author_line[0]
        dots = "..."
        dot_length = self.draw.textlength(dots, self.font_author)
        max_length = 900 - dot_length
        for word in author_line[1:]:
            new_chunk = f" {word}"
            new_len = self.draw.textlength(f"{title_apply}{new_chunk}", self.font_author)
            if new_len < max_length:
                title_apply += new_chunk
            else:
                title_apply += dots
                break

        self.draw.text((x, 523), title_apply, font=self.font_author, fill=(0, 0, 0))

        # Solid Line
        x2 = 1454 if page_reuse else 987
        self.draw.line(((x, 560), (x2, 560)), fill=(0, 0, 0), width=5)

        # Text
        start_of_paragraph = True
        for paragraph in article.paragraphs:
            words = paragraph.split(" ")
            # Start of a column, and it's a blank line from the paragraph is a blank line
            if self.column_text == "" and words == [""]:
                continue
            if words == [""]:
                self.column_text += "\n"
                continue

            print('.', end='', flush=True)
            word_index = 0
            while word_index < len(words):
                assert self.column_number in (1, 2, 3), self.column_number

                word = words[word_index]
                if start_of_paragraph or self.column_text == "":
                    new_chunk = word
                    start_of_paragraph = False
                    self.height2_cache = None
                else:
                    new_chunk = f" {word}"

                width, height = self.get_column_width_height(f"{self.column_text}{new_chunk}")
                # The new lines from paragraphs can push a column over. So we check it, but cache it for speed.
                if self.height2_cache is None:
                    _, self.height2_cache = self.get_column_width_height(f"{self.column_text}{LINE_HEIGHT_CHARS}")
                if width <= COLUMN_MAX_WIDTH and self.height2_cache < self.column_max_height:  # Fits on current line
                    self.column_text += new_chunk
                else:
                    # Check if another line can still fit in the current column
                    _, height = self.get_column_width_height(f"{self.column_text}\n{LINE_HEIGHT_CHARS}")
                    if height < self.column_max_height:  # Column still has room for another line
                        self.column_text += f"\n{word}"  # Is at the start of a new line
                    else:  # Column is full. Write current column and prepare next column.
                        self._write_column(is_first_page, page_reuse)

                        # Set next column
                        self.column_text = ""
                        if self.column_number == 3:
                            self.save_page(article, page_number)
                            page_number += 1

                            self.reset_draw_page()
                            is_first_page = False
                            self.column_number = 1
                            if page_reuse:
                                page_reuse = False
                                self.column_max_height = COLUMN_LONG_MAX_HEIGHT
                        else:
                            self.column_number += 1

                        continue  # Redo the word with the new column, so do not increment word_index

                word_index += 1

            # New paragraph is next
            self.column_text += "\n"
            start_of_paragraph = True

        # Note: There can be a redundant save_page in order to catch a left over final page
        # Finished this article
        if self.column_text.strip():
            self._write_column(is_first_page, page_reuse)
            if is_last_page:
                self.save_page(article, page_number)

        # -- Prepare for next article

        # This article was only one page
        if is_first_page:
            self.column_number = 1
            self.save_page(article, page_number)
            self.reset_draw_page()
        else:
            if self.column_number == 1:  # Next article will go on this page
                self.column_number += 1
            else:  # Save this page and prepare for next article
                self.column_number = 1
                self.save_page(article, page_number)
                self.reset_draw_page()

        self.column_text = ""

    def get_column_width_height(self, text):
        _, _, width, height = self.draw.multiline_textbbox((0, 0), text,
                                                           font=self.font_body)
        return width, height

    def save_page(self, article, page_number):
        page_file_name = f"{article.text_path[:-4]}_{page_number:02d}.png"
        self.out.save(f"pages\\{page_file_name}")

    def reset_draw_page(self):
        self.out = Image.new("RGB", (1530, 1980), (255, 255, 255))
        self.draw = ImageDraw.Draw(self.out)

    def _write_column(self, is_first_page, page_reuse):
        xy = None
        if is_first_page:
            if self.column_number == 1:
                xy = (87, 570)
            elif self.column_number == 2:
                xy = (554, 570)
                if not page_reuse:
                    self.column_max_height = COLUMN_LONG_MAX_HEIGHT
            elif self.column_number == 3:
                y = 570 if page_reuse else 35
                xy = (1008, y)
        else:
            assert not page_reuse
            if self.column_number == 1:
                xy = (87, 35)
            elif self.column_number == 2:
                xy = (554, 35)
            elif self.column_number == 3:
                xy = (1008, 35)

        self.draw.multiline_text(xy, self.column_text, font=self.font_body, fill=(0, 0, 0))


class Cover:

    def __init__(self, articles):
        self.articles = articles

        self.font_date = ImageFont.truetype("times.ttf", 50)
        self.font_text = ImageFont.truetype("timesi.ttf", 40)

        self.out = Image.new("RGB", (1530, 1980), (255, 255, 255))
        self.draw = ImageDraw.Draw(self.out)

    def create(self):
        os.makedirs("pages", exist_ok=True)

        image = os.path.join(HERE, "default.png")
        with open(image, "rb") as fp:
            im = Image.open(fp)
            im = im.convert("RGBA")
            im = im.resize((900, 415))

        x = int((1530/2) - (900/2))
        self.out.paste(im, box=(x, 35))

        date_str = datetime.datetime.now().strftime("%Y / %m / %d")
        _, _, width, height = self.draw.multiline_textbbox((0, 0), date_str,
                                                           font=self.font_date)
        x = int((1530/2) - (width/2))
        self.draw.text((x, 450), date_str, font=self.font_date, fill=(0, 0, 0))

        y = 600
        # List the first 15 article titles
        for index, article in enumerate(self.articles[:15]):
            number = index + 1
            number = str(number) if number >= 10 else f" {number}"
            title = article.title.split(" ")
            title_apply = f"{number}. {title[0]}"
            for word in title[1:]:
                new_chunk = f" {word}"
                new_len = self.draw.textlength(f"{title_apply}{new_chunk}", self.font_text)
                if new_len < 1400:
                    title_apply += new_chunk
                else:
                    title_apply += "..."
                    break

            self.draw.text((35, y), title_apply, font=self.font_text, fill=(0, 0, 0))
            y += 85

        self.out.save(f"pages\\000cover.png")
