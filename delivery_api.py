import os
from flask import jsonify
from flask_restful import Resource
import requests
from datetime import timedelta
import holidayapi
import threading
from database_init import *
from api_keys import *


class Address:
    def __init__(self, street, home_num, city, country, country_code):
        self.street = street
        self.home_num = home_num
        self.city = city
        self.country = country
        self.country_code = country_code
        #self.postcode = postcode   # N/A for Israel


class User(Resource):
    # creates new user
    def post(self, address_str, country_code,  user_name, user_email):
        user = UsersModel.query.filter_by(user_email=user_email).first()
        if user:
            return jsonify({'message': 'User with this email is already in database'})

        elif self.is_valid_email(user_email) and self.is_valid_address(address_str) and self.is_valid_user_name(user_name)\
                and self.is_valid_country_code:
            new_user = UsersModel(user_name=user_name, address=address_str, country_code=country_code,
                                  user_email=user_email, address_object=None)
            db.session.add(new_user)
            db.session.commit()
            return jsonify({'message': 'User creasted successfully'})

        else:
            return jsonify({'message': 'Failed to create user. Wrong input'})   # TODO: specify which input is not correct


    def is_valid_email(self, user_email):
        # TODO: add functionality
        return True

    def is_valid_address(self, address_str):
        # TODO: add functionality
        return (address_str != "")

    def is_valid_user_name(self, user_name):
        # TODO: add functionality
        return (user_name != "")

    def is_valid_country_code(self, country_code):
        # TODO: add functionality
        return (country_code != "")


class ResolveAddress(Resource):
    def post(self, user_email):
        # resolve single line address into class, func accesses Google's Geocoding API
        user = UsersModel.query.filter_by(user_email=user_email).first()
        if user:
            address_str = user.address
            params = {'key': geocoding_api_key, 'address': address_str}
            base_url = 'https://maps.googleapis.com/maps/api/geocode/json?'
            response = requests.get(base_url, params=params).json()
            if response['status'] == 'OK':
                # extract the relevant info from the response
                address_components = response['results'][0]['address_components']
                home_num, street, city, country, country_code = ["", "", "", "", ""]
                for address_component in address_components:
                    if address_component['types'][0] == 'street_number':
                        home_num = address_component['long_name']

                    elif address_component['types'][0] == 'route':
                        street = address_component['long_name']

                    elif address_component['types'][0] == 'locality':
                        city = address_component['long_name']

                    elif address_component['types'][0] == 'country':
                        country = address_component['long_name']
                        country_code = address_component['short_name']  # country code is needed for accessing Holiday API

                resolved_address = Address(street, home_num, city, country, country_code)
                user.address_object = resolved_address
                db.session.commit()

                return jsonify({'message': 'Address object added to user\'s info'})

            elif response['status'] == 'ZERO_RESULTS':
                return jsonify({'message': 'Address does not exist. Please provide a valid address'})

            else:   # response['status'] is any other status
                return jsonify({'message': 'Something went wrong'})

        else:  # user does not exist in database
            return jsonify({'message': 'User does not exist. Please create user.'})


