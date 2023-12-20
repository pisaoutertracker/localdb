from flask import Blueprint, render_template

bp = Blueprint('main', __name__)

@bp.route('/')
def homeGUI():
    return render_template('home.html')

@bp.route('/connect.html')
def connectGUI():
    return render_template('connect.html')

