from app import flask_app as app
from flask import render_template, request, send_file
import psycopg2 as psql
import json
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib import figure
import io
import base64

#Database parameters
params = {
    'user': "ubuntu",
    'password': "password",
    'dbname': 'dvdrentals',
    'host': 'localhost',
    'port': 5432
}

@app.route("/", methods=["GET"])
def index():

    return render_template('homepage.html')

#Use flask to create a page that displays all rentals in
#chronological order and info about them by pulling
#the info from a postgres database
@app.route('/all_interactions')
def all_interactions():
    query = """SELECT r.rental_id, CAST(r.rental_date AS text), f.title, k.name, CAST(f.rental_rate as text), CAST(r.return_date AS text), CAST(p.amount as text), r.customer_id FROM rental r INNER JOIN inventory i ON r.inventory_id = i.inventory_id INNER JOIN film f on i.film_id = f.film_id INNER JOIN film_category c on f.film_id = c.film_id INNER JOIN category k on k.category_id = c.category_id INNER JOIN payment p ON p.rental_id = r.rental_id
    ORDER BY r.rental_date DESC"""
    try:
        conn = psql.connect(**params)
        c = conn.cursor()
        c.execute(query)
        colnames = [desc[0] for desc in c.description]
        R = c.fetchall()
        conn.close()
        R = [list(['None' if v is None else v for v in d]) for d in R]
    except Exception as e:
        print(e)
        R=[]
    return render_template("all_interactions.html", info=R, top='')


@app.route('/fig/')
def hp_graph():

    query = """SELECT DISTINCT(CAST(r.rental_date as date)), COUNT(r.rental_id), SUM(p.amount) FROM rental r INNER JOIN payment p on p.rental_id = r.rental_id
    GROUP BY CAST(r.rental_date as DATE)
    ORDER BY CAST(r.rental_date as DATE)"""

    try:
        conn = psql.connect(**params)
        c = conn.cursor()
        c.execute(query)
        colnames = [desc[0] for desc in c.description]
        R = c.fetchall()
        conn.close()
        x = [x[0] for x in R]
        z = [x[1] for x in R]
        y = [x[2] for x in R]
        img = io.BytesIO()
        plt.figure(figsize=(8, 4.2))
        plt.plot(x,y, label='Fees Paid')
        plt.plot(x,z, label='Number of Rentals')
        plt.legend()
        plt.title('Business Activity')
        plt.ylabel('Date')
        plt.xlabel('Amount')
        plt.savefig(img, format='png')
        img.seek(0)
        return send_file(img, mimetype='image/png')

    except Exception as e:
        print(e)
        plot_url=''
        return ''

#Create a page (linked to by search or all_interactions)
#that displays info about customer and all their rentals
@app.route("/customer/<id>")
def customer(id):
    query = """SELECT CONCAT(c.first_name, ' ', c.last_name), c.email, CONCAT(a.address, i.city, ', ', a.district, ' ', o.country), c.active FROM customer c INNER JOIN address a ON a.address_id = c.address_id INNER JOIN city i on i.city_id = a.city_id INNER JOIN country o on i.country_id = o.country_id
        WHERE c.customer_id = '{0}'""".format(id)
    try:
        conn = psql.connect(**params)
        c = conn.cursor()

        c.execute(query)
        colnames = [desc[0] for desc in c.description]
        R = c.fetchall()
        conn.close()
        R = [(['None' if v is None else v for v in d]) for d in R]
        R = R[0]
        top = """<h2>Customer {0}</h2>
        <div id=info> 
            <b>Name:</b> {1}</br>
            <b>Email:</b> {2}</br>
            <b>Address:</b> {3}</br>
            <b>Active:</b> {4}</br>
        </div>""".format(id, R[0], R[1], R[2], bool(R[3]))
        name = R[0]
        email = R[1]
        addr = R[2]
        act = R[3]
    except Exception as e:
        print(e)
        top = ''

    query = """SELECT r.rental_id, CAST(r.rental_date AS text), f.title, k.name, CAST(f.rental_rate as text), CAST(r.return_date AS text), CAST(p.amount as text), r.customer_id FROM rental r INNER JOIN inventory i ON r.inventory_id = i.inventory_id INNER JOIN film f on i.film_id = f.film_id INNER JOIN film_category c on f.film_id = c.film_id INNER JOIN category k on k.category_id = c.category_id INNER JOIN payment p ON p.rental_id = r.rental_id
        WHERE r.customer_id = '{0}'
        ORDER BY r.rental_date""".format(id)
    try:
        conn = psql.connect(**params)
        c = conn.cursor()
        c.execute(query)
        colnames = [desc[0] for desc in c.description]
        R = c.fetchall()
        conn.close()
        R = [list(['None' if v is None else v for v in d]) for d in R]
    except Exception as e:
        print(e)
    return render_template("all_interactions.html", info=R, top = top)

@app.route('/most_frequent')
def most_freq():
    query = """SELECT {0}, COUNT(r.inventory_id) from rental r INNER JOIN inventory i ON i.inventory_id = r.inventory_id INNER JOIN film f on i.film_id = f.film_id INNER JOIN film_category fc on f.film_id = fc.film_id INNER JOIN category k on k.category_id = fc.category_id
        GROUP BY f.title
        ORDER BY COUNT(r.inventory_id) DESC
        LIMIT 10;
        """
    results = []
    for x in ['f.title', 'k.category']:
        try:
            conn = psql.connect(**params)
            c = conn.cursor()
            c.execute(query.format(x))
            colnames = [desc[0] for desc in c.description]
            R = c.fetchall()
            conn.close()
            results.append(R)
        except Exception as e:
            results.append([])
            print(e)

@app.route('/search')
def search():
    return render_template('search.html')

@app.route('/genre/<g>')
def get_genre(g):
    g = g.lower().capitalize()
    query = """SELECT f.title, f.description, f.release_year,  f.rating, CAST(f.rental_rate as text) from film f INNER JOIN film_category c on f.film_id = c.film_id INNER JOIN category k on k.category_id = c.category_id
    WHERE k.name = '{0}' 
            ORDER BY f.title;
            """.format(g)
    try:
        conn = psql.connect(**params)
        c = conn.cursor()
        c.execute(query)
        colnames = [desc[0] for desc in c.description]
        R = c.fetchall()
        R = [list(['None' if v is None else v for v in d]) for d in R]
        conn.close()
    except Exception as e:
        print(e)
        R=[]
    return render_template('genre_list.html', info=R, g=g)

@app.route('/movie_details', methods=['GET', 'POST'])
def movie():

    try:
        movie = request.form['movie'].title()
        query = """SELECT f.title, f.description, k.name, f.release_year,  f.rating, CAST(f.rental_rate as text) from film f INNER JOIN film_category c on f.film_id = c.film_id INNER JOIN category k on k.category_id = c.category_id
    WHERE UPPER(f.title) = UPPER('{0}') 
            ORDER BY f.title;
            """.format(movie)
        conn = psql.connect(**params)
        c = conn.cursor()
        c.execute(query)
        colnames = [desc[0] for desc in c.description]
        R = c.fetchall()
        R = [list(['None' if v is None else v for v in d]) for d in R]
        R = R[0]
        conn.close()
        if R!= []:
            return render_template('movie_details.html', info=R)

    except Exception as e:
        print(e)
    return 'No movie by that title found'
