import os
from cs50 import SQL
from flask import Flask, redirect, render_template, request, session, make_response
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
import csv
import io
from helpers import apology, login_required, usd, delete_goal, calculate_total_income, calculate_total_expenses, get_expense_breakdown, get_monthly_income_expenses
from sklearn.ensemble import RandomForestRegressor
import numpy as np
import pandas as pd
from joblib import dump, load

# Configure application
app = Flask(__name__)

# Register the usd filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Ensure database tables exist
db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, username TEXT NOT NULL, hash TEXT NOT NULL)")
db.execute("CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, user_id INTEGER NOT NULL, category TEXT NOT NULL, amount NUMERIC NOT NULL, description TEXT, date DATETIME DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users(id))")
db.execute("CREATE TABLE IF NOT EXISTS goals (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, user_id INTEGER NOT NULL, name TEXT NOT NULL, target_amount NUMERIC NOT NULL, current_amount NUMERIC DEFAULT 0, FOREIGN KEY(user_id) REFERENCES users(id))")

class AIFinancialAnalyst:
    def __init__(self, db):
        self.db = db
        self.model_path = 'financial_model.joblib'
        if os.path.exists(self.model_path):
            self.model = load(self.model_path)
        else:
            self.model = RandomForestRegressor(n_estimators=100)
        self.feedback_data = []

    def collect_data(self, user_id):
        transactions = self.db.execute("SELECT * FROM transactions WHERE user_id = ?", user_id)
        goals = self.db.execute("SELECT * FROM goals WHERE user_id = ?", user_id)
        return pd.DataFrame(transactions), pd.DataFrame(goals)

    def preprocess_data(self, transactions, goals):
        # Check if 'amount' column exists in transactions
        if 'amount' not in transactions.columns:
            # If 'amount' doesn't exist, use a default value or return empty arrays
            X = np.array([])
        else:
            X = transactions[['amount']].values

        y = goals['target_amount'].values if not goals.empty else np.zeros(X.shape[0])
        return X, y

    def train_model(self, X, y):
        self.model.fit(X, y)
        dump(self.model, self.model_path)


    def generate_insights(self, user_id):
        transactions, goals = self.collect_data(user_id)
        X, y = self.preprocess_data(transactions, goals)

        insights = []
        if transactions.empty and goals.empty:
            insights.append("More information is needed to provide personalized insights. Please add some transactions and financial goals.")
        else:
            if X.shape[0] > 0 and X.shape[0] == y.shape[0]:
                if not hasattr(self.model, 'n_features_in_'):
                    self.train_model(X, y)
                predictions = self.model.predict(X)

            total_income = transactions[transactions['category'] == 'income']['amount'].sum()
            total_expenses = transactions[transactions['category'] == 'expense']['amount'].sum()
            if total_income > 0:
                savings_rate = (total_income - total_expenses) / total_income * 100
                insights.append(f"Your current savings rate is {savings_rate:.2f}%.")
                if savings_rate < 20:
                    insights.append("Consider increasing your savings rate to at least 20% for better financial stability.")
                elif savings_rate > 30:
                    insights.append("Great job on your savings rate! You're on track for strong financial health.")

            if not goals.empty:
                for _, goal in goals.iterrows():
                    progress = (goal['current_amount'] / goal['target_amount']) * 100
                    insights.append(f"For your goal '{goal['name']}', you're {progress:.2f}% of the way there.")
                    if progress < 50:
                        insights.append(f"Consider allocating more funds to your '{goal['name']}' goal to reach it faster.")

        return insights

    def update_from_feedback(self, user_id, insight_id, feedback):
        self.feedback_data.append({'user_id': user_id, 'insight_id': insight_id, 'feedback': feedback})
        if len(self.feedback_data) >= 10:  # Retrain after every 10 feedback instances
            self.retrain_model()

    def retrain_model(self):
        # Implement logic to retrain the model using feedback data
        # This is a placeholder implementation
        X, y = self.preprocess_data(pd.DataFrame(self.feedback_data), pd.DataFrame())
        self.train_model(X, y)
        self.feedback_data = []

# Initialize the AI analyst
ai_analyst = AIFinancialAnalyst(db)

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username:
            return apology("must provide username", 400)
        elif not password:
            return apology("must provide password", 400)
        elif not confirmation:
            return apology("must confirm password", 400)
        elif password != confirmation:
            return apology("passwords do not match", 400)

        hash = generate_password_hash(password)

        try:
            db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", username, hash)
            return redirect("/")
        except:
            return apology("username already exists", 400)

    else:
        return render_template("register.html")

