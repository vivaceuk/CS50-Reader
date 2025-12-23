from util.helpers import apology, login_required
from sqlalchemy import select

from flask import (
    Blueprint, flash, redirect, render_template, request, Response, session
)

import json

from db.models import User
from db.db import get_db

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route("/login", methods=["GET", "POST"])
async def login():
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

        async with get_db() as db_session:
            result = await db_session.execute(select(User).where(
                User.username == request.form.get("username")))
            user = result.scalars().one_or_none()

            await db_session.close()

        # Ensure username exists and password is correct
        if not isinstance(user, User) or not user.check_password(request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = user.id

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@auth_bp.route("/register", methods=["GET", "POST"])
async def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirmation")

        # Ensure username was submitted
        if not username:
            return apology("must provide username", 400)
        # Ensure password was submitted
        elif not password or not confirm_password:
            return apology("must provide password", 400)
        elif password != confirm_password:
            return apology("passwords must match", 400)

        async with get_db() as db_session:
            try:
                user = User()
                user.username = username
                user.set_password(password)
                await db_session.add(user)
                await db_session.commit()
            except:
                await db_session.close()
                return apology("Username already exists", 400)

            flash('You have successfully registerd!')
            await db_session.close()
            return redirect("/login")

    return render_template("register.html")


@auth_bp.route("/change_password", methods=["POST"])
@login_required
async def change_password():
    """Change user password"""
    user_id = session["user_id"]
    request_data = request.get_json()
    current_password = request_data['current_password']
    new_password = request_data['new_password']
    confirm_password = request_data['confirm_password']

    async with get_db() as db_session:
        user = await db_session.get(User, user_id)

        # check that the current password matches
        if not user.check_password(current_password):
            await db_session.close()
            return Response(json.dumps({'status': 'failure', 'error': 'bad password'}), status=400, mimetype='application/json')

        if new_password == '' or confirm_password == '':
            await db_session.close()
            return Response(json.dumps({'status': 'failure', 'error': 'password blank'}), status=400, mimetype='application/json')

        # check that the new password and confirmation match each other
        if not new_password == confirm_password:
            await db_session.close()
            return Response(json.dumps({'status': 'failure', 'error': 'password mismatch'}), status=400, mimetype='application/json')

        # create a new hash, and update the users table
        try:
            user.set_password(new_password)
            await db_session.commit()
            await db_session.close()
            return Response(response=json.dumps({'status': 'success'}), status=200, mimetype='application/json')
        except:
            pass

        await db_session.close()
    return Response(response=json.dumps({'status': 'failure'}), status=400, mimetype='application/json')
