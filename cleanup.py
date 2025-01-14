from app import app, db
from app.models import Review

def clean_up_duplicates():
    all_reviews = Review.query.all()
    unique_movies = {}

    for review in all_reviews:
        normalized_title = review.movie.strip().lower()
        if normalized_title not in unique_movies:
            unique_movies[normalized_title] = review.id
            review.movie = normalized_title
        else:
            # Duplicate found, delete the record
            db.session.delete(review)

    db.session.commit()
    print("Database cleanup complete: duplicates removed, and titles normalized.")

if __name__ == "__main__":
    with app.app_context():  # Ensure the application context is active
        clean_up_duplicates()
