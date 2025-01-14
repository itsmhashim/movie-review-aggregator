from flask import Blueprint, jsonify, request
from .models import db, Review
from .utils import fetch_movie_ratings

main = Blueprint('main', __name__)

@main.route('/')
def home():
    return jsonify({"message":"Welcome to the Movie Review Aggregator!"})

@main.route("/ratings", methods=["GET", "POST"])
def add_review():
    if request.method == "POST":
        data = request.get_json()
        if not data or not all(key in data for key in ["movie", "review", "rating"]):
            return jsonify({"error":"Invalid input"}), 400

        new_review=Review(
            movie=data["movie"],
            review=data["review"],
            rating=float(data["rating"])
        )

        db.session.add(new_review)
        db.session.commit()
        return jsonify({"message":"New review added"}), 201

    if request.method == "GET":

        movie=request.args.get("movie")
        min_rating=request.args.get("min_rating")
        sort_by=request.args.get("sort_by", "id")
        order=request.args.get("order", "asc")
        page=(request.args.get("page", 1))
        per_page=(request.args.get("per_page", 5))

        try:
            page=int(page)
            per_page=int(per_page)
            if page<=0 or per_page<=0:
                raise ValueError('Page and per_page must be positive.')
        except ValueError as e:
            return jsonify({"error":str(e)}), 400

        try:
            if min_rating:
                min_rating=float(min_rating)
        except ValueError:
            return jsonify({"error":"min_rating must be a number."}), 400

        if movie:
            movie_data=fetch_movie_ratings(movie)
            if 'error' in movie_data:
                return jsonify({"error":movie_data["error"]}), 404

        query=Review.query

        if movie:
            query=query.filter(Review.movie.ilike(f"%{movie}%"))
        if min_rating:
            query=query.filter(Review.aggregated_score >= min_rating)

        valid_sort_columns=['id', 'movie', 'rating', 'aggregated_score', 'last_updated']
        if sort_by not in valid_sort_columns:
            return jsonify({'error': f'Invalid sort value. Choose from {valid_sort_columns}.'}), 400

        if order =="desc":
            query=query.order_by(db.desc(getattr(Review, sort_by)))
        else:
            query=query.order_by(getattr(Review, sort_by))

        paginated_reviews=query.paginate(page=page, per_page=per_page, error_out=False)

        result=[
            {"id":review.id,
            "movie":review.movie,
            "review":review.review,
            "rating":review.rating,
            'aggregated_score':review.aggregated_score,
            'last_updated':review.last_updated
             }
            for review in paginated_reviews.items
        ]

        response={

            "page":paginated_reviews.page,
            "per_page":paginated_reviews.per_page,
            "total":paginated_reviews.total,
            "total_pages":paginated_reviews.pages,
            "reviews":result
        }
        return jsonify(response), 200

@main.route("/reviews/<int:review_id>", methods=["PUT", "DELETE"])
def manage_reviews(review_id):
    if request.method == "PUT":
        data = request.get_json()
        review=Review.query.get(review_id)

        if not review:
            return jsonify({"error":"Review not found"}), 404

        if "movie" in data:
            review.movie=data["movie"]
        if "review" in data:
            review.review=data["review"]
        if "rating" in data:
            review.rating=float(data["rating"])
        db.session.commit()
        return jsonify({"message":"Review updated"}), 200

    if request.method == "DELETE":
        review=Review.query.get(review_id)

        if not review:
            return jsonify({"error":"Review not found"}), 404

        db.session.delete(review)
        db.session.commit()
        return jsonify({"message":"Review deleted"}), 200

@main.route('/ratings/all', methods=["GET"])
def get_all_reviews():
    reviews = Review.query.all()
    result=[
        {
            'id':review.id,
            'movie':review.movie,
            'review':review.review,
            'ratings':review.rating,
            'aggregated_score':review.aggregated_score,
            'last_updated':review.last_updated
        }
        for review in reviews
    ]
    return jsonify(result), 200

