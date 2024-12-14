from flask import redirect, render_template, session
from functools import wraps

def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code

def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"

def calculate_total_income(db, user_id):
    result = db.execute("SELECT SUM(amount) as total FROM transactions WHERE user_id = ? AND category = 'income'", user_id)
    return result[0]["total"] if result[0]["total"] else 0

def calculate_total_expenses(db, user_id):
    """Calculate total expenses for a user."""
    result = db.execute("SELECT SUM(amount) as total FROM transactions WHERE user_id = ? AND category = 'expense'", user_id)
    return result[0]["total"] if result[0]["total"] else 0

def get_expense_breakdown(db, user_id):
    """Get expense breakdown for pie chart."""
    expenses = db.execute("SELECT description, SUM(amount) as total FROM transactions WHERE user_id = ? AND category = 'expense' GROUP BY description", user_id)
    labels = [expense['description'] for expense in expenses]
    data = [expense['total'] for expense in expenses]
    return labels, data

def get_monthly_income_expenses(db, user_id):
    """Get monthly income and expenses for bar chart."""
    query = """
    SELECT strftime('%Y-%m', date) as month,
           SUM(CASE WHEN category = 'income' THEN amount ELSE 0 END) as income,
           SUM(CASE WHEN category = 'expense' THEN amount ELSE 0 END) as expenses
    FROM transactions
    WHERE user_id = ?
    GROUP BY strftime('%Y-%m', date)
    ORDER BY month
    LIMIT 6
    """
    results = db.execute(query, user_id)
    months = [result['month'] for result in results]
    incomes = [result['income'] for result in results]
    expenses = [result['expenses'] for result in results]
    return months, incomes, expenses

def update_goal_progress(db, user_id, goal_id, additional_amount):
    db.execute("UPDATE goals SET current_amount = current_amount + ? WHERE user_id = ? AND id = ?", additional_amount, user_id, goal_id)

def calculate_progress(goal):
    if goal['target_amount'] > 0:
        return (goal['current_amount'] / goal['target_amount']) * 100
    return 0

def fetch_goals_with_progress(db, user_id):
    goals = db.execute("SELECT * FROM goals WHERE user_id = ?", user_id)
    for goal in goals:
        goal['progress_percentage'] = calculate_progress(goal)
    return goals

def delete_goal(db, goal_id, user_id):
    db.execute("DELETE FROM goals WHERE id = ? AND user_id = ?", goal_id, user_id)
