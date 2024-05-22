import argparse
import json
import os
import traceback
from typing import List, Dict

import requests
from tqdm import tqdm

from prisma import Prisma
from prisma.models import Movie, Worker, Review, CrewMember

from dotenv import dotenv_values
from urllib.parse import quote_plus
from scraper import LetterboxdReview


def create_crew_for(movie: Movie, crew_list: List[str], role: str) -> None:
    """
    Creates CrewMember models for everybody with a given role
    :param movie: the movie that the crew member belongs to
    :param crew_list: a list of names to create CrewMember models for
    :param role: the role of the crew members
    """
    for cm in crew_list:
        wiki_link = f'https://en.wikipedia.org/wiki/{cm.replace(" ", "_")}'

        # Find or create worker
        worker = Worker.prisma().upsert(
            where={
                'name': cm,
            },
            data={
                'update': {},
                'create': {
                    'name': cm,
                    'link': wiki_link
                }
            },
        )

        # Find crew member
        existing_crew = CrewMember.prisma().find_unique(
            where={
                'movieId_workerId': {'movieId': movie.id, 'workerId': worker.id}
            }
        )

        if existing_crew is not None:
            new_role = existing_crew.role + f' + {role}'
        else:
            new_role = role

        # Create crew member link
        CrewMember.prisma().upsert(
            where={
                'movieId_workerId': {'movieId': movie.id, 'workerId': worker.id}
            },
            data={
                'update': {
                    'role': new_role
                },
                'create': {
                    'movieId': movie.id,
                    'workerId': worker.id,
                    'role': role
                }
            },
        )


def create_movie_model(config: Dict, movie_name: str) -> Movie:
    """
    Collects data about a movie and creates a model.
    :param config: the .env config containing the OMDB API key
    :param movie_name: the name of the movie
    :return: the movie model
    """

    url_encoded = quote_plus(movie_name)
    movie_data = requests.get(f'https://www.omdbapi.com/?t={url_encoded}&apikey={config["OMDB_KEY"]}').json()
    movie = Movie.prisma().create(
        data={
            'id': movie_data['imdbID'],
            'title': movie_name,
            'year': int(movie_data['Year'].split('–')[0]),  # Split to handle series (2021-2024 etc.)
            'genre': movie_data['Genre'],
            'poster': movie_data['Poster'],
            'criticRating': float(movie_data['imdbRating'] if movie_data['imdbRating'] != 'N/A' else -1)
        }
    )

    actors = movie_data['Actors'].split(', ')
    directors = movie_data['Director'].split(', ')

    create_crew_for(movie, actors, 'Actor')
    create_crew_for(movie, directors, 'Director')

    return movie


def create_review_model(review: LetterboxdReview, movie_id: str):
    """
    Creates and stores a model for a given review
    :param review: the review to create a model for
    :param movie_id: the ID of the movie to which the review belongs
    :return:
    """
    review_id = int(review['id'].replace('viewing:', ''))

    Review.prisma().upsert(
        where={
            'id': review_id
        },
        data={
            'update': {
                'id': review_id,
                'reviewer': review['user'],
                'link': review['link'],
                'text': review['text'],
                'rating': review['rating']
            },
            'create': {
                'id': review_id,
                'movieId': movie_id,
                'reviewer': review['user'],
                'link': review['link'],
                'text': review['text'],
                'rating': review['rating']
            }
        },
    )


def main(config: Dict) -> None:
    """
    The driver function for the program
    :param config: dictionary storing environment variables retrieved from .env
    """

    parser = argparse.ArgumentParser()

    parser.add_argument('review_file')

    args = parser.parse_args()
    # Load cached reviews
    with open(args.review_file, 'r') as f:
        reviews = json.load(f)

    # Load cached film IDs
    if os.path.exists("movies.json"):
        with open('movies.json', 'r') as f:
            movies = json.load(f)
    else:
        movies = {}

    # Connect to postgres DB
    db = Prisma(auto_register=True)
    db.connect()
    crash_movie = ""
    try:
        for review in tqdm(reviews, desc='Building models'):
            if movies.get(review['movie'].lower()) is None:
                crash_movie = review['movie']
                movie_id = create_movie_model(config, review['movie']).id
                movies[review['movie'].lower()] = movie_id
            else:
                movie_id = movies[review['movie'].lower()]

            create_review_model(review, movie_id)
    except Exception as e:
        print(f"Crashed on {crash_movie}")
        traceback.print_exc()

    # Close connection and write current movies to file in case of failure
    db.disconnect()
    with open('movies.json', 'w') as f:
        json.dump(movies, f, indent=4, ensure_ascii=False)


if __name__ == '__main__':
    main(dotenv_values())
