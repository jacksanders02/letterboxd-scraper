import argparse
import json
from typing import List

from fontTools.ttLib import TTFont

from scraper import LetterboxdReview


def char_not_in_font(unicode_char: str, font: TTFont) -> bool:
    """
    Checks whether a unicode character is not in a font.
    From https://stackoverflow.com/questions/43834362/python-unicode-rendering-how-to-know-if-a-unicode-character-is-missing-from-the
    :param unicode_char: the unicode character
    :param font: the font to check
    :return: True if `unicode_char` is not in font, otherwise False
    """
    for cmap in font['cmap'].tables:
        if cmap.isUnicode():
            if ord(unicode_char) in cmap.cmap:
                return False
    return True


def should_include(review: LetterboxdReview, fonts: List[TTFont]) -> bool:
    """
    Checks whether a letterboxd review should be included in the clean set.
    Reviews must be 100 words or less, and must be renderable by the chosen font
    :param review: the review to check
    :param fonts: the fonts which will be used to render the review
    :return: True if review should be included in the clean set, otherwise False
    """
    if len(review['text'].split()) > 100:
        return False

    for char in review['text']:
        if char != '\n' and all(char_not_in_font(char, font) for font in fonts):
            return False

    return True


def main() -> None:
    """
    The driver function for the program. Removes all long reviews, and ones that cannot be rendered
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True, help="File containing reviews to clean")
    parser.add_argument("-o", "--output", required=True, help="File where cleaned reviews will be stored")
    parser.add_argument("-f", "--fonts", nargs='+', required=True,
                        help="The font(s) which will be used to render the reviews")

    args = parser.parse_args()

    fonts = [TTFont(f) for f in args.fonts]

    with open(args.input, "r") as f:
        reviews = json.load(f)

    clean_reviews = []
    for review in reviews:
        if should_include(review, fonts):
            clean_reviews.append(review)

    print(f"Original reviews: {len(reviews)}\nCleaned reviews: {len(clean_reviews)}")
    with open(args.output, "w") as f:
        json.dump(clean_reviews, f, indent=4, ensure_ascii=False)


if __name__ == '__main__':
    main()
