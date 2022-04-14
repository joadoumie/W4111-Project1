"""
Columbia W4111 Intro to databases
Example webserver

To run locally

    python server.py

Go to http://localhost:8111 in your browser


A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""

import os
import json
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response

# JSON RECIPEUID STUFF
with open('ids.json') as f:
    ids_data = json.load(f)

print(ids_data)
print(ids_data["recipeuid"])
recipe_uid = ids_data["recipeuid"]
# ids_data["recipeuid"] += 1
print(ids_data["recipeuid"])
with open('ids.json', 'w') as json_file:
    json.dump(ids_data, json_file)

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)

# XXX: The Database URI should be in the format of:
#
#     postgresql://USER:PASSWORD@<IP_OF_POSTGRE_SQL_SERVER>/<DB_NAME>
#
# For example, if you had username ewu2493, password foobar, then the following line would be:
#
#     DATABASEURI = "postgresql://ewu2493:foobar@<IP_OF_POSTGRE_SQL_SERVER>/postgres"
#
# For your convenience, we already set it to the class database

# Use the DB credentials you received by e-mail
DB_USER = "sjc2233"
DB_PASSWORD = "bridge"

DB_SERVER = "w4111.cisxo09blonu.us-east-1.rds.amazonaws.com"

DATABASEURI = "postgresql://" + DB_USER + ":" + DB_PASSWORD + "@" + DB_SERVER + "/proj1part2"

#
# This line creates a database engine that knows how to connect to the URI above
#
engine = create_engine(DATABASEURI)

# Here we create a test table and insert some values in it
engine.execute("""DROP TABLE IF EXISTS test;""")
engine.execute("""CREATE TABLE IF NOT EXISTS test (
  id serial,
  name text
);""")
engine.execute("""INSERT INTO test(name) VALUES ('grace hopper'), ('alan turing'), ('ada lovelace');""")


@app.before_request
def before_request():
    """
  This function is run at the beginning of every web request 
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request

  The variable g is globally accessible
  """
    try:
        g.conn = engine.connect()
    except:
        print("uh oh, problem connecting to database")
        import traceback;
        traceback.print_exc()
        g.conn = None


@app.teardown_request
def teardown_request(exception):
    """
  At the end of the web request, this makes sure to close the database connection.
  If you don't the database could run out of memory!
  """
    try:
        g.conn.close()
    except Exception as e:
        pass


#
# @app.route is a decorator around index() that means:
#   run index() whenever the user tries to access the "/" path using a GET request
#
# If you wanted the user to go to e.g., localhost:8111/foobar/ with POST or GET then you could use
#
#       @app.route("/foobar/", methods=["POST", "GET"])
#
# PROTIP: (the trailing / in the path is important)
# 
# see for routing: http://flask.pocoo.org/docs/0.10/quickstart/#routing
# see for decorators: http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/
#
@app.route('/')
def index():
    """
  request is a special object that Flask provides to access web request information:

  request.method:   "GET" or "POST"
  request.form:     if the browser submitted a form, this contains the data in the form
  request.args:     dictionary of URL arguments e.g., {a:1, b:2} for http://localhost?a=1&b=2

  See its API: http://flask.pocoo.org/docs/0.10/api/#incoming-request-data
  """

    # DEBUG: this is debugging code to see what request looks like
    print(request.args)

    #
    # example of a database query
    #
    cursor1 = g.conn.execute("SELECT * FROM recipes")
    recipeIDList = []
    recipeNamesDict = {}
    recipeInstDict = {}
    for result in cursor1:
        recipeIDList.append(result['recipeid'])  # can also be accessed using result[0]
        currRecipeID = result['recipeid']
        recipeNamesDict[currRecipeID]= str(result['recipename']).strip()
        recipeInstDict[currRecipeID]= str(result['instructions']).strip()
    cursor1.close()

    recipeIngredDict = {}
    for curr_recipeID in recipeIDList:
        temp_sql = """
        select *
        from recipes natural join contains_ingredients natural join ingredients
        where recipeID = %d
        """ % (curr_recipeID)
        tempCursor = g.conn.execute(temp_sql)
        currRecipeIngred = []
        for result in tempCursor:
            tempAmt = str(result['amount']).strip()
            tempUnit = str(result['unit']).strip()
            tempName = str(result['name']).strip()
            tempStr = tempAmt + ' ' + tempUnit + ' ' + tempName
            currRecipeIngred.append(tempStr)
        recipeIngredDict[curr_recipeID] = currRecipeIngred
        tempCursor.close()

    recipeRatingDict = {}
    for curr_recipeID in recipeIDList:
        temp_sql = """
        select *
        from review natural join users
        where recipeID = %d
        """ % (curr_recipeID)
        tempCursor1 = g.conn.execute(temp_sql)
        currReviewList = []
        for result in tempCursor1:
            tempReview = {'reviewid': result['reviewid'],
                          'stars': result['stars'],
                          'content': str(result['content']).strip(),
                          'username': result['username']}
            # tempReview = [result['reviewid'], result['stars'], str(result['content']).strip()]
            currReviewList.append(tempReview)
        recipeRatingDict[curr_recipeID] = currReviewList
        tempCursor1.close()

    print(recipeRatingDict[2][1])

    context1 = dict(recipeIDList=recipeIDList, recipeNamesDict=recipeNamesDict,
                    recipeInstDict=recipeInstDict, recipeIngredDict=recipeIngredDict,
                    recipeRatingDict=recipeRatingDict)
    #
    # render_template looks in the templates/ folder for files.
    # for example, the below file reads template/index.html
    #
    return render_template("index.html", **context1)


#
# This is an example of a different path.  You can see it at
# 
#     localhost:8111/another
#
# notice that the functio name is another() rather than index()
# the functions for each app.route needs to have different names
#
@app.route('/another')
def another():
    return render_template("anotherfile.html")


@app.route('/home')
def recipe_home():
    return render_template("recipe_home.html")


@app.route('/testnav')
def navbar():
    return render_template("testnavbar.html")


# Example of adding new data to the database
@app.route('/add', methods=['POST'])
def add():
    name = request.form['name']
    cmd = 'INSERT INTO test(name) VALUES (:name1), (:name2)';
    g.conn.execute(text(cmd), name1=name, name2=name);
    return redirect('/')


@app.route('/addrecipe', methods=['POST'])
def recipe_add():
    recipe_name = request.form['recipename']
    instructions = request.form['instructions']
    ingredients = request.form['ingredients']
    print(recipe_name, instructions, ingredients)
    cmd = 'INSERT INTO recipes VALUES (:name1, :name2, :name3)';
    g.conn.execute(text(cmd), name1=recipe_uid, name2=recipe_name, name3=instructions);
    return redirect('/home')


@app.route('/login')
def login():
    abort(401)
    this_is_never_executed()


if __name__ == "__main__":
    import click


    @click.command()
    @click.option('--debug', is_flag=True)
    @click.option('--threaded', is_flag=True)
    @click.argument('HOST', default='0.0.0.0')
    @click.argument('PORT', default=8111, type=int)
    def run(debug, threaded, host, port):
        """
    This function handles command line parameters.
    Run the server using

        python server.py

    Show the help text using

        python server.py --help

    """

        HOST, PORT = host, port
        print("running on %s:%d" % (HOST, PORT))
        app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


    run()
