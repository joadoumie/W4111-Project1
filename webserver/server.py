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
# TO BE REMOVED
import time
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response, session, flash

# JSON RECIPEUID STUFF
with open('ids.json') as f:
    ids_data = json.load(f)

recipe_uid = ids_data["recipeuid"]
ingredient_uid = ids_data["ingredientid"]
review_id = ids_data["reviewid"]
new_user_id = ids_data["userid"]
print(ids_data["recipeuid"])
with open('ids.json', 'w') as json_file:
    json.dump(ids_data, json_file)


def increment_recipeID():
    global recipe_uid, ids_data
    recipe_uid += 1
    ids_data["recipeuid"] += 1
    with open('ids.json', 'w') as json_file:
        json.dump(ids_data, json_file)


def increment_ingredientID():
    global ingredient_uid, ids_data
    ingredient_uid += 1
    ids_data["ingredientid"] += 1
    with open('ids.json', 'w') as json_file:
        json.dump(ids_data, json_file)


def increment_userID():
    global new_user_id, ids_data
    new_user_id += 1
    ids_data["userid"] += 1
    with open('ids.json', 'w') as json_file:
        json.dump(ids_data, json_file)

def increment_reviewID():
  global review_id, ids_data
  review_id += 1
  ids_data["reviewid"] += 1
  with open('ids.json', 'w') as json_file:
    json.dump(ids_data, json_file)


tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)


def insert_into_table(table_name, list_of_vals):
    values = "("
    for val in list_of_vals:
        values += str(val)
    values += ")"
    return "INSERT INTO " + table_name + "VALUES " + values


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
    if not session.get('logged_in'):
        return render_template('login.html')
    return render_template("recipe_home.html")


@app.route('/allrecipes')
def all_recipes():
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
        recipeNamesDict[currRecipeID] = str(result['recipename']).strip()
        recipeInstDict[currRecipeID] = str(result['instructions']).strip()
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

    context1 = dict(recipeIDList=recipeIDList, recipeNamesDict=recipeNamesDict,
                    recipeInstDict=recipeInstDict, recipeIngredDict=recipeIngredDict,
                    recipeRatingDict=recipeRatingDict)
    #
    # render_template looks in the templates/ folder for files.
    # for example, the below file reads template/index.html
    #
    return render_template("allrecipes.html", **context1)


@app.route('/reviews')
def review_recipes():
    return render_template("reviewrecipe.html")


@app.route('/logout')
def logout():
    session['logged_in'] = False
    return index()


@app.route('/another')
def another():
    return render_template("anotherfile.html")


@app.route('/home')
def recipe_home():
    return render_template("recipe_home.html")


@app.route('/addingredienterror')
def add_ingr_err():
    return render_template("addingingredienterror.html")


@app.route('/testnav')
def navbar():
    return render_template("testnavbar.html")

@app.route('/favoriterecipes')
def fave_recipes():
    # DEBUG: this is debugging code to see what request looks like
    print(request.args)

    #
    # example of a database query
    #
    tempfave = """
    select *
    from recipes natural join favorites
    where uid = (:name1)
    """
    cursor1 = g.conn.execute(text(tempfave), name1 = session["uid"])
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

    context2 = dict(recipeIDList=recipeIDList, recipeNamesDict=recipeNamesDict,
                    recipeInstDict=recipeInstDict, recipeIngredDict=recipeIngredDict)

    return render_template("favoriterecipes.html", **context2)

@app.route('/follows')
def follow():

    tempsql1 = """
    select * from follows as f join users as u
    on f.leader = u.uid
    where f.follower = (:name8)
    """
    cursor3 = g.conn.execute(text(tempsql1), name8=session["uid"])

    leaderDict = {}
    for result1 in cursor3:
        leaderDict[result1['leader']] = str(result1['username']).strip()

    context4 = dict(leaderDict = leaderDict)

    return render_template("follows.html", **context4)

@app.route('/follownew', methods=['POST'])
def follow_add():
    leader = request.form['username']
    uid = session["uid"]
    cmd0 = 'SELECT uid FROM users where username = (:name1)'
    leaderID = g.conn.execute(text(cmd0), name1=leader)
    for row in leaderID:
        print("ROW", row)
        x = row[0]
    # print(leaderID.get('uid'))
    cmd = 'INSERT INTO follows VALUES (:name1, :name2)';
    g.conn.execute(text(cmd), name1=x, name2=uid);
    return redirect('/home')

@app.route('/addfavorite', methods=['POST'])
def favorite_add():
    recipeid = request.form['recipeid']
    uid = session["uid"]
    cmd = 'INSERT INTO favorites VALUES (:name1, :name2)';
    g.conn.execute(text(cmd), name1=recipeid, name2=uid);
    return redirect('/home')

