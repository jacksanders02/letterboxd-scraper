from typing import List, TypedDict

import langdetect
import requests
from bs4 import BeautifulSoup

# Define custom type to return reviews as JSON
LetterboxdReview = TypedDict(
    'LetterboxdReview',
    {
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
        paras.append(para.text)
    return paras


def parse_letterboxd(url: str) -> List[LetterboxdReview]:
    """
    Parses all letterboxd reviews from a URL.
    :param url: the URL containing a list of letterboxd reviews (i.e. a user page, or popular reviews)
    :return: a list of letterboxd reviews as JSON objects
    """
    all_reviews = []

    soup = BeautifulSoup(requests.get(url).text, 'html.parser')
    reviews = soup.find('ul', class_='film-list').find_all('li')
    for review in reviews:
        text_url = f'https://letterboxd.com/s/full-text/{review.attrs['data-object-id']}/'
        full_text = parse_paragraphs(BeautifulSoup(requests.get(text_url).text, 'html.parser'))

        if langdetect.detect(' '.join(full_text)) != 'en':
            # Skip non-english reviews
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
            'movie': title_text,
            'user': user,
            'rating': rating,
            'link': review_link,
            'text': full_text
        })

    return all_reviews


if __name__ == '__main__':
    langdetect.DetectorFactory.seed = 123
    reviews = []

    reviews.extend(parse_letterboxd('https://letterboxd.com/hulls1/films/reviews/page/1'))
    reviews.extend(parse_letterboxd('https://letterboxd.com/hulls1/films/reviews/page/2'))
    reviews.extend(parse_letterboxd('https://letterboxd.com/hulls1/films/reviews/page/3'))
