import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, relationship
import pytz

Base = declarative_base()
class Customer(Base):
    __tablename__ = "customer"
    customer_id = Column(String, primary_key=True)
    customer_name = Column(String, nullable=False, doc="Full name of the customer")
    customer_age = Column(Integer, nullable=False, doc="Age of the customer")
    customer_location = Column(String, doc="Name of the city, customer belongs to")



for col in Customer.__table__.columns:

    print(f" {col.name} {col.type} {col.doc}")