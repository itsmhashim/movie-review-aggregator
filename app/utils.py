import requests
from datetime import datetime, timedelta
from .models import db, Review
import os
from dotenv import load_dotenv

load_dotenv()

OMDB_API_KEY = os.getenv('OMDB_API_KEY')
if not OMDB_API_KEY:
    raise Exception("OMDB_API_KEY not set.")

OMDB_BASE_URL = 'https://www.omdbapi.com/'

CACHE_EXPIRY_DAYS = 365

def fetch_movie_ratings(movie):
    try:
        print(f"Movies in database: {[review.movie for review in Review.query.all()]}")  # Debug
        # Check if the movie already exists in the database
        print(f"Checking for existing movie: {movie}")  # Debug
        existing_movie = Review.query.filter(Review.movie.ilike(movie)).first()

        if existing_movie:
            print(f"Movie found in database: {movie}")  # Debug
            return {
                'title': existing_movie.movie,
                'ratings': existing_movie.rating,
                'aggregated_score': existing_movie.aggregated_score
            }

        # Fetch fresh data from OMDb if not in the database
        print(f"Fetching data from OMDb for movie: {movie}")  # Debug
        params = {'t': movie, 'apikey': OMDB_API_KEY}
        response = requests.get(OMDB_BASE_URL, params=params)
        response.raise_for_status()

        data = response.json()
        if data.get('Response') == 'False':
            print(f"Movie not found on OMDb: {movie}")  # Debug
            return {'error': 'Movie not found'}

        # Normalize ratings
        ratings = data.get('Ratings', [])
        normalized_ratings = [
            {
                'source': rating['Source'],
                'value': normalize_rating(rating['Source'], rating['Value'])
            }
            for rating in ratings
            if rating['Source'] in ['Internet Movie Database', 'Rotten Tomatoes', 'Metacritic']
        ]
        aggregated_score = aggregate_ratings(normalized_ratings)

        # Insert the new movie into the database
        print(f"Inserting new movie into database: {movie}")  # Debug
        new_movie = Review(
            movie=data.get('Title'),
            review='',  # Default empty review
            rating=normalized_ratings,
            aggregated_score=aggregated_score,
            last_updated=datetime.now()
        )
        db.session.add(new_movie)
        db.session.commit()
        print(f"Movie successfully added: {new_movie.movie}")

        return {
            'title': data.get('Title'),
            'ratings': normalized_ratings,
            'aggregated_score': aggregated_score
        }

    except requests.RequestException as e:
        print(f"Error fetching data from OMDb: {str(e)}")  # Debug
        return {'error': str(e)}

    except Exception as e:
        print(f"Unexpected error: {str(e)}")  # Debug
        return {'error': str(e)}



def normalize_rating(source, value):

    if source=='Internet Movie Database':
        return float(value.split('/')[0])*10
    if source=='Rotten Tomatoes':
        return float(value.strip('%'))
    if source=='Metacritic':
        return float(value.split('/')[0])

def aggregate_ratings(ratings):

    valid_ratings=[r['value']for r in ratings if r['value'] is not None]
    return round(sum(valid_ratings) / len(valid_ratings), 2) if valid_ratings else None