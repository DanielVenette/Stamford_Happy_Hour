from flask import Flask, render_template, request, url_for
from flask_wtf import FlaskForm
from werkzeug.utils import redirect
from wtforms import StringField, SelectField, SubmitField, FloatField, TextAreaField
from wtforms.validators import DataRequired, Length
from flask_bootstrap import Bootstrap
import psycopg2
import requests
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv

GAPIKEY = os.environ.get('GAPIKEY')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASKSECRETKEY')
Bootstrap(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:g04Postgres@localhost/happy_hour_astoria'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
load_dotenv()


class AddForm(FlaskForm):
    location = StringField('Location:', validators=[DataRequired('Field Cannot Be Blank')], render_kw={'autocomplete': 'off', 'class': 'form-control', 'id': 'autocomplete'})
    business_hh_description = TextAreaField(label="Happy Hour Description:", validators=[DataRequired('Field Cannot Be Blank')])
    submit = SubmitField('Submit')

class Businesses(db.Model):
    record_id = db.Column(db.Integer, primary_key=True)
    business_name = db.Column(db.String(100))
    description = db.Column(db.Text)
    lat = db.Column(db.Float)
    long = db.Column(db.Float)


@app.route("/")
def main():

    businesses = db.session.query(Businesses).order_by(Businesses.record_id).all()
    rows = [(business.record_id, business.business_name, business.description, business.lat, business.long) for business in businesses]

    return render_template("hhs1_google.htm", business_info=rows, key=GAPIKEY)


@app.route('/add', methods=['GET', 'POST'])
def add():
    form = AddForm()
    if form.validate_on_submit():
        location = form.location
        print(location.data)
        endpoint = 'https://maps.googleapis.com/maps/api/place/autocomplete/json'
        params = {
            'input': location.data,
            'types': 'establishment',
            'key': GAPIKEY
        }
        response = requests.get(endpoint, params=params)

        data = response.json()

        print(f"data: {data}")

        endpoint = 'https://maps.googleapis.com/maps/api/place/details/json'
        params2 = {
            'place_id': data['predictions'][0]['place_id'],
            'fields': 'name,formatted_address,geometry,formatted_phone_number,website',
            'key': GAPIKEY
        }

        response2 = requests.get(endpoint, params=params2)

        data2 = response2.json()

        lat = data2['result']['geometry']['location']['lat']
        lng = data2['result']['geometry']['location']['lng']
        name = data2['result']['name']
        description = form.business_hh_description.data

        conn = psycopg2.connect(
            dbname="happy_hour_astoria",
            user="postgres",
            password="g04Postgres",
            host="localhost"
        )

        cur = conn.cursor()

        sql_max = f"SELECT MAX(record_id) FROM public.businesses"
        cur.execute(sql_max)

        max_record_id = cur.fetchone()[0]
        next_record_id = max_record_id + 1

        sql = f"INSERT INTO businesses (record_id, business_name, description, lat, long) VALUES (%s, %s, %s, %s, %s)"
        values = (next_record_id, name, description, lat, lng)

        cur.execute(sql, values)

        conn.commit()

        cur.close()
        conn.close()

        return redirect(url_for('main'))

    else:
        print(form.errors)


    return render_template('add_google.html', form=form, key=GAPIKEY)

@app.route('/edit/<record_id>', methods=['GET', 'POST'])
def edit(record_id):
    business_to_edit = Businesses.query.get(record_id)
    print(business_to_edit.business_name)
    form = AddForm(obj=business_to_edit)
    form.location.data = business_to_edit.business_name
    form.business_hh_description.data = business_to_edit.description
    if form.validate_on_submit():
        # print("success")
        business_to_edit.description = request.form['business_hh_description']
        db.session.commit()
        return redirect(url_for('main'))
    else:
        print(form.errors)
    # form.process(obj=business_to_edit)
    return render_template('edit_google.html', business=business_to_edit, form=form, key=GAPIKEY)

@app.route("/delete/<record_id>")
def delete(record_id):
    business_to_delete = Businesses.query.get(record_id)
    db.session.delete(business_to_delete)
    db.session.commit()
    return redirect(url_for('main', _anchor='finder'))

if __name__ == "__main__":
    app.run(debug=True)