@app.route('/addreview', methods=['POST'])
def review_add():
    recipeid = request.form['recipeid']
    stars = request.form['stars']
    content = request.form['reviewtext']
    uid = session["uid"]
    # print(recipe_name, instructions, ingredients)
    cmd = 'INSERT INTO review VALUES (:name1, :name2, :name3, :name4, :name5)';
    g.conn.execute(text(cmd), name1=review_id, name2=content,
                   name3=stars, name4=recipeid, name5=uid);
    increment_reviewID()
    return redirect('/home')


@app.route('/addrecipe', methods=['POST'])
def recipe_add():
    recipe_name = request.form['recipename']
    instructions = request.form['instructions']
    print(recipe_name, instructions)
    cmd = 'INSERT INTO recipes VALUES (:name1, :name2, :name3)';
    g.conn.execute(text(cmd), name1=recipe_uid, name2=recipe_name, name3=instructions);
    session["recipeid"] = recipe_uid
    increment_recipeID()
    flash("Successfully added Recipe! Please add your ingredients now!")
    return redirect('/home')


@app.route('/addingredient', methods=['POST'])
def ingredient_add():
    ingredient_name = request.form['ingredient_name']
    ingredient_qty = request.form['quantity']
    ingredient_unit = request.form['unit']
    # cmd = 'SELECT * FROM recipes WHERE recipeID = (:name1)'
    # recipe_exists = g.conn.execute(text(cmd), name1 = ).scalar()
    if "recipeid" not in session:
        flash("You must add a recipe first! Try again!")
        return redirect('/home')
    cmd = 'SELECT * FROM ingredients WHERE name = (:name1)'
    ingredient_exists = g.conn.execute(text(cmd), name1=request.form["ingredient_name"]).scalar()
    if not ingredient_exists:
        # Add ingredient to ingredients table.
        local_ingr_id = ingredient_uid
        cmd = 'INSERT INTO ingredients VALUES (:name1, :name2)';
        g.conn.execute(text(cmd), name1=local_ingr_id, name2=ingredient_name);
        increment_ingredientID()
    else:
        ingr_result = g.conn.execute(text(cmd), name1=request.form["ingredient_name"])
        for row in ingr_result:
          print("ROW", row)
          local_ingr_id = row[0]

    cmd = 'INSERT INTO contains_ingredients VALUES (:name1, :name2, :name3, :name4)';
    g.conn.execute(text(cmd), name1=local_ingr_id, name2=session["recipeid"], name3=ingredient_qty, name4=ingredient_unit);
    flash("Ingredient successfully added! Add another ingredient if need be!")
    return redirect('/home')


@app.route('/existing_login')
def existing_login():
    return render_template('existinglogin.html')


@app.route('/create_new_login')
def create_new_login():
    return render_template('createnewaccount.html')


@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/login_attempt', methods=['POST'])
def do_login():
    print("Testing testing")
    if request.form['password'] == '123123' and request.form['username'] == 'admin':
        session['logged_in'] = True
        return index()
    cmd = "SELECT * FROM users WHERE username = (:name1)"
    user_exists = g.conn.execute(text(cmd), name1=request.form["username"]).scalar()
    if not user_exists:
        flash("No user with that username")
        return render_template('existinglogin.html')
    cmd = "SELECT * FROM users WHERE username = (:name1) AND password = (:name2)"
    correct_password = g.conn.execute(text(cmd), name1=request.form["username"],
                                      name2=request.form["password"]).scalar()
    if not correct_password:
        flash('wrong password!')
        return redirect(request.referrer)
    session['logged_in'] = True
    cmd = "SELECT uid FROM users WHERE username = (:name1)"
    uid_row = g.conn.execute(text(cmd), name1=request.form["username"])
    for row in uid_row:
        uid = row["uid"]
    session["uid"] = uid
    return index()


@app.route('/create_new_account', methods=['POST'])
def create_new_account():
    cmd = "SELECT * FROM users WHERE username = (:name1)"
    user_exists = g.conn.execute(text(cmd), name1=request.form["username"]).scalar()
    if user_exists:
        flash("A user already exists with that username - please choose a new username")
        return redirect(request.referrer)
    cmd = "INSERT INTO users VALUES (:name1, :name2, :name3)"
    g.conn.execute(text(cmd), name1=new_user_id, name2=request.form["username"], name3=request.form["password"])
    increment_userID()
    flash("Please login now")
    return render_template('existinglogin.html')


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
        app.secret_key = os.urandom(12)
        app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


    run()
