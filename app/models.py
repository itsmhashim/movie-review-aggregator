from . import db
from datetime import datetime
from sqlalchemy.dialects.sqlite import JSON

class Review(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    movie=db.Column(db.String(100), nullable=False, unique=True)
    review=db.Column(db.Text, nullable=False, default='')
    rating=db.Column(JSON, nullable=False)
    aggregated_score=db.Column(db.Float, nullable=False)
    last_updated=db.Column(db.DateTime, nullable=False, default=datetime.now)


    def to_dict(self):
        return {
            "id": self.id,
            "movie": self.movie,
            "review": self.review,
            "rating": self.rating
        }