@app.route("/dashboard")
@login_required
def dashboard():
    user_id = session["user_id"]
    total_income = calculate_total_income(db, user_id)
    total_expenses = calculate_total_expenses(db, user_id)
    expense_labels, expense_data = get_expense_breakdown(db, user_id)
    months, incomes, expenses = get_monthly_income_expenses(db, user_id)

    # Calculate savings
    savings = [income - expense for income, expense in zip(incomes, expenses)]

    return render_template("dashboard.html",
                           total_income=total_income,
                           total_expenses=total_expenses,
                           expense_labels=expense_labels,
                           expense_data=expense_data,
                           months=months,
                           incomes=incomes,
                           expenses=expenses,
                           savings=savings)

@app.route("/budget", methods=["GET", "POST"])
@login_required
def budget():
    if request.method == "POST":
        category = request.form.get("category")
        amount = request.form.get("amount")
        description = request.form.get("description")
        goal_category = request.form.get("goal_category")  # New field

        if not category or not amount:
            return apology("must provide category and amount", 400)

        db.execute("INSERT INTO transactions (user_id, category, amount, description) VALUES (?, ?, ?, ?)",
                   session["user_id"], category, amount, description)

        # Update goal progress if a goal category is selected
        if goal_category and category == "expense":
            db.execute("UPDATE goals SET current_amount = current_amount + ? WHERE user_id = ? AND category = ?",
                       amount, session["user_id"], goal_category)

        return redirect("/budget")
    else:
        transactions = db.execute("SELECT * FROM transactions WHERE user_id = ? ORDER BY date DESC", session["user_id"])
        total_income = calculate_total_income(db, session["user_id"])
        total_expenses = calculate_total_expenses(db, session["user_id"])
        goal_categories = db.execute("SELECT DISTINCT category FROM goals WHERE user_id = ?", session["user_id"])
        return render_template("budget.html", transactions=transactions, total_income=total_income,
                               total_expenses=total_expenses, goal_categories=goal_categories)

@app.route("/goals", methods=["GET", "POST"])
@login_required
def goals():
    if request.method == "POST":
        goal_name = request.form.get("goal_name")
        target_amount = request.form.get("target_amount")
        category = request.form.get("category")
        if category == "custom":
            category = request.form.get("custom_category")
        if not goal_name or not target_amount or not category:
            return apology("must provide goal name, target amount, and category", 400)
        db.execute("INSERT INTO goals (user_id, name, target_amount, category) VALUES (?, ?, ?, ?)",
                   session["user_id"], goal_name, target_amount, category)
        return redirect("/goals")
    else:
        goals = db.execute("SELECT * FROM goals WHERE user_id = ?", session["user_id"])
        for goal in goals:
            if goal['category'] == 'savings':
                goal['progress_percentage'] = (float(goal['current_amount']) / float(goal['target_amount'])) * 100 if float(goal['target_amount']) > 0 else 0
            else:
                spent = db.execute("SELECT SUM(amount) as total FROM transactions WHERE user_id = ? AND category = 'expense' AND description = ?",
                                   session["user_id"], goal['category'])[0]['total'] or 0
                goal['current_amount'] = spent
                goal['progress_percentage'] = (spent / float(goal['target_amount'])) * 100 if float(goal['target_amount']) > 0 else 0
        return render_template("goals.html", goals=goals)

@app.route("/update_goal", methods=["POST"])
@login_required
def update_goal():
    goal_id = request.form.get("goal_id")
    amount = float(request.form.get("amount"))

    db.execute("UPDATE goals SET current_amount = current_amount + ? WHERE id = ? AND user_id = ?",
               amount, goal_id, session["user_id"])

    return redirect("/goals")

@app.route("/delete_goal", methods=["POST"])
@login_required
def delete_goal_route():
    goal_id = request.form.get("goal_id")
    if goal_id:
        delete_goal(db, goal_id, session["user_id"])
    return redirect("/goals")

@app.route("/export_data")
@login_required
def export_data():
    # Fetch user's financial data
    user_id = session["user_id"]
    transactions = db.execute("SELECT * FROM transactions WHERE user_id = ?", user_id)

    # Define all fields from your transactions table
    fieldnames = ["id", "user_id", "date", "category", "amount", "description"]

    # Convert data to CSV
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for transaction in transactions:
        # Ensure all keys in fieldnames are present in the dictionary
        row = {field: transaction.get(field, '') for field in fieldnames}
        writer.writerow(row)

    # Create response
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=financial_data.csv"
    response.headers["Content-type"] = "text/csv"
    return response

@app.route("/ai_recommendations")
@login_required
def ai_recommendations():
    user_id = session["user_id"]
    # Generate insights using the AI analyst
    insights = ai_analyst.generate_insights(user_id)
    return render_template("ai_recommendations.html", insights=insights)

# Main execution
if __name__ == "__main__":
    app.run(debug=True)
