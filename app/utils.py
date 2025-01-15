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
        all_movies= [review.movie for review in Review.query.all()]
        print(f"Movies in database: {all_movies}")

        original_movie = movie.strip()  # Keep the movie name as provided
        print(f"Checking for exact match in the database for: {original_movie}")

        # Step 1: Check for an exact match in the database
        exact_match = Review.query.filter(Review.movie.ilike(original_movie)).first()

        if exact_match:
            print(f"Exact match found in the database: {exact_match.movie}")
            return {
                'title': exact_match.movie,
                'ratings': exact_match.rating,
                'aggregated_score': exact_match.aggregated_score
            }

        # Step 2: Fetch from OMDb if no exact match
        print(f"No exact match found. Fetching from OMDb for: {original_movie}")
        params = {'t': original_movie, 'apikey': OMDB_API_KEY}
        response = requests.get(OMDB_BASE_URL, params=params)
        response.raise_for_status()

        data = response.json()
        if data.get('Response') == 'True':
            # Normalize ratings and save to database
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

            # Check again for an exact match using the title from OMDb
            omdb_title = data.get('Title')
            duplicate_check = Review.query.filter(Review.movie.ilike(omdb_title)).first()

            if duplicate_check:
                print(f"Duplicate movie found during insertion: {duplicate_check.movie}")
                return {
                    'title': duplicate_check.movie,
                    'ratings': duplicate_check.rating,
                    'aggregated_score': duplicate_check.aggregated_score
                }

            # Insert the new movie into the database
            new_movie = Review(
                movie=omdb_title,
                review='',  # Default empty review
                rating=normalized_ratings,
                aggregated_score=aggregated_score,
                last_updated=datetime.now()
            )
            db.session.add(new_movie)
            db.session.commit()
            print(f"Movie successfully added: {new_movie.movie}")

            return {
                'title': omdb_title,
                'ratings': normalized_ratings,
                'aggregated_score': aggregated_score
            }

        # Step 3: Fetch closest matches in the database if no exact match and no OMDb result
        print(f"Fetching closest matches in the database for: {original_movie}")
        closest_matches = Review.query.filter(Review.movie.ilike(f"%{original_movie}%")).all()

        if closest_matches:
            suggestions = [match.movie for match in closest_matches]
            print(f"Closest matches found: {suggestions}")
            return {
                'error': 'Exact match not found. Here are the closest matches:',
                'suggestions': suggestions
            }

        # No matches at all
        return {'error': 'Movie not found in database or OMDb, and no similar matches found.'}

    except requests.RequestException as e:
        print(f"Error fetching data from OMDb: {str(e)}")
        return {'error': str(e)}

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
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