import requests
import math

from flask import redirect, render_template, session
from functools import wraps


def escape(s):
    """
    Escape special characters.

    https://github.com/jacebrowning/memegen#special-characters
    """
    for old, new in [
        ("-", "--"),
        (" ", "-"),
        ("_", "__"),
        ("?", "~q"),
        ("%", "~p"),
        ("#", "~h"),
        ("/", "~s"),
        ('"', "\""),
        ("'", "\'"),
    ]:
        s = s.replace(old, new)
    return s


def apology(message, code=400):
    """Render message as an apology to user."""

    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [
            ("-", "--"),
            (" ", "-"),
            ("_", "__"),
            ("?", "~q"),
            ("%", "~p"),
            ("#", "~h"),
            ("/", "~s"),
            ('"', "''"),
        ]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


# https://www.geeksforgeeks.org/searching-algorithms-in-python/
def binary_search(arr, target, low, high):
    """
    Perform binary search recursively to find the target value in the given sorted list.

    Parameters:
        arr (list): The sorted list to be searched.
        target: The value to be searched for.
        low (int): The lower index of the search interval.
        high (int): The upper index of the search interval.

    Returns:
        int: The index of the target value if found, otherwise -1.
    """
    if low <= high:
        mid = (low + high) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            return binary_search(arr, target, mid + 1, high)
        else:
            return binary_search(arr, target, low, mid - 1)
    else:
        return -1


def interpolation_search(arr, target):
    """
    Perform interpolation search to find the target value in the given sorted list.

    Parameters:
        arr (list): The sorted list to be searched.
        target: The value to be searched for.

    Returns:
        int: The index of the target value if found, otherwise -1.
    """
    low = 0
    high = len(arr) - 1
    while low <= high and target >= arr[low] and target <= arr[high]:
        pos = low + ((high - low) // (arr[high] - arr[low])) * (target - arr[low])
        if arr[pos] == target:
            return pos
        elif arr[pos] < target:
            low = pos + 1
        else:
            high = pos - 1
    return -1
