from flask import Flask
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

app = Flask(__name__)
api = Api(app)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///database.db"
# Flask-SQLAlchemy has its own event notification system that gets layered on top of SQLAlchemy.
# To do this, it tracks modifications to the SQLAlchemy session. This takes extra resources, so the option
# SQLALCHEMY_TRACK_MODIFICATIONS allows you to disable the modification tracking system.
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app, session_options={"autoflush": False})  # TODO: remove autoflush=False, this prevents from database to lock queries when accessed

# PyCharm code inspection error ignored in all Flask SQLAlchemy Models, see:
#   https://stackoverflow.com/questions/35242153/unresolved-attribute-column-in-class-sqlalchemy
class UsersModel(db.Model):
    # init columns
    user_id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(500), nullable=False)
    country_code = db.Column(db.String(100), nullable=False)
    user_email = db.Column(db.String(100), nullable=False)
    address_object = db.Column(db.PickleType())     # address_object is None when creating new user


class CouriersModel(db.Model):
    # init variables
    max_num_of_remaining_deliveries_var = 10
    # status variables
    available = 0
    full = 1
    # init columns
    query_id = db.Column(db.Integer, primary_key=True)
    courier_id = db.Column(db.Integer, nullable=False)
    num_of_remaining_deliveries = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.Integer, nullable=False)


class DeliveriesModel(db.Model):
    # status variables
    scheduled = 0
    completed = 1
    # init columns
    delivery_id = db.Column(db.Integer, primary_key=True)
    timeslot_id = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    courier_id = db.Column(db.Integer, nullable=False)
    user_email = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Integer, nullable=False)


class TimeslotsModel(db.Model):
    # status variables
    available = 0
    not_available = 1
    max_num_of_deliveries = 2
    # init columns
    timeslot_id = db.Column(db.Integer, primary_key=True)
    courier_id = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    num_of_scheduled_deliveries = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Integer, nullable=False)
    supported_addresses = db.Column(db.PickleType(), nullable=False)


def load_courier_timeslots(json_file):
    # all existing queries in timeslot table are deleted on start, to avoid duplicate timeslots
    TimeslotsModel.query.delete()
    CouriersModel.query.delete()
    DeliveriesModel.query.delete()

    with open(json_file) as data_file:
        data = json.load(data_file)
        # data is a dictionary of weekdays as keys and list of lists as value. The list of lists contains a list per timeslot
        # that consists of start time as int/float and a list of supported addresses
        courier_id = data["courier_id"]
        for date_str in data["timeslots"]:
            date_next_weekday = datetime.strptime(date_str, '%d/%m/%Y').date()
            year, month, day = [date_next_weekday.year, date_next_weekday.month, date_next_weekday.day]
            # new row for each date per courier - tracking total num of deliveries booked (max of 10)
            new_date_for_courier_table = CouriersModel(courier_id=courier_id,
                                                       num_of_remaining_deliveries=CouriersModel.max_num_of_remaining_deliveries_var,
                                                       date=date_next_weekday, status=CouriersModel.available)
            db.session.add(new_date_for_courier_table)
            timeslots_list = data["timeslots"][date_str]
            for timeslot in timeslots_list:
                timeslot_start_time_str, timeslot_end_time_str, supported_addresses_list = timeslot
                timeslot_start_time = datetime.strptime(timeslot_start_time_str, '%H:%M')
                timeslot_end_time   = datetime.strptime(timeslot_end_time_str, '%H:%M')
                new_timeslot_start_time = timeslot_start_time.replace(year=year, month=month, day=day)
                new_timeslot_end_time   = timeslot_end_time.replace(year=year, month=month, day=day)
                # new row for each timeslot per courier - tracking num of scheduled deliveries per timeslot (max of 2),
                # status. contains supported addresses info per timeslot
                new_timeslot = TimeslotsModel(courier_id=courier_id, start_time=new_timeslot_start_time,
                                              end_time=new_timeslot_end_time, date=date_next_weekday,
                                              num_of_scheduled_deliveries=0, status=TimeslotsModel.available,
                                              supported_addresses=supported_addresses_list)
                db.session.add(new_timeslot)

        db.session.commit()