class Timeslots(Resource):
    # vars
    year_for_holiday_API = 2021

    def __init__(self):
        self.available_timeslots_list = []
        self.user_city                = ''
        self.user_country_code        = ''
        self.holidays                 = set()


    def post(self, user_email):
        # returns all available timeslots in the upcoming week for user's address contained in user table in db.
        # decision whether the address is supported by specific courier is based on user_city
        user = UsersModel.query.filter_by(user_email=user_email).first()
        if user:    # TODO: add a redirect to user creation if user does not exist in db
            self.user_country_code = user.country_code
            user_email = user.user_email
            # resolve address_str to object, if user has not done it yet
            # accessing geocoding and holidays API is done in parallel, using two threads
            if user.address_object is None:
                create_address_object_thread = threading.Thread(target=self.create_address_object, args=(user_email,))
                get_holidays_thread = threading.Thread(target=self.get_holidays)
                create_address_object_thread.start()
                get_holidays_thread.start()
                create_address_object_thread.join()
                get_holidays_thread.join()

            else:   # if user has address_object, only access holiday API
                self.user_city         = user.address_object.city
                self.user_country_code = user.address_object.country_code
                self.get_holidays()

            timeslots = TimeslotsModel.query.filter_by(status=TimeslotsModel.available).all()
            for timeslot in timeslots:
                courier_id    = timeslot.courier_id
                timeslot_date = timeslot.date
                courier       = CouriersModel.query.filter_by(courier_id=courier_id, date=timeslot_date).first()

                if courier.status == CouriersModel.available and self.is_city_in_supported_addresses(timeslot) \
                        and not self.is_holiday(timeslot):
                    self.add_to_available_timeslots(timeslot)

                elif self.is_holiday(timeslot):    # if date is holiday, update timeslot as not available
                    timeslot.status = TimeslotsModel.not_available

            db.session.commit()

            return self.available_timeslots_list

        else:   # user does not exist in database
            return jsonify({'message': 'User does not exist. Please create user to see available timeslots'})


    def add_to_available_timeslots(self, timeslot):
        start_time      = timeslot.start_time
        start_time_str  = start_time.strftime('%d/%m/%Y, %H:%M')
        end_time        = timeslot.end_time
        end_time_str    = end_time.strftime('%d/%m/%Y, %H:%M')
        timeslot_string = '{}-{}'.format(start_time_str, end_time_str)
        timeslot_id_str = str(timeslot.timeslot_id)
        self.available_timeslots_list.append([timeslot_id_str, timeslot_string])


    def is_city_in_supported_addresses(self, timeslot):
        supported_addresses_list = timeslot.supported_addresses
        return (self.user_city in supported_addresses_list)


    def is_holiday(self, timeslot):
        date = timeslot.date.date()# TODO: check if needed
        return (date in self.holidays)


    def get_holidays(self):
        hapi       = holidayapi.v1(holiday_api_key)
        # year set to 2021 due to limitation of free version of holiday API, contains info about the past, not curr year
        # tested dates (from courier_timeslots.json) are set in 2021
        parameters = { 'country': self.user_country_code, 'year': self.year_for_holiday_API }

        try:
            holidays_dict = hapi.holidays(parameters)
            holidays = holidays_dict['holidays']
            for holiday in holidays:
                # all holidays from dict are add to the holidays set (even though some holidays in Irsrael are considered workdays)
                # TODO: check which holiday is a workday
                holiday_datetime_obj = datetime.strptime(holiday['date'], '%Y-%m-%d')
                self.holidays.add(holiday_datetime_obj.date())
        except:
            print("An error occurred")


    def create_address_object(self, user_email):
        # resolve single line address into class, func accesses Google's Geocoding API (could not use func from ResolveAddress
        # class because this function runs in a separate thread and class attribute user_city needs an update
        user = UsersModel.query.filter_by(user_email=user_email).first()
        if user:
            address_str = user.address
            params = { 'key': geocoding_api_key, 'address': address_str }
            base_url = 'https://maps.googleapis.com/maps/api/geocode/json?'
            response = requests.get(base_url, params=params).json()
            if response['status'] == 'OK':
                # extract the relevant info from the response
                address_components = response['results'][0]['address_components']
                home_num, street, city, country, country_code = ["", "", "", "", ""]
                for address_component in address_components:
                    if address_component['types'][0] == 'street_number':
                        home_num = address_component['long_name']

                    elif address_component['types'][0] == 'route':
                        street = address_component['long_name']

                    elif address_component['types'][0] == 'locality':
                        self.user_city = address_component['long_name']

                    elif address_component['types'][0] == 'country':
                        country = address_component['long_name']
                        country_code = address_component['short_name']

                resolved_address = Address(street, home_num, self.user_city, country, country_code)
                user.address_object = resolved_address
                db.session.commit()

            elif response['status'] == 'ZERO_RESULTS':
                return jsonify({'message': 'Address does not exist. Please provide a valid address'})

            else:
                return jsonify({'message': 'Something went wrong'})

        else:  # user does not exist in database
            return jsonify({'message': 'User does not exist. Please create user.'})


class DeliveryBooking(Resource):
    def post(self, user_email, timeslot_id):
        # func books a delivery for user provided timeslot_id
        user = UsersModel.query.filter_by(user_email=user_email).first()
        if user:
            timeslot = TimeslotsModel.query.filter_by(timeslot_id=timeslot_id).with_for_update().first()
            if timeslot.status == TimeslotsModel.available:
                timeslot_date = timeslot.date
                courier_id    = timeslot.courier_id
                new_delivery  = DeliveriesModel(timeslot_id=timeslot_id, date=timeslot_date, courier_id=courier_id,
                                                user_email=user_email, status=DeliveriesModel.scheduled)
                db.session.add(new_delivery)
                courier = CouriersModel.query.filter_by(courier_id=courier_id).first()
                # courier status update
                if courier.num_of_remaining_deliveries > 0: # courier not fully booked
                    courier.num_of_remaining_deliveries -= 1
                    if courier.num_of_remaining_deliveries == 0:
                        courier.status = CouriersModel.full

                # timeslot status update
                if timeslot.num_of_scheduled_deliveries < TimeslotsModel.max_num_of_deliveries:
                    timeslot.num_of_scheduled_deliveries += 1
                    if timeslot.num_of_scheduled_deliveries == TimeslotsModel.max_num_of_deliveries:
                        timeslot.status = TimeslotsModel.not_available

                db.session.commit()

                return jsonify({'message': 'Delivery booked!'})

            else:   # timeslot is not available
                return jsonify({'message': 'Timeslot is not available. Please choose another timeslot'})

        else:   # user does not exist in database
            return jsonify({'message': 'User does not exist. Please create user to book a timeslot'})


