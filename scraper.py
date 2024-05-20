import json
from typing import List, TypedDict

import langdetect
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# Define custom type to return reviews as JSON
LetterboxdReview = TypedDict(
    'LetterboxdReview',
    {
        'id': str,
        'movie': str,
        'user': str,
        'rating': int,
        'link': str,
        'text': List[str]
    }
)


def parse_paragraphs(parent: BeautifulSoup) -> List[str]:
    """
    Helper class to retrieve paragraphs from a BeautifulSoup object.
    :param parent: the BeautifulSoup object to retrieve paragraphs from
    :return: a list of paragraphs
    """
    paras = []
    for para in parent.find_all('p'):
        for br in para.find_all('br'):
            br.replace_with('\n')
        paras.extend(para.text.split('\n'))
    return paras


def parse_letterboxd(url: str, exclude_list: List[str]) -> List[LetterboxdReview]:
    """
    Parses all letterboxd reviews from a URL.
    :param url: the URL containing a list of letterboxd reviews (i.e. a user page, or popular reviews)
    :param exclude_list: a list of phrases which should be excluded from results
    :return: a list of letterboxd reviews as JSON objects
    """
    all_reviews = []

    soup = BeautifulSoup(requests.get(url).text, 'html.parser')
    review_elems = soup.find('ul', class_='film-list').find_all('li')
    for review in tqdm(review_elems, desc='Reviews on page: ', leave=False):
        review_id = review.attrs['data-object-id']
        text_url = f'https://letterboxd.com/s/full-text/{review_id}/'
        full_text = parse_paragraphs(BeautifulSoup(requests.get(text_url).text, 'html.parser'))

        # Used to check text for language/banned words etc.
        check_text = ' '.join(full_text).lower()

        try:
            if (langdetect.detect(check_text) != 'en' or
                    any(banned_word in check_text for banned_word in exclude_list)):
                # Skip non-english/bad language reviews
                continue
        except langdetect.lang_detect_exception.LangDetectException:
            # Handle reviews with no text
            continue

        title = review.find('a')
        title_text = title.text
        review_link = 'https://letterboxd.com' + title.attrs['href']

        rating_elem = review.find('span', class_='rating')
        rating = -1

        if rating_elem is not None:
            for css_class in rating_elem.attrs['class']:
                if css_class.startswith('rated-'):
                    rating = int(css_class.split('-')[1])

        user = review.attrs['data-owner']

        all_reviews.append({
            'id': review_id,
            'movie': title_text,
            'user': user,
            'rating': rating,
            'link': review_link,
            'text': full_text
        })

    return all_reviews


if __name__ == '__main__':
    with open('banned_words.txt', 'r') as f:
        exclude_list = f.read().splitlines()

    langdetect.DetectorFactory.seed = 123
    reviews = []

    for i in tqdm(range(256), desc="Fetching popular reviews: Page "):
        reviews.extend(parse_letterboxd(f'https://letterboxd.com/reviews/popular/page/{i}/', exclude_list))

    print(len(reviews))

    with open('reviews.json', 'w') as f:
        json.dump(reviews, f, indent=4)