def create_delivery_strings_list(delivery_queries_list):
    deliveries_list = []
    for delivery_query in delivery_queries_list:
        delivery_id       = delivery_query.delivery_id
        timeslot_id       = delivery_query.timeslot_id
        delivery_date     = delivery_query.date
        delivery_date_str = delivery_date.strftime('%d/%m/%Y')
        delivery_string   = 'Delivery ID: {}, Timeslot ID: {}, Delivery date: {}'.format(delivery_id, timeslot_id, delivery_date_str)
        deliveries_list.append(delivery_string)
    return deliveries_list


class Deliveries(Resource):
    def post(self, user_email, delivery_id):
        # marks delivery as complete
        user     = UsersModel.query.filter_by(user_email=user_email).first()
        delivery = DeliveriesModel.query.filter_by(delivery_id=delivery_id).first()
        if user and delivery:
            delivery.status = DeliveriesModel.completed
            db.session.commit()
            return jsonify({'message': 'Delivery completed'})

        elif user and not delivery:   # user exists, but no delivery with delivery_id exists
            return jsonify({'message': 'Delivery does not exist'})

        else:   # user does not exist in database
            return jsonify({'message': 'User does not exist'})


    def delete(self, user_email, delivery_id):
        # cancels a delivery
        user     = UsersModel.query.filter_by(user_email=user_email).first()
        delivery = DeliveriesModel.query.filter_by(delivery_id=delivery_id).first()
        if user and delivery:
            courier_id = delivery.courier_id
            courier    = CouriersModel.query.filter_by(courier_id=courier_id).first()
            # courier status update
            if courier.num_of_remaining_deliveries < CouriersModel.max_num_of_remaining_deliveries_var: # courier not fully booked
                courier.num_of_remaining_deliveries += 1
                if courier.status == CouriersModel.full:
                    courier.status = CouriersModel.available

            # timeslot status update
            timeslot_id = delivery.timeslot_id
            timeslot    = TimeslotsModel.query.filter_by(timeslot_id=timeslot_id).first()
            if timeslot.num_of_scheduled_deliveries > 0:
                timeslot.num_of_scheduled_deliveries -= 1
            if timeslot.status == TimeslotsModel.not_available:  # status before deletion was full
                timeslot.status = TimeslotsModel.available

            db.session.delete(delivery)
            db.session.commit()
            return jsonify({'message': 'Delivery deleted'})

        elif user and not delivery:
            return jsonify({'message': 'Delivery does not exist'})

        else:  # user does not exist in database
            return jsonify({'message': 'User does not exist'})


    def get(self):
        # returns list of daily deliveries
        #today = datetime.now()
        # today's date is simulated for testing as the Holiday API provides info for 2021
        today            = datetime(2021, 7, 19)
        date_today       = today.replace(hour=0, minute=0, second=0, microsecond=0)
        daily_deliveries = DeliveriesModel.query.filter_by(date=date_today).all()
        if daily_deliveries:
            daily_deliveries_list = create_delivery_strings_list(daily_deliveries)
            return daily_deliveries_list

        else:   # no deliveries today
            return jsonify({'message': 'No deliveries today'})


class WeeklyDeliveries(Resource):
    # vars
    num_of_days_for_display = 7

    def __init__(self):
        self.curr_week_dates_list = []


    def get(self):
        # retrieves all weekly deliveries (starting from today)
        self.create_curr_week_dates_list()
        weekly_deliveries_list = []
        for date in self.curr_week_dates_list:
            curr_date_deliveries = DeliveriesModel.query.filter_by(date=date).all()
            if curr_date_deliveries:
                curr_date_deliveries_list = create_delivery_strings_list(curr_date_deliveries)
                weekly_deliveries_list += curr_date_deliveries_list

        if weekly_deliveries_list:
            return weekly_deliveries_list

        else:   # no deliveries this week
            return jsonify({'message': 'No deliveries this week'})

    def create_curr_week_dates_list(self):
        # creates list of dates for current week for displaying weekly deliveries
        #today = datetime.now()
        # today's date is simulated for testing as the Holiday API provides info for 2021
        today      = datetime(2021, 7, 17)
        date_today = today.replace(hour=0, minute=0, second=0, microsecond=0)
        for days_delta in range(self.num_of_days_for_display):
            date = date_today + timedelta(days=days_delta)
            self.curr_week_dates_list.append(date)



# API build
api.add_resource(User, "/create-user/<string:address_str>/<string:country_code>/<string:user_name>/<string:user_email>")
api.add_resource(ResolveAddress, "/resolve-address/<string:user_email>")
api.add_resource(Timeslots, '/timeslots/<string:user_email>')
api.add_resource(DeliveryBooking, '/deliveries/<string:user_email>/<string:timeslot_id>')
api.add_resource(Deliveries, '/deliveries/<string:user_email>/<string:delivery_id>/completed',
                             '/deliveries/<string:user_email>/<string:delivery_id>', '/deliveries/daily')
api.add_resource(WeeklyDeliveries, '/deliveries/weekly')


if __name__ == '__main__':
    database_filename = os.path.abspath(os.getcwd()) + "/database.db"
    if not os.path.exists(database_filename):
        db.create_all()
    load_courier_timeslots('courier_timeslots.json')
    app.run(debug=False)
